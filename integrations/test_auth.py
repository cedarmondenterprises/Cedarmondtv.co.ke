from unittest import skipUnless
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from news.tests import TEST_STORAGE

@skipUnless(settings.NEWSROOM_2FA_REQUIRED, 'Run with 2FA enabled at startup')
@override_settings(STORAGES=TEST_STORAGE,SECURE_SSL_REDIRECT=False)
class PlatformOTPTests(TestCase):
    def test_unverified_password_session_cannot_reach_integrations_or_beat(self):
        user=User.objects.create_superuser('otp-platform','otp@example.com','test-password')
        self.client.force_login(user)
        for url in (reverse('admin:platform_integrations'),reverse('admin:platform_health'),reverse('admin:geo_dashboard'),reverse('admin:homepage_editor'),'/admin/django_celery_beat/periodictask/'):
            self.assertEqual(self.client.get(url).status_code,302,url)
    def test_login_exposes_otp_field(self):
        self.assertContains(self.client.get(reverse('admin:login')),'name="otp_token"')
