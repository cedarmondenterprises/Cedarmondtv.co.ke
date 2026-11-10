import json
from urllib.parse import quote
from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import connection
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import Article, Category, Author, Tag, Subscription
from .forms import SubscribeForm, ContactForm

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
        articles = articles.filter(Q(title__icontains=query)|Q(summary__icontains=query)|Q(body__icontains=query)); title = 'Search results'
    return render(request,'news/list.html',{'page':Paginator(articles,9).get_page(request.GET.get('page')),'title':title,'description':description,'query':query})

def article(request,slug):
    item = get_object_or_404(Article.objects.live(),slug=slug)
    url = settings.SITE_URL + item.get_absolute_url()
    schema = {'@context':'https://schema.org','@type':'NewsArticle','headline':item.title,'description':item.summary,'datePublished':item.published_at.isoformat(),'dateModified':item.updated_at.isoformat(),'author':[{'@type':'Person','name':item.author.name,'url':settings.SITE_URL+item.author.get_absolute_url()}],'publisher':{'@type':'Organization','name':'Cedarmond TV'},'mainEntityOfPage':url}
    if item.image: schema['image'] = [settings.SITE_URL+item.image.url]
    return render(request,'news/article.html',{'article':item,'related':Article.objects.live().filter(category=item.category).exclude(pk=item.pk)[:3],'canonical':url,'share_url':quote(url,safe=''),'share_text':quote(item.title+' '+url,safe=''),'schema_json':json.dumps(schema).replace('<',r'\u003c')})

def throttled(request,key):
    now = timezone.now().timestamp()
    if now - request.session.get(key,0) < 60: return True
    request.session[key] = now
    return False

@require_http_methods(['GET','POST'])
def newsletter(request):
    form = SubscribeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if not form.cleaned_data['website'] and not throttled(request,'subscribe_time'):
            email = form.cleaned_data['email'].lower()
            token = signing.dumps(email,salt='newsletter-confirm')
            link = settings.SITE_URL+'/newsletter/confirm/'+token+'/'
            try:
                send_mail('Confirm your Cedarmond TV subscription','Confirm your subscription: '+link,settings.DEFAULT_FROM_EMAIL,[email])
            except Exception:
                form.add_error(None,'We could not send your confirmation. Please try again later.')
            else:
                Subscription.objects.get_or_create(email=email)
                messages.success(request,'Check your inbox for a confirmation link.'); return redirect('newsletter')
        else: form.add_error(None,'Please wait a minute before trying again.')
    return render(request,'news/form.html',{'form':form,'title':'The stories that matter. In your inbox.','description':'Sign up for the Cedarmond briefing. Confirm your email to join.','button':'Send confirmation'})

@require_http_methods(['GET','POST'])
def subscription_action(request,token,action):
    try: email = signing.loads(token,salt='newsletter-'+action,max_age=172800 if action=='confirm' else None)
    except signing.BadSignature: raise Http404('This link has expired or is invalid.')
    if request.method == 'POST':
        Subscription.objects.filter(email=email).update(active=action=='confirm')
        messages.success(request,'Subscription confirmed.' if action=='confirm' else 'You have been unsubscribed.')
        return redirect('newsletter')
    return render(request,'news/confirm.html',{'title':'Confirm subscription' if action=='confirm' else 'Unsubscribe','email':email})

@require_http_methods(['GET','POST'])
def contact(request):
    form = ContactForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        if form.cleaned_data['website'] or throttled(request,'contact_time'): form.add_error(None,'Please wait a minute before trying again.')
        else:
            form.save(); messages.success(request,'Your message has reached our editorial inbox.'); return redirect('contact')
    return render(request,'news/form.html',{'form':form,'title':'Talk to the newsroom','description':'Send a story tip, correction, advertising enquiry, or feedback.','button':'Send message'})

def page(request,slug):
    content = {
        'about':('Independent perspective. Kenyan at heart.','Cedarmond TV covers Kenya, its people, and the issues shaping everyday life. This is the foundation of our independent digital newsroom.'),
        'editorial-policy':('Our editorial standards','We seek primary sources, distinguish reporting from opinion, and label sponsored content. Readers can request corrections through our contact form. Demo stories are clearly labelled and are not reported news.'),
        'privacy':('Your privacy','This site stores newsletter details only after you request a subscription, and stores messages you submit to the newsroom. Essential cookies protect forms and editor sign-in. Saved stories stay in your browser. Contact us to request deletion. No advertising trackers are enabled by default. This starting policy must be reviewed before public launch.'),
        'advertise':('Reach an engaged Kenyan audience','Advertising placements are available in our masthead and sidebar. Sponsored placements are clearly labelled. Contact our team to discuss campaigns and availability.')}
    if slug not in content: raise Http404
    title,body = content[slug]
    return render(request,'news/page.html',{'title':title,'body':body})

def health(request):
    try:
        with connection.cursor() as cursor: cursor.execute('SELECT 1')
    except Exception: return JsonResponse({'status':'unavailable'},status=503)
    return JsonResponse({'status':'ok'})

def robots(request):
    return HttpResponse('User-agent: *\nDisallow: /admin/\nDisallow: /search/\nSitemap: '+settings.SITE_URL+'/sitemap.xml\n',content_type='text/plain')
