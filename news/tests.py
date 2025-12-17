"""
お知らせ機能のテスト
"""
from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import News


class NewsModelTest(TestCase):
    """Newsモデルのテスト"""
    
    def setUp(self):
        """テストデータの作成"""
        self.news1 = News.objects.create(
            title='テストお知らせ1',
            body='本文1',
            category='info',
            is_active=True,
            is_important=False
        )
        self.news2 = News.objects.create(
            title='重要なお知らせ',
            body='本文2',
            category='important',
            is_active=True,
            is_important=True
        )
        self.news3 = News.objects.create(
            title='非公開のお知らせ',
            body='本文3',
            is_active=False
        )
        # 未来の公開日時を設定
        self.news_future = News.objects.create(
            title='予約投稿',
            body='本文4',
            published_at=timezone.now() + timedelta(days=1),
            is_active=True
        )
    
    def test_str_method(self):
        """__str__メソッドのテスト"""
        self.assertEqual(str(self.news1), 'テストお知らせ1')
    
    def test_get_active_news(self):
        """公開中のお知らせ取得テスト"""
        active_news = News.get_active_news()
        # 公開中かつ公開日時が過去のもののみ
        self.assertEqual(active_news.count(), 2)
        self.assertIn(self.news1, active_news)
        self.assertIn(self.news2, active_news)
        self.assertNotIn(self.news3, active_news)
        self.assertNotIn(self.news_future, active_news)
    
    def test_get_active_news_with_limit(self):
        """件数制限付きでお知らせ取得"""
        active_news = News.get_active_news(limit=1)
        self.assertEqual(len(active_news), 1)
    
    def test_ordering(self):
        """新しい順にソートされていることを確認"""
        news_list = list(News.objects.all())
        for i in range(len(news_list) - 1):
            self.assertGreaterEqual(
                news_list[i].published_at, 
                news_list[i+1].published_at
            )


class NewsViewTest(TestCase):
    """Newsビューのテスト"""
    
    def setUp(self):
        """テストデータの作成"""
        self.client = Client()
        self.news = News.objects.create(
            title='テストニュース',
            body='テスト本文です。',
            category='info',
            is_active=True
        )
    
    def test_news_list_view(self):
        """お知らせ一覧ページのテスト"""
        response = self.client.get(reverse('news:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テストニュース')
    
    def test_news_detail_view(self):
        """お知らせ詳細ページのテスト"""
        response = self.client.get(reverse('news:detail', kwargs={'pk': self.news.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テストニュース')
        self.assertContains(response, 'テスト本文です。')
    
    def test_inactive_news_not_shown(self):
        """非公開のお知らせは詳細ページで404"""
        inactive_news = News.objects.create(
            title='非公開',
            body='非公開本文',
            is_active=False
        )
        response = self.client.get(reverse('news:detail', kwargs={'pk': inactive_news.pk}))
        self.assertEqual(response.status_code, 404)
