"""
認証シグナル - ログイン成功/失敗のログ記録、ユーザー削除時の整合性維持
"""
import logging

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import pre_delete
from django.dispatch import receiver

security_logger = logging.getLogger('security')


def get_client_ip(request):
    """クライアントIPアドレスを取得"""
    if request is None:
        return 'unknown'
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


@receiver(user_logged_in)
def log_user_logged_in(sender, request, user, **kwargs):
    """ログイン成功時のログ記録"""
    ip = get_client_ip(request)
    security_logger.info(
        f"Login success: user={user.email}, ip={ip}, "
        f"user_agent={request.META.get('HTTP_USER_AGENT', 'unknown')[:100]}"
    )


@receiver(user_logged_out)
def log_user_logged_out(sender, request, user, **kwargs):
    """ログアウト時のログ記録"""
    if user:
        ip = get_client_ip(request)
        security_logger.info(
            f"Logout: user={user.email}, ip={ip}"
        )


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    """ログイン失敗時のログ記録"""
    ip = get_client_ip(request)
    # パスワードは記録しない（セキュリティ）
    email = credentials.get('username', 'unknown')
    security_logger.warning(
        f"Login failed: attempted_email={email}, ip={ip}, "
        f"user_agent={request.META.get('HTTP_USER_AGENT', 'unknown')[:100] if request else 'unknown'}"
    )


@receiver(pre_delete)
def cleanup_user_references(sender, instance, **kwargs):
    """
    User削除前に関連テーブルの参照をNULLに設定
    SQLiteの外部キー制約がNO ACTIONになっている場合の対策
    """
    from accounts.models import User
    
    if sender != User:
        return
    
    # auditlog_logentryのactor_idをNULLに設定
    try:
        from auditlog.models import LogEntry
        LogEntry.objects.filter(actor_id=instance.id).update(actor=None)
    except ImportError:
        pass
    
    # django_admin_logのuser_idをNULLに設定（nullable=Trueの場合）
    # ただしDjangoのLogEntryはuser_idがnullable=Falseなので、削除する
    try:
        from django.contrib.admin.models import LogEntry as AdminLogEntry
        AdminLogEntry.objects.filter(user_id=instance.id).delete()
    except Exception:
        pass

