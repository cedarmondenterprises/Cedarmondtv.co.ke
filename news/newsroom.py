"""Private newsroom workflows. All routes are wrapped by AdminSite.admin_view."""
import calendar
import json
import uuid
from datetime import date, datetime, time, timedelta
from django import forms
from django.contrib import messages
from django.contrib.admin.models import LogEntry, CHANGE
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods
from .editor import sanitize_html
from .models import Article, DraftRecovery, EditorialComment
from .permissions import can_view_article, can_edit_article


class CommentForm(forms.Form):
    message = forms.CharField(max_length=5000,widget=forms.Textarea(attrs={'rows':4}))


def visible_articles(user):
    if not user.is_staff or not user.has_perm('news.view_article'): raise PermissionDenied
    articles=Article.objects.select_related('owner','author','category')
    return articles if user.has_perm('news.publish_article') else articles.filter(owner=user)


def desk(request,admin_site):
    today=timezone.localdate()
    try:
        month=datetime.strptime(request.GET.get('month',today.strftime('%Y-%m')),'%Y-%m').date()
        if not 2000 <= month.year <= 2100: raise ValueError
    except ValueError:
        month=today.replace(day=1)
    next_month=(month.replace(day=28)+timedelta(days=4)).replace(day=1)
    previous=(month-timedelta(days=1)).replace(day=1)
    start=timezone.make_aware(datetime.combine(month,time.min))
    end=timezone.make_aware(datetime.combine(next_month,time.min))
    articles=visible_articles(request.user)
    scheduled=articles.filter(Q(deadline__gte=start,deadline__lt=end)|Q(status='published',published_at__gte=start,published_at__lt=end)).order_by('deadline','published_at')[:300]
    events=[]
    for item in scheduled:
        if item.deadline and start <= item.deadline < end: events.append({'at':item.deadline,'kind':'Deadline','article':item})
        if item.status=='published' and start <= item.published_at < end: events.append({'at':item.published_at,'kind':'Publication','article':item})
    events.sort(key=lambda event:event['at'])
    recoveries=DraftRecovery.objects.filter(user=request.user)
    if not request.user.has_perm('news.publish_article'):
        recoveries=recoveries.filter(Q(article__isnull=True)|Q(article__owner=request.user))
    recovery_rows=[]
    for recovery in recoveries.select_related('article')[:20]:
        path=reverse('admin:news_article_change',args=[recovery.article_id]) if recovery.article_id else reverse('admin:news_article_add')
        recovery_rows.append({'id':recovery.pk,'title':recovery.data.get('title') or 'Untitled draft','url':path+'?recovery='+str(recovery.pk),'saved_at':recovery.saved_at})
    context=dict(admin_site.each_context(request),title='Editorial calendar and assignments',events=events,month=month,previous=previous.strftime('%Y-%m'),next_month=next_month.strftime('%Y-%m'),recoveries=recovery_rows,review_queue=articles.filter(status='review').order_by('deadline','published_at')[:30])
    return TemplateResponse(request,'admin/news/desk.html',context)


@require_http_methods(['GET','POST'])
def workspace(request,pk,admin_site):
    article=get_object_or_404(visible_articles(request.user),pk=pk)
    form=CommentForm(request.POST or None)
    if request.method=='POST':
        if not request.user.has_perm('news.change_article'): raise PermissionDenied
        if request.POST.get('action')=='resolve':
            comment=get_object_or_404(EditorialComment,pk=request.POST.get('comment'),article=article)
            if not request.user.has_perm('news.publish_article') and comment.author_id != request.user.pk: raise PermissionDenied
            comment.resolved_at=timezone.now(); comment.resolved_by=request.user
            comment.save(update_fields=['resolved_at','resolved_by'])
            return redirect('admin:news_article_workspace',pk=pk)
        if form.is_valid():
            EditorialComment.objects.create(article=article,author=request.user,**form.cleaned_data)
            return redirect('admin:news_article_workspace',pk=pk)
    comments=article.editorial_comments.select_related('author','resolved_by')[:200]
    context=dict(admin_site.each_context(request),title='Editorial discussion',article=article,form=form,comments=comments,publisher=request.user.has_perm('news.publish_article'))
    return TemplateResponse(request,'admin/news/workspace.html',context)


FIELDS={'title':220,'slug':240,'summary':400,'body':100000,'seo_title':70,'seo_description':160,'category':20,'author':20,'media_asset':20}


