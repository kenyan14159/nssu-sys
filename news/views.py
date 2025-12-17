"""
お知らせビュー
"""
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import News


def news_list(request):
    """お知らせ一覧"""
    news_items = News.get_active_news()
    paginator = Paginator(news_items, 10)  # 10件ずつ
    page = request.GET.get('page')
    news = paginator.get_page(page)
    
    return render(request, 'news/news_list.html', {
        'news': news,
    })


def news_detail(request, pk):
    """お知らせ詳細"""
    news_item = get_object_or_404(News, pk=pk, is_active=True)
    return render(request, 'news/news_detail.html', {
        'news_item': news_item,
    })
