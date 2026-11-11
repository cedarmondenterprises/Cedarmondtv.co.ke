from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.urls import path
from simple_history.admin import SimpleHistoryAdmin
from .models import Article, Category, Author, Tag, Subscription, ReaderMessage, AdPlacement, Page, Campaign, MediaAsset, DraftRecovery, StoryComment
from .newsletter import queue_campaign
admin.site.site_header = 'Cedarmond TV · Newsroom'
admin.site.site_title = 'Cedarmond TV Newsroom'
admin.site.index_title = 'Publishing desk'
admin.site.index_template = 'admin/newsroom_index.html'

class ArticleAdminForm(forms.ModelForm):
    recovery_key=forms.CharField(required=False,widget=forms.HiddenInput)
    loaded_version=forms.CharField(required=False,widget=forms.HiddenInput)
    class Meta:
        model=Article
        fields='__all__'
    def clean(self):
        cleaned=super().clean()
        if self.instance.pk:
            current=Article.objects.select_for_update().filter(pk=self.instance.pk).values_list('updated_at',flat=True).first()
            expected=self.data.get('loaded_version','')
            if current and expected != current.isoformat():
                raise forms.ValidationError('This story changed after you opened it. Reload the latest version before saving.')
        return cleaned

class ReadOnlyHistoryAdmin(SimpleHistoryAdmin):
    def history_view(self,request,object_id,extra_context=None):
        extra_context={**(extra_context or {}),'can_restore':self.model is Article and request.user.has_perm('news.publish_article') and request.user.has_perm('news.add_article')}
        return super().history_view(request,object_id,extra_context)
    def history_form_view(self,request,object_id,version_id,extra_context=None):
        # The library's disabled button alone does not reject crafted POSTs.
        if request.method != 'GET': raise PermissionDenied
        from django.shortcuts import get_object_or_404
        obj=get_object_or_404(self.get_queryset(request),pk=object_id)
        if not self.has_view_permission(request,obj): raise PermissionDenied
        return super().history_form_view(request,object_id,version_id,extra_context)

