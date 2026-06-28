from django.apps import AppConfig

class IdentityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.identity'  # <--- এখানে 'apps.' যোগ করতে হবে