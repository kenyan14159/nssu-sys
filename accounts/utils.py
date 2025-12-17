"""
accounts ユーティリティ - 認可チェック、ログ記録用デコレータ
"""
import logging
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

security_logger = logging.getLogger('security')


def get_client_ip(request):
    """クライアントIPアドレスを取得"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def admin_required(view_func):
    """
    管理者権限が必要なビュー用デコレータ
    権限がない場合はログを記録してリダイレクト
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if not request.user.is_admin:
            security_logger.warning(
                f"Admin access denied: user={request.user.email}, "
                f"path={request.path}, ip={get_client_ip(request)}"
            )
            messages.error(request, 'この機能を使用する権限がありません。')
            return redirect('competitions:dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def log_permission_denied(request, reason=""):
    """
    権限エラーをログに記録する関数
    ビュー内で権限チェックが失敗した時に呼び出す
    """
    user_email = getattr(request.user, 'email', 'anonymous')
    security_logger.warning(
        f"Permission denied: user={user_email}, path={request.path}, "
        f"reason={reason}, ip={get_client_ip(request)}"
    )
