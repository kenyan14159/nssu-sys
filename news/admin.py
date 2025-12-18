"""
お知らせ管理画面
初心者でも使いやすい管理画面を提供
ブログ感覚で記事を作成・編集・削除
"""
from django.contrib import admin, messages
from django.utils.html import format_html

from .models import News

# =============================================================================
# 管理アクション
# =============================================================================

@admin.action(description="選択したお知らせを公開")
def publish_news(modeladmin, request, queryset):
    """お知らせを一括公開"""
    count = queryset.update(is_active=True)
    messages.success(request, f'{count}件のお知らせを公開しました。')


@admin.action(description="選択したお知らせを非公開")
def unpublish_news(modeladmin, request, queryset):
    """お知らせを一括非公開"""
    count = queryset.update(is_active=False)
    messages.success(request, f'{count}件のお知らせを非公開にしました。')


@admin.action(description="⚠ 選択したお知らせを重要に設定")
def mark_important(modeladmin, request, queryset):
    """お知らせを重要に設定"""
    count = queryset.update(is_important=True)
    messages.success(request, f'{count}件のお知らせを重要に設定しました。')


@admin.action(description="選択したお知らせの重要を解除")
def unmark_important(modeladmin, request, queryset):
    """お知らせの重要を解除"""
    count = queryset.update(is_important=False)
    messages.success(request, f'{count}件のお知らせの重要を解除しました。')


# =============================================================================
# お知らせ管理
# =============================================================================

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    """お知らせ管理（大幅強化版）"""
    list_display = [
        'title', 
        'category_badge', 
        'is_important_badge',
        'is_active_badge', 
        'published_at',
        'body_preview'
    ]
    list_filter = ['category', 'is_active', 'is_important', 'published_at']
    search_fields = ['title', 'body']
    date_hierarchy = 'published_at'
    ordering = ['-published_at']
    list_per_page = 20
    actions = [publish_news, unpublish_news, mark_important, unmark_important]
    
    fieldsets = [
        ('記事内容', {
            'fields': ['title', 'body'],
            'description': 'タイトルと本文を入力してください。本文はマークダウン形式で記述できます。'
        }),
        ('公開設定', {
            'fields': ['category', 'is_important', 'is_active', 'published_at'],
            'description': 'カテゴリを選択し、公開日時を設定してください。「有効」にチェックを入れると公開されます。'
        }),
    ]
    
    def category_badge(self, obj):
        """カテゴリをバッジで表示"""
        colors = {
            'info': '#17a2b8',      # 青
            'important': '#dc3545', # 赤
            'correction': '#ffc107', # 黄
            'urgent': '#dc3545',    # 赤
        }
        icons = {
            'info': 'ℹ️',
            'important': '❗',
            'correction': '✏️',
            'urgent': '🚨',
        }
        color = colors.get(obj.category, '#6c757d')
        icon = icons.get(obj.category, '')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{} {}</span>',
            color, icon, obj.get_category_display()
        )
    category_badge.short_description = 'カテゴリ'
    category_badge.admin_order_field = 'category'
    
    def is_important_badge(self, obj):
        """重要フラグをアイコンで表示"""
        if obj.is_important:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">⚠ 重要</span>'
            )
        return '-'
    is_important_badge.short_description = '重要'
    is_important_badge.admin_order_field = 'is_important'
    
    def is_active_badge(self, obj):
        """有効/無効バッジ"""
        if obj.is_active:
            return format_html('<span style="color: #28a745;">✓ 公開中</span>')
        return format_html('<span style="color: #6c757d;">非公開</span>')
    is_active_badge.short_description = '状態'
    is_active_badge.admin_order_field = 'is_active'
    
    def body_preview(self, obj):
        """本文プレビュー"""
        if obj.body:
            preview = obj.body[:50]
            if len(obj.body) > 50:
                preview += '...'
            return format_html('<small style="color: #6c757d;">{}</small>', preview)
        return '-'
    body_preview.short_description = '本文'
    is_important_badge.admin_order_field = 'is_important'
