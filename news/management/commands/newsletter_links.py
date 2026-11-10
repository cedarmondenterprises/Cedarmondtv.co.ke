from django.conf import settings
from django.core import signing
from django.core.management.base import BaseCommand
class Command(BaseCommand):
    help = 'Generate an unsubscribe link for an email. Include a recipient-specific link in every campaign.'
    def add_arguments(self,parser): parser.add_argument('email')
    def handle(self,*args,**options):
        token = signing.dumps(options['email'].strip().lower(),salt='newsletter-unsubscribe')
        self.stdout.write(settings.SITE_URL+'/newsletter/unsubscribe/'+token+'/')
