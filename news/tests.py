from datetime import timedelta
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from django.core import mail, signing
from django.contrib.auth.models import User
from django.core.management import call_command
from .models import Article, Author, Category, Subscription, ReaderMessage

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}},SECURE_SSL_REDIRECT=False)
class NewsroomTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Kenya',slug='kenya')
        self.author = Author.objects.create(name='News desk',slug='news-desk')
        self.article = Article.objects.create(title='A verified story',slug='verified',summary='Context matters',body='Original reporting.',category=self.category,author=self.author,status='published')
    def test_home_and_reading_routes(self):
        for url in ['/',self.article.get_absolute_url(),'/category/kenya/','/author/news-desk/','/latest/','/search/?q=verified','/pages/about/','/pages/privacy/','/contact/','/newsletter/','/feed.xml','/sitemap.xml','/robots.txt','/healthz/']:
            self.assertEqual(self.client.get(url).status_code,200,url)
    def test_draft_and_future_articles_are_not_public(self):
        for status,date in [('draft',timezone.now()),('published',timezone.now()+timedelta(days=1)),('review',timezone.now())]:
            self.article.status=status; self.article.published_at=date; self.article.save()
            self.assertEqual(self.client.get(self.article.get_absolute_url()).status_code,404)
            for url in ['/','/search/?q=verified','/feed.xml','/sitemap.xml','/category/kenya/','/author/news-desk/']:
                self.assertNotContains(self.client.get(url),'A verified story')
    def test_search_filters_and_pagination(self):
        self.assertContains(self.client.get('/search/?q=verified'),'A verified story')
        self.assertNotContains(self.client.get('/search/?q=unmatched'),'A verified story')
        self.assertEqual(self.client.get('/latest/?page=oops').status_code,200)
    def test_content_is_escaped_including_schema(self):
        self.article.title='</script><script>alert(1)</script>'; self.article.body='<script>alert(1)</script>'; self.article.save()
        response=self.client.get(self.article.get_absolute_url())
        self.assertNotContains(response,'<script>alert(1)</script>')
    def test_newsletter_requires_consent_and_confirmation(self):
        self.client.post('/newsletter/',{'email':'reader@example.com'})
        self.assertFalse(Subscription.objects.exists())
        response=self.client.post('/newsletter/',{'email':'reader@example.com','consent':'on'})
        self.assertEqual(response.status_code,302)
        self.assertFalse(Subscription.objects.get().active)
        self.assertEqual(len(mail.outbox),1)
        token=signing.dumps('reader@example.com',salt='newsletter-confirm')
        url='/newsletter/confirm/'+token+'/'
        self.client.get(url)
        self.assertFalse(Subscription.objects.get().active)
        self.client.post(url)
        self.assertTrue(Subscription.objects.get().active)
        token=signing.dumps('reader@example.com',salt='newsletter-unsubscribe')
        self.client.post('/newsletter/unsubscribe/'+token+'/')
        self.assertFalse(Subscription.objects.get().active)
    def test_invalid_confirmation_rejected(self):
        self.assertEqual(self.client.post('/newsletter/confirm/invalid/').status_code,404)
    def test_contact_storage_and_throttle(self):
        data={'name':'Reader','email':'reader@example.com','subject':'Correction','message':'Please review.'}
        self.assertEqual(self.client.post('/contact/',data).status_code,302)
        self.client.post('/contact/',data)
        self.assertEqual(ReaderMessage.objects.count(),1)
    def test_csrf_is_required(self):
        response=Client(enforce_csrf_checks=True).post('/contact/',{'name':'Reader'})
        self.assertEqual(response.status_code,403)
    def test_admin_requires_login(self):
        self.assertEqual(self.client.get('/admin/news/article/').status_code,302)
    def test_reporter_cannot_edit_published_articles(self):
        call_command('setup_newsroom',verbosity=0)
        user=User.objects.create_user('reporter',password='a-long-test-password',is_staff=True)
        user.groups.add(__import__('django.contrib.auth.models',fromlist=['Group']).Group.objects.get(name='Reporter'))
        self.client.force_login(user)
        response=self.client.post(f'/admin/news/article/{self.article.pk}/change/',{'title':'Tampered'})
        self.assertEqual(response.status_code,403)
        self.article.refresh_from_db(); self.assertEqual(self.article.title,'A verified story')
    def test_demo_seed_is_idempotent(self):
        call_command('seed_demo',verbosity=0); call_command('seed_demo',verbosity=0)
        self.assertEqual(Article.objects.filter(demo=True).count(),12)
