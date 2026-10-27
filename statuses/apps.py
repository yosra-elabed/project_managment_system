from django.apps import AppConfig


class StatusesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'statuses'

    def ready(self):
        import statuses.signals  # noqa