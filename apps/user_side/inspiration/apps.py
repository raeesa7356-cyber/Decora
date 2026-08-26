from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # Change this from 'accounts' to the full path:
    name = 'apps.user_side.inspiration'
