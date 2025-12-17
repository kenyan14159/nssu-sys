"""
accounts アプリケーション設定
"""
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'ユーザー管理'
    
    def ready(self):
        # シグナルを登録
        from . import signals  # noqa: F401
