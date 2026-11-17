from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from guardian.shortcuts import assign_perm, remove_perm
from news.models import Article

class Command(BaseCommand):
    help = 'Grant/revoke access to one draft for an existing staff user; never grants publish rights.'
    def add_arguments(self, parser):
        parser.add_argument('article_id', type=int); parser.add_argument('username')
        parser.add_argument('--edit', action='store_true'); parser.add_argument('--revoke', action='store_true')
    def handle(self, article_id, username, edit=False, revoke=False, **options):
        article = Article.objects.get(pk=article_id)
        user = get_user_model().objects.get(username=username, is_staff=True, is_active=True)
        if article.status == 'published' and not revoke: raise CommandError('Only drafts and review stories can be shared.')
        for perm in (['view_article','change_article'] if edit or revoke else ['view_article']):
            (remove_perm if revoke else assign_perm)(f'news.{perm}', user, article)
        self.stdout.write('Draft access updated. Existing global model permissions still apply.')
