from django.apps import AppConfig

class IntegrationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'integrations'
    verbose_name = 'Platform integrations'

    def ready(self):
        from auditlog.registry import auditlog
        from news.models import AdSenseConfiguration, AdPlacement, BreakingNewsTicker
        # Article/Page revisions already use simple-history. Never log subscriber data or credentials.
        for model in (AdSenseConfiguration, AdPlacement, BreakingNewsTicker):
            auditlog.register(model)
        from . import signals  # noqa: F401
