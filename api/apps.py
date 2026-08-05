from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    verbose_name = ("Account Api")
    
    def ready(self):
        # Import signal handlers when the app is ready
        try:
            import api.views as views
        except Exception as e:
            # Log but don't fail if signals can't be imported
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to import views/signals: {e}")
