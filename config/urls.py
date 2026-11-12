from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from news import views
from news.feeds import ArticleSitemap, AuthorSitemap, CategoryFeed, CategorySitemap, LatestFeed, LiveBlogSitemap, PageSitemap, StaticSitemap, TagSitemap

urlpatterns = [
    path('newsroom/preview/<int:pk>/', views.preview, name='preview'),
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='api-docs'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='api-schema'), name='api-redoc'),
    path('api/v1/', include('news.api_urls')),
    path('', views.home, name='home'),
    path('latest/', views.listing, name='latest'),
    path('live/<slug:slug>/updates/', views.live_blog_updates, name='live_blog_updates'),
    path('live/<slug:slug>/', views.live_blog, name='live_blog'),
    path('live/', views.live_blog_list, name='live_blogs'),
    path('search/', views.listing, name='search'),
    path('category/<slug:slug>/feed.xml', CategoryFeed(), name='category_feed'),
    path('category/<slug:slug>/', views.listing, {'kind': 'category'}, name='category'),
    path('author/<slug:slug>/', views.listing, {'kind': 'author'}, name='author'),
    path('topic/<slug:slug>/', views.listing, {'kind': 'tag'}, name='tag'),
    path('story/<slug:slug>/comments/', views.story_comment, name='story_comment'),
    path('story/<slug:slug>/', views.article, name='article'),
    path('newsletter/', views.newsletter, name='newsletter'),
    path('newsletter/confirm/<str:token>/', views.subscription_action, {'action': 'confirm'}),
    path('newsletter/unsubscribe/<str:token>/', views.subscription_action, {'action': 'unsubscribe'}),
    path('contact/', views.contact, name='contact'),
    path('pages/<slug:slug>/', views.page, name='page'),
    path('feed.xml', LatestFeed(), name='feed'),
    path('sitemap.xml', sitemap, {'sitemaps': {
        'static': StaticSitemap,
        'articles': ArticleSitemap,
        'live-coverage': LiveBlogSitemap,
        'categories': CategorySitemap,
        'authors': AuthorSitemap,
        'topics': TagSitemap,
        'pages': PageSitemap,
    }}),
    path('robots.txt', views.robots),
    path('healthz/', views.health),
    path('ads.txt', views.ads_txt, name='ads_txt'),
]
if settings.DEBUG: urlpatterns += static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
