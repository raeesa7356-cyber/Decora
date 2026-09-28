from django.apps import AppConfig


from django.apps import AppConfig

class CatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # This MUST match the full path from the project root
    name = 'apps.admin_side.catalog'
