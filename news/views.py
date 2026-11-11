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
from django.utils.html import strip_tags
from django.utils.text import Truncator
from .models import Article, ArticleURL, Category, Author, Tag, Subscription, Page, StoryComment
from .forms import SubscribeForm, ContactForm, StoryCommentForm


def json_ld(data):
    return json.dumps(data, ensure_ascii=False).replace('<', r'\u003c')


def organization_schema(logo_url):
    return {
        '@type': 'Organization',
        '@id': settings.SITE_URL + '/#organization',
        'name': 'Cedarmond TV',
        'url': settings.SITE_URL + '/',
        'logo': {
            '@type': 'ImageObject',
            'url': logo_url,
            'width': 512,
            'height': 512,
        },
    }


def absolute_image_url(image):
    if not image:
        return None
    try:
        return settings.SITE_URL + image.url
    except ValueError:
        return None


def branded_title(title):
    suffix = ' | Cedarmond TV'
    return f'{Truncator(title).chars(70 - len(suffix))}{suffix}'


def home(request):
    live = Article.objects.live()
    lead = live.filter(featured=True).first() or live.first()
    rest = live.exclude(pk=lead.pk) if lead else live
    top_stories = list(rest[:2])
    latest = list(rest[2:7])
    stories = list(rest[7:13])
    already_shown = [item.pk for item in ([lead] if lead else []) + top_stories + latest + stories]
    logo_url = settings.SITE_URL + settings.STATIC_URL + 'cedarmond-mark.svg'
    publisher = organization_schema(logo_url)
    website_schema = {
        '@context': 'https://schema.org',
        '@graph': [
            publisher,
            {
                '@type': 'WebSite',
                '@id': settings.SITE_URL + '/#website',
                'url': settings.SITE_URL + '/',
                'name': 'Cedarmond TV',
                'alternateName': 'Cedarmond TV Kenya',
                'inLanguage': 'en-KE',
                'publisher': {'@id': settings.SITE_URL + '/#organization'},
            },
        ],
    }
    context = {
        'lead': lead,
        'top_stories': top_stories,
        'latest': latest,
        'stories': stories,
        'picks': list(live.filter(editors_pick=True).exclude(pk__in=already_shown)[:3]),
        'has_supporting_stories': bool(top_stories or latest),
        'seo_title': 'Cedarmond TV | Kenyan News, Politics, Business & Culture',
        'seo_description': 'Independent journalism and original reporting from Kenya. Read the latest news, politics, business, county, culture and sports coverage.',
        'seo_image': absolute_image_url(lead.display_image) if lead and lead.display_image else logo_url,
        'seo_image_alt': lead.display_alt if lead and lead.display_image else 'Cedarmond TV',
        'website_schema_json': json_ld(website_schema),
    }
    return render(request, 'news/home.html', context)

def listing(request,kind=None,slug=None):
    articles = Article.objects.live()
    title, description = 'Latest stories', 'The latest original reporting from the Cedarmond TV newsroom.'
    if kind == 'category':
        obj = get_object_or_404(Category,slug=slug); articles = articles.filter(category=obj); title = obj.name
        description = f'Latest {obj.name.lower()} news and reporting from Cedarmond TV.'
    elif kind == 'author':
        obj = get_object_or_404(Author,slug=slug); articles = articles.filter(author=obj); title = obj.name
        description = obj.bio or f'Articles and original reporting by {obj.name} for Cedarmond TV.'
    elif kind == 'tag':
        obj = get_object_or_404(Tag,slug=slug); articles = articles.filter(tags=obj); title = obj.name
        description = f'Latest stories about {obj.name} from Cedarmond TV.'
    query = request.GET.get('q','').strip()[:120]
    if query:
        articles = articles.filter(Q(title__icontains=query)|Q(summary__icontains=query)|Q(body__icontains=query)|Q(author__name__icontains=query)|Q(category__name__icontains=query)|Q(tags__name__icontains=query)).distinct(); title = 'Search results'
    page=Paginator(articles,9).get_page(request.GET.get('page'))
    pagination_params=request.GET.copy()
    pagination_params.pop('page',None)
    noindex = bool(query) or request.resolver_match.url_name == 'search'
    canonical = settings.SITE_URL + request.path
    if page.number > 1 and not noindex:
        canonical += f'?page={page.number}'
    first_story = page.object_list[0] if page.object_list else None
    return render(request, 'news/list.html', {
        'page': page,
        'title': title,
        'description': description,
        'query': query,
        'pagination_query': pagination_params.urlencode(),
        'noindex': noindex,
        'canonical': canonical,
        'seo_title': branded_title(title),
        'seo_description': Truncator(strip_tags(description)).chars(160),
        'seo_image': absolute_image_url(first_story.display_image) if first_story and first_story.display_image else settings.SITE_URL + settings.STATIC_URL + 'cedarmond-mark.svg',
        'seo_image_alt': first_story.display_alt if first_story and first_story.display_image else 'Cedarmond TV',
    })

def article(request,slug):
    item = Article.objects.live().prefetch_related('tags').filter(slug=slug).first()
    if item is None:
        reservation=get_object_or_404(ArticleURL,slug=slug)
        target=get_object_or_404(Article.objects.live(),pk=reservation.article_id)
        return redirect(target.get_absolute_url(),permanent=True)
    return render_article(request,item)

