from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Controle da Trigger de Peso do Container'

    def ready(self):
        from . import signals  # noqa: F401  (registra os signals)
