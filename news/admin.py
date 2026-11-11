from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from simple_history.admin import SimpleHistoryAdmin
from .models import Article, Category, Author, Tag, Subscription, ReaderMessage, AdPlacement, Page, Campaign
from .newsletter import queue_campaign
admin.site.site_header = 'Cedarmond TV · Newsroom'
admin.site.site_title = 'Cedarmond TV Newsroom'
admin.site.index_title = 'Publishing desk'

class ReadOnlyHistoryAdmin(SimpleHistoryAdmin):
    def history_form_view(self,request,object_id,version_id,extra_context=None):
        # The library's disabled button alone does not reject crafted POSTs.
        if request.method != 'GET': raise PermissionDenied
        from django.shortcuts import get_object_or_404
        obj=get_object_or_404(self.get_queryset(request),pk=object_id)
        if not self.has_view_permission(request,obj): raise PermissionDenied
        return super().history_form_view(request,object_id,version_id,extra_context)

@admin.register(Article)
class ArticleAdmin(ReadOnlyHistoryAdmin):
    list_display = ['title','category','author','status','published_at','featured']
    list_filter = ['status','category','featured']
    search_fields = ['title','summary']
    prepopulated_fields = {'slug':('title',)}
    filter_horizontal = ['tags']
    date_hierarchy = 'published_at'
    readonly_fields = ['updated_at','owner','preview_link']
    list_select_related = ['category','author']
    actions = ['submit_for_review']
    fieldsets = [('Story',{'fields':('title','slug','summary','body')}),('Attribution',{'fields':('author','category','tags','owner')}),('Photography',{'fields':('image','image_alt','image_credit')}),('Publishing',{'fields':('status','published_at','featured','breaking','editors_pick','preview_link')}),('Search appearance',{'fields':('seo_title','seo_description','updated_at'),'classes':('collapse',)})]
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
admin.site.register(AdPlacement)