def render_article(request,item,preview=False,comment_form=None,status=200):
    url = settings.SITE_URL + item.get_absolute_url()
    images = list(dict.fromkeys(filter(None, [absolute_image_url(item.display_image), absolute_image_url(item.display_thumbnail)])))
    logo_url = settings.SITE_URL + settings.STATIC_URL + 'cedarmond-mark.svg'
    schema = {
        '@context': 'https://schema.org',
        '@type': 'NewsArticle',
        '@id': url + '#article',
        'headline': item.title,
        'description': item.seo_description or item.summary,
        'datePublished': item.published_at.isoformat(),
        'dateModified': item.updated_at.isoformat(),
        'inLanguage': 'en-KE',
        'articleSection': item.category.name,
        'keywords': list(item.tags.values_list('name', flat=True)),
        'wordCount': len(strip_tags(item.body).split()),
        'isAccessibleForFree': True,
        'author': [{
            '@type': 'Person',
            'name': item.author.name,
            'url': settings.SITE_URL + item.author.get_absolute_url(),
        }],
        'publisher': organization_schema(logo_url),
        'mainEntityOfPage': {'@type': 'WebPage', '@id': url},
    }
    if images:
        schema['image'] = images
    breadcrumb_schema = {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': settings.SITE_URL + '/'},
            {'@type': 'ListItem', 'position': 2, 'name': item.category.name, 'item': settings.SITE_URL + item.category.get_absolute_url()},
            {'@type': 'ListItem', 'position': 3, 'name': item.title, 'item': url},
        ],
    }
    context = {
        'article': item,
        'preview': preview,
        'related': Article.objects.live().filter(category=item.category).exclude(pk=item.pk)[:3],
        'reader_comments': item.reader_comments.filter(status=StoryComment.APPROVED)[:50],
        'comment_count': item.reader_comments.filter(status=StoryComment.APPROVED).count(),
        'comment_form': comment_form or (None if preview else StoryCommentForm()),
        'canonical': url,
        'og_type': 'article',
        'seo_title': branded_title(item.seo_title or item.title),
        'seo_description': Truncator(strip_tags(item.seo_description or item.summary)).chars(160),
        'seo_image': absolute_image_url(item.display_image) if item.display_image else logo_url,
        'seo_image_alt': item.display_alt or 'Cedarmond TV' if item.display_image else 'Cedarmond TV',
        'noindex': preview,
        'share_url': quote(url, safe=''),
        'share_text': quote(item.title + ' ' + url, safe=''),
        'schema_json': json_ld(schema),
        'breadcrumb_schema_json': json_ld(breadcrumb_schema),
    }
    return render(request, 'news/article.html', context, status=status)

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
    title = 'The stories that matter. In your inbox.'
    description = 'Sign up for the Cedarmond briefing. Confirm your email to join.'
    return render(request,'news/form.html',{'form':form,'title':title,'description':description,'seo_title':f'{title} | Cedarmond TV','seo_description':description,'button':'Request confirmation'})

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
        response = render(request,'news/unavailable.html',{'title':'Subscription confirmed.' if action=='confirm' else 'You have been unsubscribed.'})
    else:
        response = render(request,'news/confirm.html',{'title':'Confirm subscription' if action=='confirm' else 'Unsubscribe','email':subscriber.email})
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response

@require_http_methods(['GET','POST'])
@ratelimit(key=rate_key,rate='10/h',method='POST',block=False)
def contact(request):
    form = ContactForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        if getattr(request,'limited',False) or form.cleaned_data['website'] or throttled(request,'contact_time'): form.add_error(None,'Please wait a minute before trying again.')
        else:
            form.save(); messages.success(request,'Your message has reached our editorial inbox.'); return redirect('contact')
    title = 'Talk to the newsroom'
    description = 'Send Cedarmond TV a story tip, correction, advertising enquiry or feedback.'
    return render(request,'news/form.html',{'form':form,'title':title,'description':description,'seo_title':f'{title} | Cedarmond TV','seo_description':description,'button':'Send message'})

def page(request,slug):
    item=get_object_or_404(Page,slug=slug,published=True)
    description = item.seo_description or Truncator(strip_tags(item.body)).chars(160)
    canonical = settings.SITE_URL + item.get_absolute_url()
    logo_url = settings.SITE_URL + settings.STATIC_URL + 'cedarmond-mark.svg'
    schema = {
        '@context': 'https://schema.org',
        '@type': 'WebPage',
        'name': item.seo_title or item.title,
        'description': description,
        'url': canonical,
        'dateModified': item.updated_at.isoformat(),
        'inLanguage': 'en-KE',
        'publisher': organization_schema(logo_url),
    }
    breadcrumb_schema = {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': settings.SITE_URL + '/'},
            {'@type': 'ListItem', 'position': 2, 'name': item.title, 'item': canonical},
        ],
    }
    return render(request,'news/page.html',{
        'title': item.title,
        'page': item,
        'canonical': canonical,
        'seo_title': branded_title(item.seo_title or item.title),
        'seo_description': description,
        'seo_image': logo_url,
        'seo_image_alt': 'Cedarmond TV',
        'schema_json': json_ld(schema),
        'breadcrumb_schema_json': json_ld(breadcrumb_schema),
    })

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
    return HttpResponse('User-agent: *\nDisallow: /admin/\nDisallow: /api/\nSitemap: '+settings.SITE_URL+'/sitemap.xml\n',content_type='text/plain')