@admin.register(Article)
class ArticleAdmin(ReadOnlyHistoryAdmin):
    form=ArticleAdminForm
    list_display = ['title','category','author','status','published_at','featured']
    list_filter = ['status','category','featured']
    search_fields = ['title','summary']
    prepopulated_fields = {'slug':('title',)}
    filter_horizontal = ['tags']
    date_hierarchy = 'published_at'
    readonly_fields = ['updated_at','owner','preview_link']
    change_list_template = 'admin/news/article_change_list.html'
    change_form_template = 'admin/news/article_change_form.html'
    class Media:
        js = ('recovery.js',)
    list_select_related = ['category','author']
    actions = ['submit_for_review']
    fieldsets = [('Story',{'fields':('title','slug','summary','body')}),('Attribution',{'fields':('author','category','tags','owner')}),('Photography',{'fields':('media_asset','image','image_alt','image_credit')}),('Assignment',{'fields':('deadline','assignment_notes'),'classes':('collapse',)}),('Publishing',{'fields':('status','published_at','featured','breaking','editors_pick','preview_link')}),('Search appearance',{'fields':('seo_title','seo_description','updated_at'),'classes':('collapse',)})]
    def get_urls(self):
        from . import newsroom
        custom=[
            path('desk/',self.admin_site.admin_view(lambda request: newsroom.desk(request,self.admin_site)),name='news_article_desk'),
            path('recovery/<uuid:key>/',self.admin_site.admin_view(newsroom.recovery),name='news_article_recovery'),
            path('recovery/<uuid:key>/discard/',self.admin_site.admin_view(newsroom.discard_recovery),name='news_article_discard_recovery'),
            path('<int:pk>/workspace/',self.admin_site.admin_view(lambda request,pk: newsroom.workspace(request,pk,self.admin_site)),name='news_article_workspace'),
            path('<int:pk>/restore/<int:version>/',self.admin_site.admin_view(lambda request,pk,version: newsroom.restore_revision(request,pk,version,self.admin_site)),name='news_article_restore_revision'),
        ]
        return custom+super().get_urls()
    def render_change_form(self,request,context,add=False,change=False,form_url='',obj=None):
        import uuid
        context['recovery_enabled']=True
        recovery=None
        key=request.GET.get('recovery') or request.POST.get('recovery_key')
        if key:
            recovery=DraftRecovery.objects.filter(pk=key,user=request.user).first()
            if recovery and recovery.article_id and (not obj or recovery.article_id != obj.pk): recovery=None
        if recovery is None and obj and obj.pk:
            recovery=DraftRecovery.objects.filter(user=request.user,article=obj).first()
        context['recovery_id']=recovery.pk if recovery else uuid.uuid4()
        context['loaded_version']=obj.updated_at.isoformat() if obj and obj.pk else ''
        return super().render_change_form(request,context,add,change,form_url,obj)
    @admin.display(description='Preview')
    def preview_link(self,obj):
        if not obj.pk: return 'Save the draft to preview it.'
        from django.utils.html import format_html
        from django.urls import reverse
        return format_html('<a href="{}" target="_blank" rel="noopener">Open private preview</a>',reverse('preview',args=[obj.pk]))
    def get_queryset(self,request):
        qs=super().get_queryset(request)
        return qs if request.user.has_perm('news.publish_article') else qs.filter(owner=request.user)
    def get_readonly_fields(self,request,obj=None):
        fields = list(super().get_readonly_fields(request,obj))
        if not request.user.has_perm('news.publish_article'): fields += ['status','published_at','featured','breaking','editors_pick']
        return fields
    def has_view_permission(self,request,obj=None):
        if obj and not request.user.has_perm('news.publish_article') and obj.owner_id != request.user.pk: return False
        return super().has_view_permission(request,obj)
    def has_change_permission(self,request,obj=None):
        if obj and not request.user.has_perm('news.publish_article') and (obj.status == 'published' or obj.owner_id != request.user.pk): return False
        return super().has_change_permission(request,obj)
    def has_delete_permission(self,request,obj=None):
        return request.user.has_perm('news.publish_article') and super().has_delete_permission(request,obj)
    def save_model(self,request,obj,form,change):
        if not obj.owner_id: obj.owner=request.user
        super().save_model(request,obj,form,change)
        key=request.POST.get('recovery_key')
        if key:
            copies=DraftRecovery.objects.filter(pk=key,user=request.user)
            copies=copies.filter(article=obj) if change else copies.filter(article__isnull=True)
            copies.delete()
    @admin.action(description='Submit selected drafts for editorial review',permissions=['change'])
    def submit_for_review(self,request,queryset):
        count=0
        for item in queryset.filter(status='draft'):
            if not self.has_change_permission(request,item): continue
            item.status='review'; item._history_user=request.user; item.save(); count+=1
        self.message_user(request,f'{count} stories submitted for review.')

@admin.register(Category,Tag,Author)
class NamedAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug':('name',)}
    search_fields = ['name']

@admin.register(Page)
class PageAdmin(ReadOnlyHistoryAdmin):
    list_display=['title','published','position','updated_at']
    prepopulated_fields={'slug':('title',)}
    readonly_fields=['updated_at']
    fieldsets=[('Page content',{'fields':['title','slug','body','published','position']}),('Search appearance',{'fields':['seo_title','seo_description','updated_at'],'classes':['collapse']})]

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['email','active','created_at','confirmed_at']
    list_filter = ['active']
    search_fields = ['email']
    readonly_fields = ['email','active','created_at','confirmed_at','token_version']
    def has_add_permission(self,request): return False

