from django.conf import settings
from django.contrib.admin import AdminSite
from django_otp.admin import OTPAdminSite


class NewsroomAdminSite(OTPAdminSite if settings.NEWSROOM_2FA_REQUIRED else AdminSite):
    def get_urls(self):
        # Enrollment and recovery are handled from the trusted server console.
        from django_otp.plugins.otp_static.models import StaticDevice
        from django_otp.plugins.otp_totp.models import TOTPDevice

        for model in (StaticDevice, TOTPDevice):
            if self.is_registered(model):
                self.unregister(model)
        return super().get_urls()
