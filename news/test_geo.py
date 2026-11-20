import json
from io import StringIO
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from .models import Article, ArticleSource, Author, Category
from .tests import TEST_STORAGE


@override_settings(STORAGES=TEST_STORAGE, SECURE_SSL_REDIRECT=False, RATELIMIT_ENABLE=False)
class GEOTests(TestCase):
    def setUp(self):
        self.article = Article.objects.create(
            title="Public reporting", slug="public-reporting", summary="A verified summary",
            body="<p>Reporting text.</p>", status="published",
            category=Category.objects.create(name="Kenya", slug="kenya"),
            author=Author.objects.create(name="Reporter", slug="reporter"),
            key_facts="First fact\n\nSecond fact",
            verification_notes="CONFIDENTIAL SOURCE",
        )

    def test_visible_facts_citations_and_matching_schema(self):
        ArticleSource.objects.create(article=self.article, title="Official report",
                                     url="https://example.org/report")
        response = self.client.get(self.article.get_absolute_url())
        self.assertContains(response, "First fact")
        self.assertContains(response, "Second fact")
        self.assertContains(response, "Official report")
        self.assertNotContains(response, "CONFIDENTIAL SOURCE")
        schema = json.loads(response.context["schema_json"])
        self.assertEqual(schema["citation"][0]["url"], "https://example.org/report")

    def test_optional_fields_do_not_create_empty_sections(self):
        self.article.key_facts = ""
        self.article.save()
        response = self.client.get(self.article.get_absolute_url())
        self.assertNotContains(response, 'id="key-facts-heading"')
        self.assertNotContains(response, 'id="sources-heading"')
        self.assertNotIn("citation", json.loads(response.context["schema_json"]))

    def test_source_url_validation_and_fact_escaping(self):
        for url in ("javascript:alert(1)", "ftp://example.org/report"):
            with self.assertRaises(ValidationError):
                ArticleSource(article=self.article, title="Bad", url=url).full_clean()
        self.article.key_facts = "<script>alert(1)</script>"
        self.article.save()
        response = self.client.get(self.article.get_absolute_url())
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_drafts_and_scheduled_articles_are_not_public_or_audited(self):
        for status, date in (("draft", timezone.now()), ("published", timezone.now()+timedelta(days=1))):
            self.article.status = status
            self.article.published_at = date
            self.article.save()
            self.assertEqual(self.client.get(self.article.get_absolute_url()).status_code, 404)
            output = StringIO()
            call_command("audit_geo", stdout=output)
            self.assertNotIn(self.article.get_absolute_url(), output.getvalue())
            self.assertIn('"published_stories_checked": 0', output.getvalue())
