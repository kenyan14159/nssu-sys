"""
nitsys プロジェクトビュー
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from news.models import News


@staff_member_required
def admin_guide_view(request):
    """管理画面操作ガイド"""
    return render(request, 'admin/guide.html')


def index_view(request):
    """
    トップページ（ランディングページ）
    お知らせを含む競技会情報を表示
    """
    # 公開中のお知らせ（最新5件）
    news_items = News.get_active_news(limit=5)
    
    return render(request, 'index.html', {
        'news_items': news_items,
    })
