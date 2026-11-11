import json
from urllib.parse import quote
from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django_ratelimit.decorators import ratelimit
from .security import rate_key
from .newsletter import request_confirmation, unsubscribe
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import connection
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import Article, ArticleURL, Category, Author, Tag, Subscription, Page, StoryComment
from .forms import SubscribeForm, ContactForm, StoryCommentForm

def home(request):
    live = Article.objects.live()
    lead = live.filter(featured=True).first() or live.first()
    rest = live.exclude(pk=lead.pk) if lead else live
    return render(request,'news/home.html',{'lead':lead,'top_stories':rest[:2],'latest':live[:5],'stories':rest[2:8],'picks':live.filter(editors_pick=True)[:3]})

def listing(request,kind=None,slug=None):
    articles = Article.objects.live()
    title, description = 'Latest stories', 'The latest from the Cedarmond TV newsroom.'
    if kind == 'category':
        obj = get_object_or_404(Category,slug=slug); articles = articles.filter(category=obj); title = obj.name
    elif kind == 'author':
        obj = get_object_or_404(Author,slug=slug); articles = articles.filter(author=obj); title, description = obj.name,obj.bio
    elif kind == 'tag':
        obj = get_object_or_404(Tag,slug=slug); articles = articles.filter(tags=obj); title = obj.name
    query = request.GET.get('q','').strip()[:120]
    if query:
        articles = articles.filter(Q(title__icontains=query)|Q(summary__icontains=query)|Q(body__icontains=query)|Q(author__name__icontains=query)|Q(category__name__icontains=query)|Q(tags__name__icontains=query)).distinct(); title = 'Search results'
    return render(request,'news/list.html',{'page':Paginator(articles,9).get_page(request.GET.get('page')),'title':title,'description':description,'query':query})

def article(request,slug):
    item = Article.objects.live().prefetch_related('tags').filter(slug=slug).first()
    if item is None:
        reservation=get_object_or_404(ArticleURL,slug=slug)
        target=get_object_or_404(Article.objects.live(),pk=reservation.article_id)
        return redirect(target.get_absolute_url(),permanent=True)
    return render_article(request,item)

def render_article(request,item,preview=False,comment_form=None,status=200):
    url = settings.SITE_URL + item.get_absolute_url()
    schema = {'@context':'https://schema.org','@type':'NewsArticle','headline':item.title,'description':item.summary,'datePublished':item.published_at.isoformat(),'dateModified':item.updated_at.isoformat(),'author':[{'@type':'Person','name':item.author.name,'url':settings.SITE_URL+item.author.get_absolute_url()}],'publisher':{'@type':'Organization','name':'Cedarmond TV'},'mainEntityOfPage':url}
    if item.display_image: schema['image'] = [settings.SITE_URL+item.display_image.url]
    return render(request,'news/article.html',{'article':item,'preview':preview,'related':Article.objects.live().filter(category=item.category).exclude(pk=item.pk)[:3],'reader_comments':item.reader_comments.filter(status=StoryComment.APPROVED)[:50],'comment_count':item.reader_comments.filter(status=StoryComment.APPROVED).count(),'comment_form':comment_form or (None if preview else StoryCommentForm()),'canonical':url,'share_url':quote(url,safe=''),'share_text':quote(item.title+' '+url,safe=''),'schema_json':json.dumps(schema).replace('<',r'\u003c')},status=status)

@require_http_methods(['POST'])
@ratelimit(key=rate_key,rate='5/h',method='POST',block=False)
def story_comment(request,slug):
    item=get_object_or_404(Article.objects.live(),slug=slug)
    form=StoryCommentForm(request.POST)
    if form.is_valid():
        if form.cleaned_data['website']:
            messages.success(request,'Thank you. Comments are reviewed before they appear.')
            return redirect(item.get_absolute_url()+'#reader-comments')
        if getattr(request,'limited',False) or throttled(request,'comment_time'):
            form.add_error(None,'Please wait before posting another comment.')
            return render_article(request,item,comment_form=form,status=429)
        StoryComment.objects.create(article=item,display_name=form.cleaned_data['display_name'].strip(),body=form.cleaned_data['body'].strip())
        messages.success(request,'Thank you. Your comment is awaiting editorial review.')
        return redirect(item.get_absolute_url()+'#reader-comments')
    return render_article(request,item,comment_form=form)

