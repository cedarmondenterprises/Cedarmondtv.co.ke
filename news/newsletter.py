import uuid
from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone
from post_office import mail
from .models import Subscription, Campaign, CampaignDelivery

def subscription_token(subscriber,action):
    return signing.dumps({'email':subscriber.email,'version':str(subscriber.token_version)},salt='newsletter-'+action)

def subscription_url(subscriber,action):
    return settings.SITE_URL+'/newsletter/'+action+'/'+subscription_token(subscriber,action)+'/'

@transaction.atomic
def request_confirmation(email):
    subscriber,_=Subscription.objects.select_for_update().get_or_create(email=email.lower())
    if subscriber.active:
        return
    link=subscription_url(subscriber,'confirm')
    mail.send(subscriber.email,subject='Confirm your Cedarmond TV subscription',message='You requested the Cedarmond briefing. Confirm within 48 hours: '+link+'\n\nIf this was not you, ignore this email.',priority='high')

@transaction.atomic
def queue_campaign(campaign_id):
    if not settings.NEWSLETTER_ENABLED:
        raise ValueError('Configure and enable SMTP newsletters first.')
    campaign=Campaign.objects.select_for_update().get(pk=campaign_id)
    if campaign.queued_at:
        return 0
    count=0
    for subscriber in Subscription.objects.select_for_update().filter(active=True).iterator(chunk_size=200):
        delivery,created=CampaignDelivery.objects.get_or_create(campaign=campaign,subscriber=subscriber)
        if not created: continue
        link=subscription_url(subscriber,'unsubscribe')
        delivery.email=mail.send(subscriber.email,subject=campaign.subject,message=campaign.body+'\n\nUnsubscribe: '+link,headers={'List-Unsubscribe':'<'+link+'>'},priority='medium')
        delivery.save(update_fields=['email']); count+=1
    campaign.queued_at=timezone.now(); campaign.save(update_fields=['queued_at'])
    return count

@transaction.atomic
def unsubscribe(subscriber):
    subscriber=Subscription.objects.select_for_update().get(pk=subscriber.pk)
    subscriber.active=False
    subscriber.token_version=uuid.uuid4()
    subscriber.save(update_fields=['active','token_version'])
    # Cancel campaign mail still waiting in our queue. An SMTP delivery already in flight cannot be recalled.
    from post_office.models import Email, STATUS
    pending_ids=CampaignDelivery.objects.filter(subscriber=subscriber).values_list('email_id',flat=True)
    Email.objects.filter(pk__in=pending_ids,status__in=[STATUS.queued,STATUS.requeued]).delete()
