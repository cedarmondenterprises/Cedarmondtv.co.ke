from django.db import models

class PushSubscription(models.Model):
    endpoint = models.URLField(max_length=2048, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    token_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f'Push subscription {self.pk}'
