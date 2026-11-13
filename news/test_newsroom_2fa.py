from unittest import skipUnless

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django_otp.oath import totp
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from .models import Article, Author, Category
from .tests import TEST_STORAGE


@skipUnless(settings.NEWSROOM_2FA_REQUIRED, 'Requires the OTP admin site at startup.')
@override_settings(STORAGES=TEST_STORAGE, SECURE_SSL_REDIRECT=False)
class NewsroomTwoFactorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = 'preview-test-password-only'
        cls.staff = get_user_model().objects.create_superuser(
            'otp-editor', 'editor@example.com', cls.password,
        )
        cls.device = TOTPDevice.objects.create(user=cls.staff, name='Authenticator')
        cls.recovery = StaticDevice.objects.create(user=cls.staff, name='Recovery')
        cls.code = StaticToken.random_token()
        StaticToken.objects.create(device=cls.recovery, token=cls.code)
        category = Category.objects.create(name='Kenya', slug='kenya')
        author = Author.objects.create(name='News desk', slug='news-desk')
        cls.article = Article.objects.create(
            title='Draft', slug='draft', summary='Draft summary', body='<p>Draft text.</p>',
            category=category, author=author,
        )

    def sign_in(self, client, token=None, device=None):
        data = {'username': self.staff.username, 'password': self.password}
        if token is not None:
            data.update(otp_token=token, otp_device=device.persistent_id)
        return client.post(reverse('admin:login'), data)

    def test_password_alone_cannot_open_admin(self):
        self.assertEqual(self.sign_in(self.client).status_code, 200)
        self.assertRedirects(
            self.client.get(reverse('admin:index')), '/admin/login/?next=/admin/',
            fetch_redirect_response=False,
        )

    def test_authenticator_unlocks_admin_and_private_preview(self):
        preview = reverse('preview', args=[self.article.pk])
        self.client.force_login(self.staff)
        self.assertRedirects(
            self.client.get(preview), f'/admin/login/?next={preview}',
            fetch_redirect_response=False,
        )
        token = totp(
            self.device.bin_key, step=self.device.step, t0=self.device.t0,
            digits=self.device.digits, drift=self.device.drift,
        )
        self.assertEqual(self.sign_in(self.client, str(token).zfill(self.device.digits), self.device).status_code, 302)
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)
        self.assertEqual(self.client.get(preview).status_code, 200)

    def test_recovery_code_can_only_be_used_once(self):
        self.assertEqual(self.sign_in(self.client, self.code, self.recovery).status_code, 302)
        self.assertFalse(StaticToken.objects.filter(device=self.recovery).exists())
        second_client = Client()
        self.assertEqual(self.sign_in(second_client, self.code, self.recovery).status_code, 200)
        self.assertEqual(second_client.get(reverse('admin:index')).status_code, 302)
