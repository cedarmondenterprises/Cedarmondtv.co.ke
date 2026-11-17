import json
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from news.models import Article
from integrations.models import PushSubscription

class Command(BaseCommand):
    help = 'Send an explicit story alert to opted-in browsers; dry run unless --send is supplied.'
    def add_arguments(self, parser):
        parser.add_argument('article_id',type=int); parser.add_argument('--send',action='store_true')
    def handle(self, article_id, send=False, **options):
        if not settings.WEBPUSH_ENABLED: raise CommandError('Web push is disabled.')
        item=Article.objects.live().get(pk=article_id)
        self.stdout.write(f'{PushSubscription.objects.count()} subscriptions; story {item.pk}.')
        if not send: return
        from pywebpush import webpush, WebPushException
        delivered=failed=0
        for sub in PushSubscription.objects.iterator():
            try:
                webpush({'endpoint':sub.endpoint,'keys':{'p256dh':sub.p256dh,'auth':sub.auth}},
                    data=json.dumps({'title':item.title,'body':item.summary[:180],
                        'url':settings.SITE_URL+item.get_absolute_url(),'tag':f'story-{item.pk}'}),
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={'sub':settings.VAPID_CONTACT},timeout=10)
                delivered+=1
            except WebPushException as exc:
                failed+=1
                if exc.response is not None and exc.response.status_code in (404,410): sub.delete()
        self.stdout.write(f'Delivered: {delivered}; failed: {failed}.')
