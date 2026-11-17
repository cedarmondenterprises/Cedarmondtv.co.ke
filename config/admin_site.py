from django.conf import settings
from django.urls import path
from django_otp.admin import OTPAdminAuthenticationForm
from unfold.sites import UnfoldAdminSite

class NewsroomOTPForm(OTPAdminAuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from unfold.widgets import BASE_INPUT_CLASSES
        for field in self.fields.values():
            field.widget.attrs['class'] = ' '.join(BASE_INPUT_CLASSES)
        self.fields['otp_token'].widget.attrs['autocomplete'] = 'one-time-code'
        self.fields['otp_token'].label = 'Authenticator or recovery code'


class NewsroomAdminSite(UnfoldAdminSite):
    login_form = NewsroomOTPForm if settings.NEWSROOM_2FA_REQUIRED else None
    login_template = 'admin/platform_login.html' if settings.NEWSROOM_2FA_REQUIRED else None

    def has_permission(self, request):
        return super().has_permission(request) and (
            not settings.NEWSROOM_2FA_REQUIRED or request.user.is_verified())

    def get_urls(self):
        from django_otp.plugins.otp_static.models import StaticDevice
        from django_otp.plugins.otp_totp.models import TOTPDevice
        from integrations.views import dashboard, dependency_health
        for model in (StaticDevice, TOTPDevice):
            if self.is_registered(model): self.unregister(model)
        return [
            path('integrations/', self.admin_view(lambda r: dashboard(r,self)), name='platform_integrations'),
            path('integrations/health/', self.admin_view(dependency_health), name='platform_health'),
        ] + super().get_urls()
