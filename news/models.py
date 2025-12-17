"""
お知らせ掲示板モデル
台風接近時の開催判断やタイムテーブル変更等の緊急情報を即座に全ユーザーへ周知
"""
from django.db import models
from django.utils import timezone


class News(models.Model):
    """
    お知らせモデル
    管理者がブログ感覚で記事を作成・編集・削除できる
    """
    CATEGORY_CHOICES = [
        ('info', 'お知らせ'),
        ('important', '重要'),
        ('correction', '訂正'),
        ('urgent', '緊急'),
    ]
    
    title = models.CharField('タイトル', max_length=200)
    body = models.TextField('本文')
    category = models.CharField(
        'カテゴリ',
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='info'
    )
    published_at = models.DateTimeField('公開日時', default=timezone.now)
    is_active = models.BooleanField('公開中', default=True)
    is_important = models.BooleanField(
        '重要なお知らせ',
        default=False,
        help_text='ONにすると赤色で目立つ表示になります'
    )
    
    # メタ情報
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        ordering = ['-published_at']  # 新しい順に表示
        verbose_name = 'お知らせ'
        verbose_name_plural = 'お知らせ'

    def __str__(self):
        return self.title
    
    @classmethod
    def get_active_news(cls, limit=None):
        """公開中のお知らせを取得"""
        queryset = cls.objects.filter(
            is_active=True,
            published_at__lte=timezone.now()
        )
        if limit:
            queryset = queryset[:limit]
        return queryset
