from datetime import timedelta
from io import BytesIO
import json
import tempfile
from unittest import skipUnless
from unittest.mock import patch
from django.conf import settings
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User, Group, Permission
from django.core.management import call_command
from PIL import Image
from post_office.models import Email, STATUS
from .models import Article, ArticleURL, Author, Category, Tag, Subscription, ReaderMessage, Page, Campaign, CampaignDelivery, DraftRecovery, EditorialComment, StoryComment
from .newsletter import subscription_token, queue_campaign

PRODUCTION_MAIL_CONFIG = settings.POST_OFFICE

TEST_STORAGE={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}}

@override_settings(STORAGES=TEST_STORAGE,SECURE_SSL_REDIRECT=False,RATELIMIT_ENABLE=False,NEWSLETTER_ENABLED=True,POST_OFFICE={'BACKENDS':{'default':'django.core.mail.backends.locmem.EmailBackend'},'DEFAULT_PRIORITY':'medium'})
class NewsroomTests(TestCase):
    def setUp(self):
        cache.clear()
        self.category=Category.objects.create(name='Kenya',slug='kenya')
        self.author=Author.objects.create(name='News desk',slug='news-desk')
        self.article=Article.objects.create(title='A verified story',slug='verified',summary='Context matters',body='<p>Original reporting.</p>',category=self.category,author=self.author,status='published')
    def test_home_and_reading_routes(self):
        Page.objects.create(title='About',slug='about',body='<p>Our newsroom.</p>',published=True)
        for url in ['/',self.article.get_absolute_url(),'/category/kenya/','/author/news-desk/','/latest/','/search/?q=verified','/pages/about/','/contact/','/newsletter/','/feed.xml','/sitemap.xml','/robots.txt','/healthz/']:
            self.assertEqual(self.client.get(url).status_code,200,url)
    def test_search_visibility_and_seo_metadata(self):
        response=self.client.get('/search/?q=verified')
        self.assertContains(response,'name="robots" content="noindex,follow"')
        self.assertContains(response,f'rel="canonical" href="{settings.SITE_URL}/search/"')
        robots=self.client.get('/robots.txt')
        self.assertContains(robots,f'Sitemap: {settings.SITE_URL}/sitemap.xml')
        self.assertNotContains(robots,'Disallow: /search/')
        article=self.client.get(self.article.get_absolute_url())
        self.assertContains(article,'property="og:type" content="article"')
        schema=json.loads(article.context['schema_json'])
        self.assertEqual(schema['@type'],'NewsArticle')
        self.assertEqual(schema['headline'],'A verified story')
        self.assertEqual(schema['mainEntityOfPage']['@id'],settings.SITE_URL+'/story/verified/')
        self.assertLessEqual(len(article.context['seo_title']),70)
    def test_sitemap_lists_public_content_and_excludes_private_content(self):
        topic=Tag.objects.create(name='Accountability',slug='accountability')
        self.article.tags.add(topic)
        Page.objects.create(title='About',slug='about',body='<p>Our newsroom.</p>',published=True)
        Page.objects.create(title='Draft page',slug='draft-page',body='<p>Private.</p>',published=False)
        Article.objects.create(title='Future report',slug='future-report',summary='Not live yet',body='<p>Private.</p>',category=self.category,author=self.author,status='published',published_at=timezone.now()+timedelta(days=1))
        response=self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code,200)
        for path in ['/','/latest/','/story/verified/','/category/kenya/','/author/news-desk/','/topic/accountability/','/pages/about/']:
            self.assertContains(response,settings.SITE_URL+path)
        self.assertNotContains(response,'future-report')
        self.assertNotContains(response,'draft-page')
    def test_public_api_only_exposes_live_stories_and_safe_fields(self):
        response=self.client.get('/api/v1/articles/')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['count'],1)
        item=response.json()['results'][0]
        self.assertEqual(item['slug'],'verified')
        self.assertEqual(item['category'],{'name':'Kenya','slug':'kenya'})
        for private_field in ['owner','assignment_notes','deadline','status','editorial_comments','reader_comments']:
            self.assertNotIn(private_field,item)
        self.article.status='draft';self.article.save()
        self.assertEqual(self.client.get('/api/v1/articles/').json()['count'],0)
        self.assertEqual(self.client.get('/api/v1/articles/verified/').status_code,404)
    def test_public_api_filters_and_paginates(self):
        tag=Tag.objects.create(name='Accountability',slug='accountability');self.article.tags.add(tag)
        for slug in ['second-report','third-report']:
            Article.objects.create(title=f'Report {slug}',slug=slug,summary='New reporting',body='<p>Verified context.</p>',category=self.category,author=self.author,status='published')
        self.assertEqual(self.client.get('/api/v1/articles/?category=kenya&page_size=1').json()['count'],3)
        self.assertEqual(len(self.client.get('/api/v1/articles/?tag=accountability').json()['results']),1)
        self.assertEqual(self.client.get('/api/v1/articles/?author=news-desk').json()['count'],3)
        self.assertEqual(self.client.get('/api/v1/articles/?q=Accountability').json()['count'],1)
        self.assertEqual(self.client.get('/api/v1/articles/?page_size=51').status_code,200)
        self.assertEqual(self.client.get('/api/v1/articles/?q='+('x'*121)).status_code,400)
    def test_public_api_metadata_and_self_hosted_documentation(self):
        tag=Tag.objects.create(name='Accountability',slug='accountability');self.article.tags.add(tag)
        for url in ['/api/v1/categories/','/api/v1/authors/','/api/v1/tags/']:
            self.assertEqual(self.client.get(url).status_code,200,url)
        category_results=self.client.get('/api/v1/categories/').json()['results']
        self.assertEqual(category_results[0]['article_count'],1,category_results)
        self.assertEqual(self.client.get('/api/v1/authors/').json()['results'][0]['article_count'],1)
        self.assertEqual(self.client.get('/api/v1/tags/').json()['results'][0]['article_count'],1)
        schema=self.client.get('/api/schema/?format=json')
        self.assertEqual(schema.status_code,200)
        self.assertIn('/api/v1/articles/',schema.json()['paths'])
        self.assertEqual(self.client.get('/api/docs/').status_code,200)
        self.assertEqual(self.client.get('/api/redoc/').status_code,200)
        self.assertEqual(self.client.post('/api/v1/articles/').status_code,405)
    def test_old_story_addresses_permanently_redirect_to_current_slug(self):
        self.article.slug='new-address';self.article.save()
        response=self.client.get('/story/verified/')
        self.assertEqual(response.status_code,301)
        self.assertEqual(response['Location'],'/story/new-address/')
        self.assertEqual(ArticleURL.objects.filter(article=self.article).count(),2)
    def test_homepage_uses_premium_story_cards_and_loads_card_styles(self):
        self.article.featured=True;self.article.save()
        for number in range(2):
            Article.objects.create(title=f'Additional report {number}',slug=f'additional-report-{number}',summary='Reporting from Kenya',body='<p>Verified reporting.</p>',category=self.category,author=self.author,status='published')
        response=self.client.get('/')
        self.assertContains(response,'class="story-card"')
        self.assertContains(response,'cards.css')
    def test_homepage_avoids_repeating_the_lead_story(self):
        self.article.featured=True
        self.article.editors_pick=True
        self.article.save()
        response=self.client.get('/')
        self.assertEqual(response.context['latest'],[])
        self.assertEqual(response.context['picks'],[])
        self.assertContains(response,'front-grid single-lead no-lead-image')
        self.assertEqual(response.content.decode().count(self.article.title),1)
    def test_editorial_desk_workspace_and_revision_restore_are_connected(self):
        editor=User.objects.create_superuser('desk-editor','desk@example.com','a-long-test-password')
        self.client.force_login(editor)
        self.article.status='draft';self.article.deadline=timezone.now()+timedelta(days=1);self.article.save()
        version=self.article.history.first().history_id
        self.assertEqual(self.client.get('/admin/news/article/desk/').status_code,200)
        history=self.client.get(f'/admin/news/article/{self.article.pk}/history/')
        self.assertEqual(history.status_code,200)
        self.assertContains(history,'Restore as a separate draft')
        self.assertEqual(self.client.get(f'/admin/news/article/{self.article.pk}/workspace/').status_code,200)
        response=self.client.post(f'/admin/news/article/{self.article.pk}/workspace/',{'message':'Add source attribution before publication.'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(EditorialComment.objects.get().message,'Add source attribution before publication.')
        preview=self.client.get(f'/admin/news/article/{self.article.pk}/restore/{version}/')
        self.assertEqual(preview.status_code,200)
        restored=self.client.post(f'/admin/news/article/{self.article.pk}/restore/{version}/')
        self.assertEqual(restored.status_code,302)
        copy=Article.objects.exclude(pk=self.article.pk).get()
        self.assertEqual(copy.status,'draft');self.assertEqual(copy.body,self.article.history.get(history_id=version).body)
        self.assertEqual(self.article.title,'A verified story')
    def test_draft_recovery_is_private_and_versioned(self):
        reporter=self.make_reporter();self.client.force_login(reporter)
        key='cb1baac3-0cf2-48b8-9fdc-2f0390a05bc2'
        url=f'/admin/news/article/recovery/{key}/'
        self.assertEqual(self.client.get(url).json()['version'],0)
        payload={'version':0,'article_id':None,'base_updated_at':'','data':{'title':'Recovered headline','slug':'recovered-headline','summary':'Saved privately','body':'<p>Working copy</p><script>bad()</script>','seo_title':'','seo_description':'','category':'1','author':'1','media_asset':'','tags':[]}}
        response=self.client.post(url,data=__import__('json').dumps(payload),content_type='application/json')
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(response.json()['version'],1)
        self.assertNotIn('<script>',DraftRecovery.objects.get().data['body'])
        self.client.force_login(self.make_reporter('second-reporter'))
        self.assertFalse(self.client.get(url).json()['exists'])
    def test_article_form_rejects_a_stale_edit(self):
        from .admin import ArticleAdminForm
        old=self.article.updated_at.isoformat()
        self.article.summary='Updated by another editor';self.article.save()
        form=ArticleAdminForm(data={'loaded_version':old,'recovery_key':''},instance=self.article)
        self.assertFalse(form.is_valid())
        self.assertTrue(any('changed after you opened it' in error for error in form.non_field_errors()))
    def test_article_form_renders_the_loaded_version_token(self):
        from .admin import ArticleAdminForm
        form=ArticleAdminForm(instance=self.article)
        self.assertEqual(form['loaded_version'].value(),self.article.updated_at.isoformat())
        stale_message='This story changed after you opened it.'
        posted=ArticleAdminForm(data={'loaded_version':self.article.updated_at.isoformat()},instance=self.article)
        posted.is_valid()
        self.assertFalse(any(stale_message in error for error in posted.non_field_errors()))
    def test_draft_and_future_articles_are_not_public(self):
        for status,date in [('draft',timezone.now()),('published',timezone.now()+timedelta(days=1)),('review',timezone.now())]:
            self.article.status=status; self.article.published_at=date; self.article.save()
            self.assertEqual(self.client.get(self.article.get_absolute_url()).status_code,404)
            for url in ['/','/search/?q=verified','/feed.xml','/sitemap.xml','/category/kenya/','/author/news-desk/']:
                self.assertNotContains(self.client.get(url),'A verified story')
    def test_empty_search_shows_the_search_form_without_latest_stories(self):
        response = self.client.get('/search/?q=%20')
        self.assertContains(response, '<h1>Search stories</h1>')
        self.assertContains(response, 'name="q"')
        self.assertNotContains(response, 'A verified story')
        self.assertNotContains(response, 'No stories found')

    def test_search_filters_and_pagination(self):
        self.assertContains(self.client.get('/search/?q=verified'),'A verified story')
        self.assertNotContains(self.client.get('/search/?q=unmatched'),'A verified story')
        self.assertEqual(self.client.get('/latest/?page=oops').status_code,200)
    def test_search_finds_authors_categories_and_topics(self):
        tag=Tag.objects.create(name='Accountability',slug='accountability');self.article.tags.add(tag)
        for query in ['News%20desk','Kenya','Accountability']:
            self.assertContains(self.client.get('/search/?q='+query),'A verified story')
    def test_reader_comments_are_moderated_and_html_escaped(self):
        response=self.client.post(f'/story/{self.article.slug}/comments/',{'display_name':'Reader One','body':'<script>alert(1)</script> Thoughtful point.','consent':'on','website':''})
        self.assertEqual(response.status_code,302)
        comment=StoryComment.objects.get();self.assertEqual(comment.status,StoryComment.PENDING)
        public=self.client.get(self.article.get_absolute_url())
        self.assertNotContains(public,'Thoughtful point')
        self.assertContains(public,'Reader discussion')
        editor=User.objects.create_superuser('moderator','moderator@example.com','a-long-test-password');self.client.force_login(editor)
        response=self.client.post('/admin/news/storycomment/',{'action':'approve_comments','_selected_action':[str(comment.pk)],'index':'0'})
        self.assertEqual(response.status_code,302)
        comment.refresh_from_db();self.assertEqual(comment.status,StoryComment.APPROVED);self.assertEqual(comment.moderated_by,editor)
        public=self.client.get(self.article.get_absolute_url())
        self.assertContains(public,'Thoughtful point')
        self.assertNotContains(public,'<script>alert(1)</script>')
    def test_comment_honeypot_and_missing_consent_do_not_save(self):
        url=f'/story/{self.article.slug}/comments/'
        response=self.client.post(url,{'display_name':'Spam bot','body':'Spam','consent':'on','website':'https://spam.example'})
        self.assertEqual(response.status_code,302)
        self.assertFalse(StoryComment.objects.exists())
        response=self.client.post(url,{'display_name':'Reader','body':'No consent','website':''})
        self.assertEqual(response.status_code,200)
        self.assertFalse(StoryComment.objects.exists())
    def test_comments_only_accept_for_live_articles(self):
        self.article.status='draft';self.article.save()
        response=self.client.post(f'/story/{self.article.slug}/comments/',{'display_name':'Reader','body':'Draft comment','consent':'on','website':''})
        self.assertEqual(response.status_code,404)
        self.assertFalse(StoryComment.objects.exists())
    def test_reporters_cannot_access_reader_comment_moderation(self):
        self.make_reporter();self.client.force_login(User.objects.get(username='reporter'))
        response=self.client.get('/admin/news/storycomment/')
        self.assertEqual(response.status_code,403)
    def test_rich_text_retains_formatting_and_removes_active_content(self):
        self.article.title='</script><script>alert(1)</script>'
        self.article.body='<h2>Context</h2><p><strong>Important</strong></p><script>alert(1)</script><a href="javascript:alert(1)">bad</a>'
        self.article.save(); self.article.refresh_from_db()
        self.assertNotIn('<script>',self.article.body)
        response=self.client.get(self.article.get_absolute_url())
        self.assertNotContains(response,'<script>alert(1)</script>')
        self.assertNotContains(response,'href="javascript:')
        self.assertContains(response,'<strong>Important</strong>')
    def test_revision_history_records_changes(self):
        self.article.title='Updated headline'; self.article.save()
        self.assertEqual(self.article.history.count(),2)
        self.assertEqual(self.article.history.last().title,'A verified story')
    def test_newsletter_confirmation_queue_delivery_and_unsubscribe(self):
        self.client.post('/newsletter/',{'email':'reader@example.com'})
        self.assertFalse(Subscription.objects.exists())
        response=self.client.post('/newsletter/',{'email':'reader@example.com','consent':'on'})
        self.assertEqual(response.status_code,302)
        subscriber=Subscription.objects.get(); self.assertFalse(subscriber.active)
        queued=Email.objects.get(); self.assertEqual(queued.status,STATUS.queued)
        queued.dispatch(); self.assertEqual(len(mail.outbox),1)
        token=subscription_token(subscriber,'confirm'); url='/newsletter/confirm/'+token+'/'
        self.client.get(url); subscriber.refresh_from_db(); self.assertFalse(subscriber.active)
        self.client.post(url); subscriber.refresh_from_db(); self.assertTrue(subscriber.active)
        token=subscription_token(subscriber,'unsubscribe')
        self.client.post('/newsletter/unsubscribe/'+token+'/')
        subscriber.refresh_from_db(); self.assertFalse(subscriber.active)
        self.assertEqual(self.client.post(url).status_code,404) # Old confirmation cannot resubscribe.
    def test_invalid_confirmation_rejected(self):
        self.assertEqual(self.client.post('/newsletter/confirm/invalid/').status_code,404)
    @override_settings(NEWSLETTER_ENABLED=False)
    def test_disabled_newsletter_is_not_advertised(self):
        self.assertNotContains(self.client.get('/'),'Join the briefing')
        self.assertEqual(self.client.get('/newsletter/').status_code,503)
    def test_contact_storage_and_throttle(self):
        data={'name':'Reader','email':'reader@example.com','subject':'Correction','message':'Please review.'}
        self.assertEqual(self.client.post('/contact/',data).status_code,302)
        self.client.post('/contact/',data)
        self.assertEqual(ReaderMessage.objects.count(),1)
    def test_csrf_is_required(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post('/contact/',{'name':'Reader'}).status_code,403)
    def test_admin_requires_login(self):
        self.assertEqual(self.client.get('/admin/news/article/').status_code,302)
    def make_reporter(self,name='reporter'):
        call_command('setup_newsroom',verbosity=0)
        user=User.objects.create_user(name,password='a-long-test-password',is_staff=True)
        user.groups.add(Group.objects.get(name='Reporter'))
        return user
    def test_reporter_cannot_edit_published_articles(self):
        user=self.make_reporter(); self.article.owner=user; self.article.save()
        self.client.force_login(user)
        response=self.client.post(f'/admin/news/article/{self.article.pk}/change/',{'title':'Tampered'})
        self.assertEqual(response.status_code,403)
        self.article.refresh_from_db(); self.assertEqual(self.article.title,'A verified story')
    def test_reporters_see_only_their_own_drafts_and_can_submit_review(self):
        user=self.make_reporter(); other=self.make_reporter('other')
        self.article.owner=other; self.article.status='draft'; self.article.save()
        self.client.force_login(user)
        self.assertNotContains(self.client.get('/admin/news/article/'),'A verified story')
        dashboard = self.client.get('/admin/')
        self.assertNotContains(dashboard, 'A verified story')
        self.assertEqual(dashboard.context['dashboard_drafts'], 0)
        self.assertEqual(self.client.get(f'/newsroom/preview/{self.article.pk}/').status_code,404)
        self.article.owner=user; self.article.save()
        response=self.client.get(f'/newsroom/preview/{self.article.pk}/')
        self.assertContains(response,'EDITORIAL PREVIEW')
        self.assertEqual(response['X-Robots-Tag'],'noindex, nofollow')
        self.client.post('/admin/news/article/',{'action':'submit_for_review','_selected_action':[str(self.article.pk)]})
        self.article.refresh_from_db(); self.assertEqual(self.article.status,'review')
    def test_history_cannot_bypass_ownership_or_publish_permissions(self):
        owner=self.make_reporter(); other=self.make_reporter('intruder')
        self.article.owner=owner; self.article.save()
        version=self.article.history.first().history_id
        url=f'/admin/news/article/{self.article.pk}/history/{version}/'
        self.client.force_login(other)
        self.assertIn(self.client.get(url).status_code,[403,404])
        self.client.force_login(owner)
        self.assertEqual(self.client.post(url,{'title':'Reverted'}).status_code,403)

    def test_article_editor_renders(self):
        user=User.objects.create_superuser('editor','editor@example.com','a-long-test-password')
        self.client.force_login(user)
        response=self.client.get(f'/admin/news/article/{self.article.pk}/change/')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'django-prose-editor')
        form=response.context['adminform'].form
        self.assertIn('loaded_version',form.fields)
        self.assertEqual(form['loaded_version'].value(),self.article.updated_at.isoformat())
        self.assertContains(response,'loaded_version')
    def test_campaign_is_queued_once_and_only_for_confirmed_subscribers(self):
        active=Subscription.objects.create(email='confirmed@example.com',active=True)
        Subscription.objects.create(email='pending@example.com')
        campaign=Campaign.objects.create(subject='Newsroom briefing',body='Original newsletter text.')
        self.assertEqual(queue_campaign(campaign.pk),1)
        self.assertEqual(queue_campaign(campaign.pk),0)
        self.assertEqual(Email.objects.count(),1)
        email=Email.objects.get(); self.assertIn('/newsletter/unsubscribe/',email.message)
        email.dispatch(); self.assertEqual(len(mail.outbox),1)
        self.assertEqual(mail.outbox[0].to,[active.email])
    def test_failed_delivery_is_scheduled_for_retry(self):
        from post_office.mail import send_queued
        config={**PRODUCTION_MAIL_CONFIG,'BACKENDS':{'default':'django.core.mail.backends.locmem.EmailBackend'}}
        sub=Subscription.objects.create(email='retry@example.com',active=True)
        campaign=Campaign.objects.create(subject='Retry',body='Retry test.')
        queue_campaign(campaign.pk)
        with override_settings(POST_OFFICE=config),patch('post_office.models.Email.dispatch',side_effect=ConnectionError('Simulated temporary SMTP failure')):
            result=send_queued(processes=1)
        email=Email.objects.get()
        self.assertEqual(email.status,STATUS.requeued)
        self.assertGreater(email.scheduled_time,timezone.now())

    def test_unsubscribe_cancels_waiting_campaign_mail(self):
        sub=Subscription.objects.create(email='confirmed@example.com',active=True)
        campaign=Campaign.objects.create(subject='News',body='News.')
        queue_campaign(campaign.pk)
        token=subscription_token(sub,'unsubscribe')
        self.client.post('/newsletter/unsubscribe/'+token+'/')
        self.assertFalse(Email.objects.exists())
    def test_campaign_action_requires_permission_and_confirmation(self):
        user=self.make_reporter(); self.client.force_login(user)
        campaign=Campaign.objects.create(subject='News',body='News.')
        self.assertEqual(self.client.post('/admin/news/campaign/',{'action':'queue_selected','_selected_action':[campaign.pk]}).status_code,403)
        user=User.objects.create_superuser('publisher','publisher@example.com','a-long-test-password')
        self.client.force_login(user)
        response=self.client.post('/admin/news/campaign/',{'action':'queue_selected','_selected_action':[campaign.pk]})
        self.assertContains(response,'Send these newsletters?')
        self.assertFalse(Email.objects.exists())
    def test_unpublished_pages_and_absent_ad_placements_are_hidden(self):
        Page.objects.create(title='Private policy',slug='privacy',body='<p>Not published.</p>')
        self.assertEqual(self.client.get('/pages/privacy/').status_code,404)
        response=self.client.get('/')
        self.assertNotContains(response,'Private policy')
        self.assertNotContains(response,'Your brand.')
        self.assertNotContains(response,'image-placeholder')
    def test_upload_optimized_with_thumbnail(self):
        image=BytesIO(); Image.new('RGB',(2400,1600),'red').save(image,'JPEG')
        with tempfile.TemporaryDirectory() as folder,override_settings(MEDIA_ROOT=folder):
            self.article.image=SimpleUploadedFile('photo.jpg',image.getvalue(),content_type='image/jpeg')
            self.article.image_alt='A red field'; self.article.save()
            self.assertTrue(self.article.image.name.endswith('.webp'))
            self.assertTrue(self.article.thumbnail.name.endswith('.webp'))
            with Image.open(self.article.image.path) as picture:self.assertLessEqual(picture.width,1800)
            with Image.open(self.article.thumbnail.path) as picture:self.assertLessEqual(picture.width,640)
    @skipUnless(settings.REDIS_URL,'Shared cache tested in PostgreSQL/Valkey CI')
    @override_settings(RATELIMIT_ENABLE=True)
    def test_rate_limit_survives_new_cookies(self):
        cache.clear()
        data={'name':'Reader','email':'reader@example.com','subject':'General enquiry','message':'Hello.'}
        for _ in range(10): Client().post('/contact/',data)
        self.assertEqual(ReaderMessage.objects.count(),10)
        response=Client().post('/contact/',data)
        self.assertContains(response,'Please wait')
        self.assertEqual(ReaderMessage.objects.count(),10)
