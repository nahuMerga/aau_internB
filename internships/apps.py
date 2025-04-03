from django.apps import AppConfig


class InternshipsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'internships'
    
    def ready(self):
        from .tasks import start_scheduler
        start_scheduler()
