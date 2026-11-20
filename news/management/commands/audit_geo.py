"""Report editorial discovery gaps without changing content or contacting providers."""
import json
from django.core.management.base import BaseCommand
from news.models import Article


class Command(BaseCommand):
    help = "Audit published stories for GEO/SEO editorial gaps; not a ranking score."

    def handle(self, *args, **options):
        articles = Article.objects.live().prefetch_related("public_sources")
        count = 0
        for article in articles.iterator(chunk_size=100):
            gaps = []
            for present, label in (
                (article.summary.strip(), "summary"),
                (article.author.bio.strip(), "author biography"),
                (article.key_fact_lines, "key facts (optional)"),
                (article.public_sources.all(), "public citations (where appropriate)"),
                (article.seo_description.strip(), "custom meta description (summary fallback exists)"),
                (article.display_image, "image"),
            ):
                if not present:
                    gaps.append(label)
            self.stdout.write(json.dumps({"url": article.get_absolute_url(), "review": gaps}, ensure_ascii=False))
            count += 1
        self.stdout.write(json.dumps({"published_stories_checked": count}))
