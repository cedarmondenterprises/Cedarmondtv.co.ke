from django.urls import path

from .api import ArticleDetailView, ArticleListView, AuthorListView, CategoryListView, TagListView

app_name = 'api'

urlpatterns = [
    path('articles/', ArticleListView.as_view(), name='article-list'),
    path('articles/<slug:slug>/', ArticleDetailView.as_view(), name='article-detail'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('authors/', AuthorListView.as_view(), name='author-list'),
    path('tags/', TagListView.as_view(), name='tag-list'),
]
