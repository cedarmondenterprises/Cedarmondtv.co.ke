"""Shared, read-only editorial checks; not predictions of search placement."""
def discovery_gaps(article):
    checks = (
        (article.summary.strip(), 'summary'),
        (article.author.bio.strip(), 'author biography'),
        (article.key_fact_lines, 'key facts (optional)'),
        (article.public_sources.all(), 'public citations (where appropriate)'),
        (article.seo_description.strip(), 'custom meta description (summary fallback exists)'),
        (article.display_image, 'image'),
    )
    return [label for present, label in checks if not present]


def geo_dashboard(request, site):
    from django.core.exceptions import PermissionDenied
    from django.core.paginator import Paginator
    from django.template.response import TemplateResponse
    from .models import Article
    from .permissions import accessible_articles
    if not request.user.has_perm('news.view_article'):
        raise PermissionDenied
    query = request.GET.get('q', '').strip()[:200]
    articles = accessible_articles(request.user, Article.objects.live()).prefetch_related('public_sources').order_by('-published_at', '-pk')
    if query:
        articles = articles.filter(title__icontains=query)
    page = Paginator(articles, 25).get_page(request.GET.get('page'))
    rows = [{'article': article, 'gaps': discovery_gaps(article),
             'can_edit': site._registry[Article].has_change_permission(request, article)} for article in page]
    return TemplateResponse(request, 'admin/geo.html', dict(site.each_context(request),
        title='Search and AI discovery', rows=rows, page=page, query=query))
