"""
カスタムエラーハンドラー
"""
import logging
import traceback

from django.http import JsonResponse
from django.shortcuts import render

logger = logging.getLogger(__name__)


def handler400(request, exception=None):
    """400 Bad Request"""
    context = {
        'error_code': 400,
        'error_title': '不正なリクエスト',
        'error_message': 'リクエストが正しくありません。入力内容を確認してください。',
    }
    
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'error': 'Bad Request',
            'message': context['error_message']
        }, status=400)
    
    return render(request, 'errors/error.html', context, status=400)


def handler403(request, exception=None):
    """403 Forbidden"""
    context = {
        'error_code': 403,
        'error_title': 'アクセス権限がありません',
        'error_message': 'このページにアクセスする権限がありません。',
    }
    
    logger.warning(
        f"403 Forbidden: user={request.user}, path={request.path}, "
        f"IP={request.META.get('REMOTE_ADDR')}"
    )
    
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'error': 'Forbidden',
            'message': context['error_message']
        }, status=403)
    
    return render(request, 'errors/error.html', context, status=403)


def handler404(request, exception=None):
    """404 Not Found"""
    context = {
        'error_code': 404,
        'error_title': 'ページが見つかりません',
        'error_message': f'お探しのページ「{request.path}」は存在しないか、移動した可能性があります。',
    }
    
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'error': 'Not Found',
            'message': 'リソースが見つかりません'
        }, status=404)
    
    return render(request, 'errors/error.html', context, status=404)


def handler500(request):
    """500 Internal Server Error"""
    context = {
        'error_code': 500,
        'error_title': 'サーバーエラー',
        'error_message': 'サーバーで問題が発生しました。しばらくしてから再度お試しください。',
    }
    
    # エラーログ記録
    logger.error(
        f"500 Error: user={request.user}, path={request.path}, "
        f"IP={request.META.get('REMOTE_ADDR')}\n{traceback.format_exc()}"
    )
    
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'error': 'Internal Server Error',
            'message': 'サーバーエラーが発生しました'
        }, status=500)
    
    return render(request, 'errors/error.html', context, status=500)
