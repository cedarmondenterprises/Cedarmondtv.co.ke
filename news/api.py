"""Public, read-only API for published Cedarmond TV reporting."""
from django.db.models import Count, Q
from django.db.models.functions import Now
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.serializers import IntegerField, ModelSerializer, SerializerMethodField
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import OpenApiParameter, extend_schema

from .models import Article, Author, Category, Tag
from .api_support import PublicPagination


class CategorySerializer(ModelSerializer):
    article_count = IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ['name', 'slug', 'article_count']


class AuthorSerializer(ModelSerializer):
    article_count = IntegerField(read_only=True)
    url = SerializerMethodField()

    class Meta:
        model = Author
        fields = ['name', 'slug', 'bio', 'url', 'article_count']

    def get_url(self, obj) -> str:
        request = self.context.get('request')
        return request.build_absolute_uri(obj.get_absolute_url()) if request else obj.get_absolute_url()


class TagSerializer(ModelSerializer):
    article_count = IntegerField(read_only=True)

    class Meta:
        model = Tag
        fields = ['name', 'slug', 'article_count']


class ArticleCategorySerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = ['name', 'slug']


class ArticleAuthorSerializer(ModelSerializer):
    url = SerializerMethodField()

    class Meta:
        model = Author
        fields = ['name', 'slug', 'bio', 'url']

    def get_url(self, obj) -> str:
        request = self.context.get('request')
        return request.build_absolute_uri(obj.get_absolute_url()) if request else obj.get_absolute_url()


class ArticleTagSerializer(ModelSerializer):
    class Meta:
        model = Tag
        fields = ['name', 'slug']


class ArticleSerializer(ModelSerializer):
    url = SerializerMethodField()
    body_html = SerializerMethodField()
    category = ArticleCategorySerializer(read_only=True)
    author = ArticleAuthorSerializer(read_only=True)
    tags = ArticleTagSerializer(many=True, read_only=True)
    image = SerializerMethodField()
    image_thumbnail = SerializerMethodField()
    image_alt = SerializerMethodField()
    image_credit = SerializerMethodField()
    reading_minutes = IntegerField(read_only=True)
    seo_title = SerializerMethodField()
    seo_description = SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'slug', 'url', 'summary', 'body_html', 'category', 'author', 'tags',
            'image', 'image_thumbnail', 'image_alt', 'image_credit', 'published_at', 'updated_at',
            'reading_minutes', 'seo_title', 'seo_description',
        ]

    def _absolute_media_url(self, field) -> str | None:
        if not field:
            return None
        request = self.context.get('request')
        path = field.url
        return request.build_absolute_uri(path) if request else path

    def get_url(self, obj) -> str:
        request = self.context.get('request')
        return request.build_absolute_uri(obj.get_absolute_url()) if request else obj.get_absolute_url()

    def get_body_html(self, obj) -> str:
        return obj.rendered_body

    def get_image(self, obj) -> str | None:
        return self._absolute_media_url(obj.display_image)

    def get_image_thumbnail(self, obj) -> str | None:
        return self._absolute_media_url(obj.display_thumbnail)

    def get_image_alt(self, obj) -> str:
        return obj.display_alt

    def get_image_credit(self, obj) -> str:
        return obj.display_credit

    def get_seo_title(self, obj) -> str:
        return obj.seo_title or obj.title

    def get_seo_description(self, obj) -> str:
        return obj.seo_description or obj.summary


def _live_article_count_filter():
    return Q(article__status='published', article__published_at__lte=Now())


class ArticleListView(ListAPIView):
    serializer_class = ArticleSerializer
    permission_classes = [AllowAny]
    pagination_class = PublicPagination

    def get_queryset(self):
        queryset = Article.objects.live().select_related('category', 'author', 'media_asset').prefetch_related('tags')
        params = self.request.query_params
        query = params.get('q', '').strip()
        if len(query) > 120:
            raise ValidationError({'q': 'Search text must be 120 characters or fewer.'})
        for parameter, lookup in (('category', 'category__slug'), ('author', 'author__slug'), ('tag', 'tags__slug')):
            value = params.get(parameter, '').strip()
            if len(value) > 80:
                raise ValidationError({parameter: 'Filter values must be 80 characters or fewer.'})
            if value:
                queryset = queryset.filter(**{lookup: value})
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(summary__icontains=query) | Q(body__icontains=query)
                | Q(author__name__icontains=query) | Q(category__name__icontains=query)
                | Q(tags__name__icontains=query)
            ).distinct()
        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter('q', str, description='Search headlines, summaries, article text, authors, sections and topics.'),
            OpenApiParameter('category', str, description='Filter by section slug, such as politics.'),
            OpenApiParameter('author', str, description='Filter by author slug.'),
            OpenApiParameter('tag', str, description='Filter by topic slug.'),
            OpenApiParameter('page', int, description='Page number (starts at 1).'),
            OpenApiParameter('page_size', int, description='Results per page (1–50; defaults to 20).'),
        ],
        summary='List published stories',
        description='Only public stories whose publication time has arrived are returned. Results are newest first.',
        tags=['Articles'],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ArticleDetailView(RetrieveAPIView):
    serializer_class = ArticleSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        return Article.objects.live().select_related('category', 'author', 'media_asset').prefetch_related('tags')

    @extend_schema(
        summary='Get a published story',
        description='Private drafts, review submissions and future-dated stories are not exposed.',
        tags=['Articles'],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CategoryListView(ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    pagination_class = PublicPagination
    queryset = Category.objects.annotate(article_count=Count('article', filter=_live_article_count_filter(), distinct=True)).order_by('position', 'name')

    @extend_schema(summary='List news sections', tags=['Newsroom metadata'])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AuthorListView(ListAPIView):
    serializer_class = AuthorSerializer
    permission_classes = [AllowAny]
    pagination_class = PublicPagination
    queryset = Author.objects.annotate(article_count=Count('article', filter=_live_article_count_filter(), distinct=True)).filter(article_count__gt=0).order_by('name')

    @extend_schema(summary='List authors with published work', tags=['Newsroom metadata'])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class TagListView(ListAPIView):
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    pagination_class = PublicPagination
    queryset = Tag.objects.annotate(article_count=Count('article', filter=_live_article_count_filter(), distinct=True)).filter(article_count__gt=0).order_by('name')

    @extend_schema(summary='List topics used by published stories', tags=['Newsroom metadata'])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
