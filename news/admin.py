from django.contrib import admin
from .models import Article, Category, Author, Tag, Subscription, ReaderMessage, AdPlacement
admin.site.site_header = 'Cedarmond TV · Newsroom'
admin.site.site_title = 'Cedarmond TV Newsroom'
admin.site.index_title = 'Publishing desk'

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title','category','author','status','published_at','featured','demo']
    list_filter = ['status','category','featured','demo']
    search_fields = ['title','summary','body']
    prepopulated_fields = {'slug':('title',)}
    filter_horizontal = ['tags']
    date_hierarchy = 'published_at'
    readonly_fields = ['updated_at']
    def get_readonly_fields(self,request,obj=None):
        fields = list(super().get_readonly_fields(request,obj))
        if not request.user.has_perm('news.publish_article'): fields += ['status','published_at','featured','breaking','editors_pick']
        return fields
    def has_change_permission(self,request,obj=None):
        if obj and obj.status == 'published' and not request.user.has_perm('news.publish_article'): return False
        return super().has_change_permission(request,obj)
    def has_delete_permission(self,request,obj=None):
        return request.user.has_perm('news.publish_article') and super().has_delete_permission(request,obj)

@admin.register(Category,Tag,Author)
class NamedAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug':('name',)}
    search_fields = ['name']

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['email','active','created_at']
    list_filter = ['active']
    search_fields = ['email']
    readonly_fields = ['created_at']

@admin.register(ReaderMessage)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['subject','name','created_at','resolved']
    list_filter = ['resolved']
    readonly_fields = ['name','email','subject','message','created_at']
admin.site.register(AdPlacement)