def clean_snapshot(data):
    if not isinstance(data,dict): raise ValueError('Invalid recovery data.')
    cleaned={}
    for field,limit in FIELDS.items():
        value=data.get(field,'')
        if not isinstance(value,str) or len(value)>limit: raise ValueError(f'{field} exceeds its recovery limit.')
        cleaned[field]=sanitize_html(value) if field=='body' else value
    tags=data.get('tags',[])
    if not isinstance(tags,list) or len(tags)>50 or any(not isinstance(tag,str) or not tag.isdecimal() for tag in tags): raise ValueError('Invalid topic list.')
    cleaned['tags']=tags
    return cleaned


@require_http_methods(['GET','POST'])
def recovery(request,key):
    if not request.user.is_staff or not request.user.has_perm('news.add_article'): raise PermissionDenied
    if request.method=='GET':
        record=DraftRecovery.objects.filter(pk=key,user=request.user).select_related('article').first()
        if record and record.article and not can_edit_article(request.user,record.article): raise PermissionDenied
        if not record: return JsonResponse({'exists':False,'version':0})
        return JsonResponse({'exists':True,'version':record.version,'data':record.data,'saved_at':record.saved_at.isoformat(),'base_updated_at':record.base_updated_at})
    if len(request.body)>150000: return JsonResponse({'error':'Recovery data is too large.'},status=413)
    try:
        payload=json.loads(request.body)
        if not isinstance(payload,dict): raise ValueError
        data=clean_snapshot(payload.get('data'))
        version=payload.get('version')
        if type(version) is not int or version<0: raise ValueError
        article_id=payload.get('article_id')
        if article_id is not None and (type(article_id) is not int or article_id<1): raise ValueError
        base=payload.get('base_updated_at','')
        if not isinstance(base,str) or len(base)>60: raise ValueError
    except (ValueError,TypeError): return JsonResponse({'error':'Invalid recovery payload.'},status=400)
    with transaction.atomic():
        article=get_object_or_404(Article.objects.select_for_update(),pk=article_id) if article_id else None
        if article and not can_edit_article(request.user,article): raise PermissionDenied
        if article and base != article.updated_at.isoformat():
            return JsonResponse({'error':'This article changed in another session. Reload it before saving further edits.'},status=409)
        record=DraftRecovery.objects.select_for_update().filter(pk=key).first()
        if record and (record.user_id != request.user.pk or record.article_id != article_id): raise Http404
        if record is None:
            if version != 0: return JsonResponse({'error':'Recovery copy was cleared. Reload the editor.'},status=409)
            if DraftRecovery.objects.filter(user=request.user).count()>=50:
                return JsonResponse({'error':'You have 50 recovery copies. Save or discard older copies from the editorial desk.'},status=409)
            record=DraftRecovery(id=key,user=request.user,article=article)
        if record.version != version:
            return JsonResponse({'error':'A newer recovery copy exists in another tab. Reload before continuing.'},status=409)
        record.data=data;record.base_updated_at=base;record.version+=1
        record.save()
    return JsonResponse({'version':record.version,'saved_at':record.saved_at.isoformat()})


@require_http_methods(['POST'])
def discard_recovery(request,key):
    get_object_or_404(DraftRecovery,pk=key,user=request.user).delete()
    messages.success(request,'Recovery copy discarded. Published articles were not changed.')
    return redirect('admin:news_article_desk')


@require_http_methods(['GET','POST'])
def restore_revision(request,pk,version,admin_site):
    if not request.user.has_perm('news.publish_article') or not request.user.has_perm('news.add_article'): raise PermissionDenied
    article=get_object_or_404(visible_articles(request.user),pk=pk)
    revision=get_object_or_404(article.history,history_id=version)
    if request.method=='POST':
        with transaction.atomic():
            article=Article.objects.select_for_update().get(pk=pk)
            restored=Article(title=revision.title,summary=revision.summary,body=revision.body,
                slug=(slugify(revision.title)[:190] or 'restored-story')+'-restored-'+uuid.uuid4().hex[:12],
                author=article.author,category=article.category,owner=article.owner or request.user,
                seo_title=revision.seo_title,seo_description=revision.seo_description,status='draft')
            restored._history_user=request.user
            restored._change_reason=f'Text restored from article {article.pk}, revision {revision.history_id}; current author/category/topics retained.'
            restored.save();restored.tags.set(article.tags.all())
            LogEntry.objects.log_actions(user_id=request.user.pk,queryset=[restored],action_flag=CHANGE,change_message=restored._change_reason)
        messages.success(request,'Revision text restored as a new unpublished draft. The original article is unchanged.')
        return redirect('admin:news_article_change',object_id=restored.pk)
    return TemplateResponse(request,'admin/news/restore.html',dict(admin_site.each_context(request),title='Restore revision text as a new draft',article=article,revision=revision))
