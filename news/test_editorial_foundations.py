import json
from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from .models import Article, Author, Category
from .views import related_reporting
from .tests import TEST_STORAGE

@override_settings(STORAGES=TEST_STORAGE, SECURE_SSL_REDIRECT=False, RATELIMIT_ENABLE=False)
class EditorialFoundationTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(name='Reporter', slug='reporter', bio='Reports on education.', role='Education reporter', reporting_interests='Schools and colleges')
        self.category = Category.objects.create(name='Kenya', slug='kenya')
        self.story = self.make('first')
        self.other = self.make('second')
        self.user = User.objects.create_superuser('editor', 'editor@example.com', 'test-only-password')

    def make(self, slug, **kwargs):
        return Article.objects.create(title=slug, slug=slug, summary='Summary', body='<p>Story</p>', category=self.category, author=self.author, status=kwargs.pop('status','published'), **kwargs)

    def test_related_reporting_filters_selected_private_and_future_stories(self):
        draft = self.make('private', status='draft')
        future = self.make('future', published_at=timezone.now()+timedelta(days=1))
        self.story.related_stories.add(draft, future, self.story, self.other)
        self.assertEqual([x.pk for x in related_reporting(self.story)], [self.other.pk])

    def test_author_profile_visible_data_and_schema_agree(self):
        response = self.client.get(self.author.get_absolute_url())
        self.assertContains(response, 'Education reporter')
        self.assertContains(response, 'Schools and colleges')
        self.assertEqual(json.loads(response.context['schema_json'])['mainEntity']['jobTitle'], self.author.role)

    def test_homepage_requires_permission_and_valid_live_selections(self):
        staff = User.objects.create_user('reporter', password='test-password', is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get('/admin/homepage/').status_code,403)
        self.client.force_login(self.user)
        payload = {'lead':self.story.pk,'top_one':self.other.pk,'top_two':'', 'sections-TOTAL_FORMS':'1','sections-INITIAL_FORMS':'1','sections-MIN_NUM_FORMS':'0','sections-MAX_NUM_FORMS':'1000','sections-0-id':self.category.pk,'sections-0-position':'4'}
        self.assertEqual(self.client.post('/admin/homepage/',payload).status_code,302)
        self.story.refresh_from_db(); self.category.refresh_from_db()
        self.assertTrue(self.story.featured)
        self.assertEqual(self.category.position,4)
        home=self.client.get('/')
        self.assertEqual(home.context['lead'].pk,self.story.pk)
        self.assertEqual(home.context['top_stories'][0].pk,self.other.pk)
        payload['top_one']=self.story.pk
        response=self.client.post('/admin/homepage/',payload)
        self.assertContains(response,'Choose a different story')
        payload['lead']=self.make('draft',status='draft').pk
        response=self.client.post('/admin/homepage/',payload)
        self.assertTrue(response.context['form'].errors)
