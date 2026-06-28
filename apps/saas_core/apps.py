from django.apps import AppConfig

class SaasCoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.saas_core'

    def ready(self):
        # Register signals when the app loads
        import apps.saas_core.signals.usage_signals
        import apps.saas_core.signals.tenant_signals  # <-- Ei line ti notun add hobe

        