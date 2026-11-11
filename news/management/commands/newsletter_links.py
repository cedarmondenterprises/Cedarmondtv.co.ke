from django.core.management.base import BaseCommand, CommandError
from news.models import Subscription
from news.newsletter import subscription_url
class Command(BaseCommand):
    help='Generate an unsubscribe URL for an existing subscriber.'
    def add_arguments(self,parser): parser.add_argument('email')
    def handle(self,*args,**options):
        try: subscriber=Subscription.objects.get(email=options['email'].strip().lower())
        except Subscription.DoesNotExist: raise CommandError('Subscriber not found.')
        self.stdout.write(subscription_url(subscriber,'unsubscribe'))
