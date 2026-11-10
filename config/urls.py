from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path
from news import views
from news.feeds import LatestFeed, ArticleSitemap
urlpatterns = [path('admin/',admin.site.urls),path('',views.home,name='home'),path('latest/',views.listing,name='latest'),path('search/',views.listing,name='search'),path('category/<slug:slug>/',views.listing,{'kind':'category'},name='category'),path('author/<slug:slug>/',views.listing,{'kind':'author'},name='author'),path('topic/<slug:slug>/',views.listing,{'kind':'tag'},name='tag'),path('story/<slug:slug>/',views.article,name='article'),path('newsletter/',views.newsletter,name='newsletter'),path('newsletter/confirm/<str:token>/',views.subscription_action,{'action':'confirm'}),path('newsletter/unsubscribe/<str:token>/',views.subscription_action,{'action':'unsubscribe'}),path('contact/',views.contact,name='contact'),path('pages/<slug:slug>/',views.page,name='page'),path('feed.xml',LatestFeed(),name='feed'),path('sitemap.xml',sitemap,{'sitemaps':{'articles':ArticleSitemap}}),path('robots.txt',views.robots),path('healthz/',views.health)]
if settings.DEBUG: urlpatterns += static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
