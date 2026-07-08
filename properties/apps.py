from django.apps import AppConfig


class PropertiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'properties'

    def ready(self):
        # Register cache-invalidation signals for locations endpoint.
        from . import signals  # noqa: F401
