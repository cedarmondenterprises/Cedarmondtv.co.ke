from django.dispatch import receiver
from anymail.signals import tracking
from news.models import Subscription

@receiver(tracking)
def suppress_undeliverable(sender, event, **kwargs):
    if event.event_type in ('bounced', 'complained') and event.recipient:
        Subscription.objects.filter(email__iexact=event.recipient).update(active=False)
