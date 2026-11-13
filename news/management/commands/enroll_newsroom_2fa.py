import base64
import sys

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice


class Command(BaseCommand):
    help = 'Enroll a staff account and display its authenticator key and recovery codes once.'

    def add_arguments(self, parser):
        parser.add_argument('username')

    def handle(self, *args, **options):
        if not sys.stdout.isatty():
            raise CommandError('Run enrollment from a private interactive terminal.')

        users = get_user_model()
        with transaction.atomic():
            try:
                user = users.objects.select_for_update().get(
                    username=options['username'], is_staff=True, is_active=True,
                )
            except users.DoesNotExist as exc:
                raise CommandError('Active staff account not found.') from exc

            if TOTPDevice.objects.filter(user=user).exists() or StaticDevice.objects.filter(user=user).exists():
                raise CommandError('This account already has a second factor.')

            device = TOTPDevice.objects.create(user=user, name='Authenticator', confirmed=False)
            key = base64.b32encode(device.bin_key).decode('ascii').rstrip('=')
            self.stdout.write(f'Add a time-based entry in your authenticator app. Setup key: {key}')
            code = input('Enter the current authenticator code to confirm enrollment: ').strip()
            if len(code) != device.digits or not code.isascii() or not code.isdecimal() or not device.verify_token(code):
                raise CommandError('Code did not match. Enrollment was rolled back.')
            device.confirmed = True
            device.save(update_fields=['confirmed'])

            recovery = StaticDevice.objects.create(user=user, name='Recovery codes')
            codes = [StaticToken.random_token() for _ in range(8)]
            StaticToken.objects.bulk_create([StaticToken(device=recovery, token=code) for code in codes])

        self.stdout.write('Save these one-time recovery codes in a password manager:')
        for code in codes:
            self.stdout.write(code)
