import base64
import json
import tempfile
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User, Permission
from django.test import TestCase, override_settings, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse
from guardian.shortcuts import assign_perm
from PIL import Image
from news.models import Article, Author, Category, Subscription, BreakingNewsTicker
from news.tests import TEST_STORAGE
from news.permissions import can_edit_article
from integrations.models import PushSubscription
from integrations.search import search_articles

@override_settings(STORAGES=TEST_STORAGE, SECURE_SSL_REDIRECT=False, RATELIMIT_ENABLE=False)
class PlatformTests(TestCase):
    def setUp(self):
        self.author=Author.objects.create(name='Reporter',slug='reporter')
        self.category=Category.objects.create(name='Kenya',slug='kenya')
        self.owner=User.objects.create_user('owner',is_staff=True)
        self.staff=User.objects.create_user('staff',is_staff=True)
        self.admin=User.objects.create_superuser('platform','admin@example.com','only-test-password')
        for user in (self.owner,self.staff):
            user.user_permissions.add(*Permission.objects.filter(content_type__app_label='news',codename__in=['view_article','change_article']))
        self.story=Article.objects.create(title='Public report',slug='public',summary='Summary',body='<p>Reporting.</p>',category=self.category,author=self.author,status='published',owner=self.owner)
        self.draft=Article.objects.create(title='Confidential draft',slug='private',summary='Private',body='<p>Unpublished.</p>',category=self.category,author=self.author,owner=self.owner)

    def test_dashboard_requires_superuser(self):
        url=reverse('admin:platform_integrations')
        self.assertEqual(self.client.get(url).status_code,302)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(url).status_code,403)
        self.client.force_login(self.admin)
        response=self.client.get(url)
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['integrations']),20)

    def test_health_is_private_and_generic(self):
        self.assertEqual(self.client.get(reverse('admin:platform_health')).status_code,302)
        self.client.force_login(self.admin)
        response=self.client.get(reverse('admin:platform_health'))
        self.assertEqual(response.json(),{'status':'ok'})

    def test_taxonomy_import_cannot_bypass_roles(self):
        self.staff.user_permissions.add(Permission.objects.get(codename='change_category'))
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get('/admin/news/category/import/').status_code,403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/admin/news/category/import/').status_code,200)

    def test_guardian_grant_only_shares_selected_draft(self):
        from news.newsroom import visible_articles
        self.assertFalse(visible_articles(self.staff).exists())
        assign_perm('news.view_article',self.staff,self.draft)
        self.assertEqual(list(visible_articles(self.staff)),[self.draft])
        self.assertFalse(can_edit_article(self.staff,self.draft))
        assign_perm('news.change_article',self.staff,self.draft)
        self.assertTrue(can_edit_article(self.staff,self.draft))
        self.draft.status='published';self.draft.save()
        self.assertFalse(can_edit_article(self.staff,self.draft))

    @override_settings(MEILISEARCH_URL='http://meilisearch:7700',MEILISEARCH_KEY='test-key')
    @patch('integrations.search.client')
    def test_search_rechecks_stale_index_hits(self, client):
        client.return_value.index.return_value.search.return_value={'hits':[{'id':self.draft.pk},{'id':self.story.pk}]}
        self.assertEqual(list(search_articles('report')),[self.story])
        response=self.client.get('/search/?q=report')
        self.assertContains(response,'Public report')
        self.assertNotContains(response,'Confidential draft')

    @override_settings(MEILISEARCH_URL='http://meilisearch:7700',MEILISEARCH_KEY='test-key')
    @patch('integrations.search.client',side_effect=TimeoutError)
    def test_search_failure_uses_database(self, client):
        self.assertContains(self.client.get('/search/?q=Public'),'Public report')

    def test_external_image_url_not_prefixed(self):
        from news.views import absolute_image_url
        self.assertEqual(absolute_image_url(SimpleNamespace(url='https://media.example.com/a.webp')),'https://media.example.com/a.webp')

    def test_imagekit_keeps_original_and_card_dimensions(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            data=BytesIO();Image.new('RGB',(2400,1200)).save(data,'JPEG')
            self.story.image=SimpleUploadedFile('sample.jpg',data.getvalue(),content_type='image/jpeg')
            self.story.save()
            with Image.open(self.story.image) as image:self.assertEqual(image.size,(1800,900))
            with Image.open(self.story.thumbnail) as image:self.assertEqual(image.size,(640,320))

    def test_email_bounces_suppress_future_campaigns(self):
        from integrations.signals import suppress_undeliverable
        sub=Subscription.objects.create(email='reader@example.com',active=True)
        suppress_undeliverable(None,SimpleNamespace(event_type='bounced',recipient=sub.email))
        sub.refresh_from_db();self.assertFalse(sub.active)

    @override_settings(UMAMI_SCRIPT_URL='https://analytics.example.com/script.js',UMAMI_WEBSITE_ID='site')
    def test_analytics_url_is_inert_before_consent(self):
        response=self.client.get('/')
        self.assertContains(response,'data-umami-url="https://analytics.example.com/script.js"')
        self.assertNotContains(response,'src="https://analytics.example.com/script.js"')

    @override_settings(WEBPUSH_ENABLED=True)
    def test_push_rejects_private_endpoints_and_requires_ownership(self):
        url='/push/subscription/'
        b64=lambda b:base64.urlsafe_b64encode(b).decode().rstrip('=')
        data={'endpoint':'https://127.0.0.1/private','keys':{'auth':b64(b'a'*16),'p256dh':b64(b'b'*65)}}
        self.assertEqual(self.client.post(url,json.dumps(data),content_type='application/json').status_code,400)
        data['endpoint']='https://fcm.googleapis.com/fcm/send/test'
        response=self.client.post(url,json.dumps(data),content_type='application/json')
        self.assertEqual(response.status_code,200); token=response.json()['token']
        data['action']='delete'
        self.assertEqual(self.client.post(url,json.dumps(data),content_type='application/json').status_code,403)
        self.assertEqual(self.client.post(url,json.dumps(data),content_type='application/json',HTTP_X_SUBSCRIPTION_TOKEN=token).status_code,200)
        self.assertFalse(PushSubscription.objects.exists())

    @override_settings(WEBPUSH_ENABLED=True)
    def test_push_requires_csrf(self):
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/push/subscription/','{}',content_type='application/json').status_code,403)

    @override_settings(WEBPUSH_ENABLED=False)
    def test_push_disabled_has_no_registration_endpoint(self):
        self.assertEqual(self.client.post('/push/subscription/','{}',content_type='application/json').status_code,404)
        self.assertEqual(self.client.get('/webpush-worker.js').status_code,404)

    @override_settings(LISTMONK_URL='https://letters.example.com',LISTMONK_USERNAME='api',LISTMONK_TOKEN='secret')
    @patch('integrations.management.commands.listmonk_draft.requests.post')
    def test_listmonk_creates_only_draft_from_public_stories(self,post):
        post.return_value.status_code=200
        call_command('listmonk_draft',list_id=1,subject='The briefing')
        data=post.call_args.kwargs['json']
        self.assertIn('Public report',data['body']);self.assertNotIn('Confidential draft',data['body'])
        self.assertNotIn('status',data)
        self.assertEqual(post.call_count,1)

    def test_auditlog_tracks_ad_settings_not_subscriber_data(self):
        from auditlog.registry import auditlog
        from news.models import AdSenseConfiguration
        self.assertTrue(auditlog.contains(AdSenseConfiguration))
        self.assertFalse(auditlog.contains(Subscription))