@admin.register(ReaderMessage)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['subject','name','created_at','resolved']
    list_filter = ['resolved']
    readonly_fields = ['name','email','subject','message','created_at']

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display=['subject','created_at','queued_at']
    readonly_fields=['queued_at','created_at']
    actions=['queue_selected']
    def has_change_permission(self,request,obj=None):
        return (not obj or not obj.queued_at) and super().has_change_permission(request,obj)
    def has_send_permission(self,request): return request.user.has_perm('news.send_campaign')
    @admin.action(description='Queue selected newsletters to confirmed subscribers',permissions=['send'])
    def queue_selected(self,request,queryset):
        if not self.has_send_permission(request): raise PermissionDenied
        # Django action confirmation requires an explicit second submission.
        if not request.POST.get('confirm_send'):
            from django.template.response import TemplateResponse
            return TemplateResponse(request,'admin/confirm_campaign.html',dict(self.admin_site.each_context(request),campaigns=queryset,action='queue_selected',title='Confirm newsletter delivery'))
        for campaign in queryset:
            try: count=queue_campaign(campaign.pk)
            except ValueError as exc: self.message_user(request,str(exc),level=messages.ERROR)
            else: self.message_user(request,f'{count} messages queued for {campaign.subject}.')
@admin.register(AdPlacement)
class AdPlacementAdmin(admin.ModelAdmin):
    list_display = ['label','placement','active','destination']
    list_filter = ['position','active']
    list_editable = ['active']
    search_fields = ['label','destination']
    readonly_fields = ['preview']
    ordering = ['position','label']
    fieldsets = [(None,{'fields':['label','position','destination','image','preview','active'],'description':'Choose a site position, upload the advertiser-approved banner, add its destination URL, then activate it. Current positions are the homepage banner and article sidebar. Only active placements appear publicly.'})]

    @admin.display(description='Placement')
    def placement(self,obj):
        return obj.get_position_display()

    @admin.display(description='Preview')
    def preview(self,obj):
        if not obj or not obj.image: return 'Upload a banner image to preview it.'
        from django.utils.html import format_html
        return format_html('<img src="{}" alt="{}" style="max-width:520px;max-height:180px;width:auto;height:auto">',obj.image.url,obj.label)

@admin.register(StoryComment)
class StoryCommentAdmin(admin.ModelAdmin):
    list_display=['created_at','display_name','article','status','moderated_by']
    list_filter=['status','created_at']
    search_fields=['display_name','body','article__title']
    date_hierarchy='created_at'
    readonly_fields=['article','display_name','body','status','created_at','moderated_at','moderated_by']
    actions=['approve_comments','reject_comments']
    def has_add_permission(self,request): return False
    @admin.action(description='Approve selected comments',permissions=['change'])
    def approve_comments(self,request,queryset):
        if not request.user.has_perm('news.change_storycomment'): raise PermissionDenied
        from django.utils import timezone
        count=queryset.filter(status=StoryComment.PENDING).update(status=StoryComment.APPROVED,moderated_at=timezone.now(),moderated_by=request.user)
        self.message_user(request,f'{count} comments approved.')
    @admin.action(description='Reject selected comments',permissions=['change'])
    def reject_comments(self,request,queryset):
        if not request.user.has_perm('news.change_storycomment'): raise PermissionDenied
        from django.utils import timezone
        count=queryset.filter(status=StoryComment.PENDING).update(status=StoryComment.REJECTED,moderated_at=timezone.now(),moderated_by=request.user)
        self.message_user(request,f'{count} comments rejected.')

@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display=['title','preview','credit','rights','created_by','created_at']
    list_display_links=['title']
    search_fields=['title','alt_text','credit','rights']
    list_filter=['created_at']
    readonly_fields=['preview','created_by','created_at','thumbnail']
    fields=['title','image','thumbnail','preview','alt_text','credit','rights','created_by','created_at']
    def save_model(self,request,obj,form,change):
        if not obj.created_by_id: obj.created_by=request.user
        super().save_model(request,obj,form,change)
    @admin.display(description='Preview')
    def preview(self,obj):
        if not obj or not obj.image: return 'Upload an image to preview it.'
        from django.utils.html import format_html
        return format_html('<img src="{}" alt="{}" style="max-width:160px;height:auto">',obj.thumbnail.url if obj.thumbnail else obj.image.url,obj.alt_text)