def throttled(request,key):
    now = timezone.now().timestamp()
    if now - request.session.get(key,0) < 60: return True
    request.session[key] = now
    return False

@require_http_methods(['GET','POST'])
@ratelimit(key=rate_key,rate='5/h',method='POST',block=False)
def newsletter(request):
    if not settings.NEWSLETTER_ENABLED:
        return render(request,'news/unavailable.html',{'title':'The briefing is not accepting subscriptions.'},status=503)
    form = SubscribeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if getattr(request,'limited',False):
            form.add_error(None,'Too many requests. Please try again later.')
        elif form.cleaned_data['website'] or throttled(request,'subscribe_time'):
            form.add_error(None,'Please wait a minute before trying again.')
        else:
            request_confirmation(form.cleaned_data['email'])
            messages.success(request,'If confirmation is needed, an email has been queued for you. Check your inbox shortly.')
            return redirect('newsletter')
    return render(request,'news/form.html',{'form':form,'title':'The stories that matter. In your inbox.','description':'Sign up for the Cedarmond briefing. Confirm your email to join.','button':'Request confirmation'})

@require_http_methods(['GET','POST'])
@never_cache
def subscription_action(request,token,action):
    try:
        payload = signing.loads(token,salt='newsletter-'+action,max_age=172800 if action=='confirm' else None)
        if not isinstance(payload,dict): raise signing.BadSignature
        subscriber=Subscription.objects.get(email=payload['email'],token_version=payload['version'])
    except (signing.BadSignature,Subscription.DoesNotExist,KeyError,ValueError,ValidationError):
        raise Http404('This link has expired or is invalid.')
    if request.method == 'POST':
        if action == 'confirm':
            Subscription.objects.filter(pk=subscriber.pk,token_version=subscriber.token_version).update(active=True,confirmed_at=timezone.now())
        else: unsubscribe(subscriber)
        return render(request,'news/unavailable.html',{'title':'Subscription confirmed.' if action=='confirm' else 'You have been unsubscribed.'})
    return render(request,'news/confirm.html',{'title':'Confirm subscription' if action=='confirm' else 'Unsubscribe','email':subscriber.email})

@require_http_methods(['GET','POST'])
@ratelimit(key=rate_key,rate='10/h',method='POST',block=False)
def contact(request):
    form = ContactForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        if getattr(request,'limited',False) or form.cleaned_data['website'] or throttled(request,'contact_time'): form.add_error(None,'Please wait a minute before trying again.')
        else:
            form.save(); messages.success(request,'Your message has reached our editorial inbox.'); return redirect('contact')
    return render(request,'news/form.html',{'form':form,'title':'Talk to the newsroom','description':'Send a story tip, correction, advertising enquiry, or feedback.','button':'Send message'})

def page(request,slug):
    item=get_object_or_404(Page,slug=slug,published=True)
    return render(request,'news/page.html',{'title':item.title,'page':item})

@login_required
@never_cache
def preview(request,pk):
    item=get_object_or_404(Article,pk=pk)
    if not request.user.is_staff or not request.user.has_perm('news.view_article'):
        raise Http404
    if not request.user.has_perm('news.publish_article') and item.owner_id != request.user.pk:
        raise Http404
    response=render_article(request,item,preview=True)
    response['X-Robots-Tag']='noindex, nofollow'
    return response


def health(request):
    try:
        with connection.cursor() as cursor: cursor.execute('SELECT 1')
    except Exception: return JsonResponse({'status':'unavailable'},status=503)
    return JsonResponse({'status':'ok'})

def robots(request):
    return HttpResponse('User-agent: *\nDisallow: /admin/\nDisallow: /search/\nSitemap: '+settings.SITE_URL+'/sitemap.xml\n',content_type='text/plain')
