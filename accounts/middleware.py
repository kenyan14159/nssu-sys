"""
カスタムミドルウェア - セッションタイムアウト、セキュリティログ
"""
import logging
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.utils import timezone

security_logger = logging.getLogger('security')


class SessionIdleTimeoutMiddleware:
    """
    セッションアイドルタイムアウトミドルウェア
    一定時間操作がない場合、再認証を求める
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # アイドルタイムアウト（デフォルト30分）
        self.timeout = getattr(settings, 'SESSION_IDLE_TIMEOUT', 1800)
    
    def __call__(self, request):
        if request.user.is_authenticated:
            current_time = timezone.now()
            last_activity = request.session.get('last_activity')
            
            if last_activity:
                last_activity_time = datetime.fromisoformat(last_activity)
                if timezone.is_naive(last_activity_time):
                    last_activity_time = timezone.make_aware(last_activity_time)
                
                elapsed = (current_time - last_activity_time).total_seconds()
                
                if elapsed > self.timeout:
                    # セッションタイムアウト
                    security_logger.info(
                        f"Session idle timeout: user={request.user.email}, "
                        f"elapsed={elapsed:.0f}s, ip={self._get_client_ip(request)}"
                    )
                    logout(request)
                    messages.warning(request, '一定時間操作がなかったため、ログアウトしました。')
                    
            # 最終アクティビティ時刻を更新
            request.session['last_activity'] = current_time.isoformat()
        
        response = self.get_response(request)
        return response
    
    def _get_client_ip(self, request):
        """クライアントIPアドレスを取得"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


class SecurityLoggingMiddleware:
    """
    セキュリティログミドルウェア
    認可エラー（403）、入力検証エラー（400）をログに記録
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # 403 Forbidden のログ
        if response.status_code == 403:
            security_logger.warning(
                f"Authorization denied: user={getattr(request.user, 'email', 'anonymous')}, "
                f"path={request.path}, method={request.method}, "
                f"ip={self._get_client_ip(request)}"
            )
        
        # 400 Bad Request のログ
        if response.status_code == 400:
            security_logger.warning(
                f"Bad request: user={getattr(request.user, 'email', 'anonymous')}, "
                f"path={request.path}, method={request.method}, "
                f"ip={self._get_client_ip(request)}"
            )
        
        return response
    
    def _get_client_ip(self, request):
        """クライアントIPアドレスを取得"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
