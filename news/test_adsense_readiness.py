"""Regression tests for low-value and empty-page AdSense readiness."""
from django.test import TestCase, override_settings

from .models import AdSenseConfiguration, Article, Author, Category, Page


@override_settings(SECURE_SSL_REDIRECT=False, RATELIMIT_ENABLE=False)
class AdsenseReadinessTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Kenya", slug="kenya")
        self.empty_category = Category.objects.create(name="Business", slug="business")
        self.author = Author.objects.create(name="News desk", slug="news-desk")
        self.article = Article.objects.create(
            title="A verified local story",
            slug="verified-local-story",
            summary="A reported development",
            body="<p>Directly checked reporting.</p>",
            category=self.category,
            author=self.author,
            status="published",
        )

    def test_empty_category_is_not_indexed_or_linked_from_navigation(self):
        category_page = self.client.get("/category/business/")
        self.assertEqual(category_page.status_code, 200)
        self.assertContains(category_page, 'name="robots" content="noindex,follow"')
        self.assertNotContains(category_page, '<a href="/category/business/">Business</a>')
        populated = self.client.get("/category/kenya/")
        self.assertContains(populated, 'name="robots" content="index,follow,max-image-preview:large"')

    def test_empty_live_page_is_noindex(self):
        response = self.client.get("/live/")
        self.assertContains(response, 'name="robots" content="noindex,follow"')

    def test_adsense_site_verification_does_not_enable_ad_serving(self):
        AdSenseConfiguration.objects.create(
            publisher_id="ca-pub-1234567890123456", active=False
        )
        response = self.client.get("/")
        self.assertContains(
            response, '<meta name="google-adsense-account" content="ca-pub-1234567890123456">'
        )
        self.assertNotContains(response, "pagead2.googlesyndication.com")

    def test_page_description_remains_readable_across_html_blocks(self):
        Page.objects.create(
            title="Editorial standards",
            slug="editorial-standards",
            body="<p>We check facts.</p><h2>Our process</h2><p>We publish corrections.</p>",
            published=True,
        )
        response = self.client.get("/pages/editorial-standards/")
        self.assertContains(response, 'content="We check facts. Our process We publish corrections."')

    def test_image_alt_falls_back_from_placeholder(self):
        self.article.image_alt = "."
        self.assertEqual(self.article.display_alt, self.article.title)
