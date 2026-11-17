import html
import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from news.models import Article

class Command(BaseCommand):
    help = 'Create a Listmonk newsletter draft from public articles. Does not import contacts or send mail.'
    def add_arguments(self, parser):
        parser.add_argument('--list-id',type=int,required=True)
        parser.add_argument('--subject',required=True)
    def handle(self,list_id,subject,**options):
        if not settings.LISTMONK_URL or not settings.LISTMONK_TOKEN: raise CommandError('Configure Listmonk first.')
        body=''.join(f'<h2><a href="{html.escape(settings.SITE_URL+a.get_absolute_url(),quote=True)}">{html.escape(a.title)}</a></h2><p>{html.escape(a.summary)}</p>' for a in Article.objects.live()[:10])
        if not body: raise CommandError('No public stories to include.')
        body += '<p><a href="{{ UnsubscribeURL }}">Unsubscribe</a></p>'
        response=requests.post(settings.LISTMONK_URL+'/api/campaigns',
            auth=(settings.LISTMONK_USERNAME,settings.LISTMONK_TOKEN),timeout=20,
            json={'name':subject,'subject':subject,'lists':[list_id], 'type':'regular',
                  'content_type':'html','body':body,'messenger':'email','from_email':settings.DEFAULT_FROM_EMAIL})
        if response.status_code not in (200,201): raise CommandError(f'Listmonk returned HTTP {response.status_code}; no send requested.')
        self.stdout.write('Draft created. Review recipients, unsubscribe link and content in Listmonk before sending.')
