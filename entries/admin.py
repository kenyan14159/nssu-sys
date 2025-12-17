"""
エントリー管理画面
初心者でも使いやすい管理画面を提供
"""
import csv
from decimal import Decimal
from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils.html import format_html

from .models import Entry, EntryGroup


# =============================================================================
# エントリーフォーム (デフォルト値と分秒表示対応)
# =============================================================================

class EntryAdminForm(forms.ModelForm):
    """エントリー管理フォーム - 申告タイム・自己ベストのデフォルト値設定"""
    
    class Meta:
        model = Entry
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 新規作成時のみデフォルト値を設定 (14分30秒 = 870秒)
        if not self.instance.pk:
            self.fields['declared_time'].initial = Decimal('870.00')
            self.fields['personal_best'].initial = Decimal('870.00')
    
    class Media:
        js = ('js/admin_time_display.js',)


# =============================================================================
# エントリーグループフォーム (合計金額のステップ値設定)
# =============================================================================

class EntryGroupAdminForm(forms.ModelForm):
    """エントリーグループ管理フォーム - 合計金額のステップ値を2000円に設定"""
    
    class Meta:
        model = EntryGroup
        fields = '__all__'
        widgets = {
            'total_amount': forms.NumberInput(attrs={'step': '2000', 'min': '0'}),
        }


# =============================================================================
# 管理アクション
# =============================================================================

@admin.action(description="選択したエントリーを確定")
def confirm_entries(modeladmin, request, queryset):
    """エントリーを一括確定"""
    count = queryset.update(status='confirmed')
    messages.success(request, f'{count}件のエントリーを確定しました。')


@admin.action(description="選択したエントリーを入金待ちに戻す")
def pending_entries(modeladmin, request, queryset):
    """エントリーを入金待ちに戻す"""
    count = queryset.update(status='pending')
    messages.success(request, f'{count}件のエントリーを入金待ちに戻しました。')


@admin.action(description="選択したエントリーをキャンセル")
def cancel_entries(modeladmin, request, queryset):
    """エントリーをキャンセル"""
    count = queryset.update(status='cancelled')
    messages.success(request, f'{count}件のエントリーをキャンセルしました。')


@admin.action(description="選択したエントリーをCSVでエクスポート")
def export_entries_csv(modeladmin, request, queryset):
    """エントリーをCSVでエクスポート"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="entries.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        '大会名', '種目名', '選手名', 'フリガナ', '団体名', 
        '申告タイム', 'ステータス', 'NCGスライド', '登録日時'
    ])
    
    for entry in queryset.select_related('athlete', 'race', 'race__competition', 'athlete__organization'):
        writer.writerow([
            entry.race.competition.name,
            entry.race.name,
            entry.athlete.full_name,
            entry.athlete.full_name_kana,
            entry.athlete.organization.name if entry.athlete.organization else '',
            entry.declared_time_display,
            entry.get_status_display(),
            'はい' if entry.moved_from_ncg else 'いいえ',
            entry.created_at.strftime('%Y-%m-%d %H:%M'),
        ])
    
    return response


@admin.action(description="選択したグループを確定")
def confirm_entry_groups(modeladmin, request, queryset):
    """エントリーグループを一括確定"""
    for group in queryset:
        group.confirm_all()
    messages.success(request, f'{queryset.count()}件のグループを確定しました。')


# =============================================================================
# エントリー管理
# =============================================================================

@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    """エントリー管理画面（大幅強化版）"""
    form = EntryAdminForm
    change_form_template = 'admin/entries/entry/change_form.html'
    
    list_display = (
        'athlete_link', 'athlete_org', 'race_link', 'declared_time_display',
        'status_badge', 'ncg_badge', 'created_at'
    )
    list_filter = (
        'status', 'race__competition', 'race', 
        'moved_from_ncg', 'athlete__organization'
    )
    search_fields = (
        'athlete__last_name', 'athlete__first_name', 
        'athlete__last_name_kana', 'athlete__first_name_kana',
        'athlete__organization__name', 'race__name'
    )
    raw_id_fields = ('athlete', 'race', 'registered_by', 'original_ncg_race')
    date_hierarchy = 'created_at'
    readonly_fields = ('moved_from_ncg', 'original_ncg_race', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    list_per_page = 50
    actions = [confirm_entries, pending_entries, cancel_entries, export_entries_csv]
    
    fieldsets = (
        ('エントリー情報', {
            'fields': ('athlete', 'race', 'declared_time', 'personal_best', 'note'),
            'description': '選手と種目を選択し、申告タイムを秒単位で入力してください（例: 14分30秒 → 870.00）'
        }),
        ('ステータス', {
            'fields': ('status', 'registered_by'),
            'description': 'ステータスを変更するとメール通知が送られる場合があります'
        }),
        ('NCG情報', {
            'fields': ('moved_from_ncg', 'original_ncg_race'),
            'classes': ('collapse',),
            'description': 'NCGから一般組へスライドした場合の情報'
        }),
        ('日時情報', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def athlete_link(self, obj):
        """選手名をリンクで表示"""
        return format_html(
            '<a href="/admin/accounts/athlete/{}/change/">{}</a>',
            obj.athlete.id, obj.athlete.full_name
        )
    athlete_link.short_description = '選手'
    athlete_link.admin_order_field = 'athlete__last_name_kana'
    
    def athlete_org(self, obj):
        """団体名を表示"""
        if obj.athlete.organization:
            return obj.athlete.organization.short_name or obj.athlete.organization.name[:8]
        return '-'
    athlete_org.short_description = '団体'
    athlete_org.admin_order_field = 'athlete__organization__name'
    
    def race_link(self, obj):
        """種目名をリンクで表示"""
        return format_html(
            '<a href="/admin/competitions/race/{}/change/">{}</a>',
            obj.race.id, obj.race.name
        )
    race_link.short_description = '種目'
    race_link.admin_order_field = 'race__name'
    
    def status_badge(self, obj):
        """ステータスバッジ"""
        colors = {
            'pending': '#ffc107',        # 黄
            'payment_uploaded': '#17a2b8', # 青
            'confirmed': '#28a745',      # 緑
            'cancelled': '#dc3545',      # 赤
            'dns': '#6c757d',            # グレー
        }
        icons = {
            'pending': '⏳',
            'payment_uploaded': '📤',
            'confirmed': '✓',
            'cancelled': '✗',
            'dns': '🚫',
        }
        color = colors.get(obj.status, '#6c757d')
        icon = icons.get(obj.status, '')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    status_badge.short_description = 'ステータス'
    status_badge.admin_order_field = 'status'
    
    def ncg_badge(self, obj):
        """NCGスライドバッジ"""
        if obj.moved_from_ncg:
            return format_html('<span style="color: #ffc107;">⚡ スライド</span>')
        return '-'
    ncg_badge.short_description = 'NCG'
    ncg_badge.admin_order_field = 'moved_from_ncg'
    
    def get_queryset(self, request):
        """クエリ最適化"""
        return super().get_queryset(request).select_related(
            'athlete', 'athlete__organization', 
            'race', 'race__competition', 'registered_by'
        )


# =============================================================================
# エントリーグループ管理
# =============================================================================

@admin.register(EntryGroup)
class EntryGroupAdmin(admin.ModelAdmin):
    """エントリーグループ管理画面（大幅強化版）"""
    form = EntryGroupAdminForm
    
    list_display = (
        'organization_link', 'competition_link', 'entry_count',
        'total_amount_display', 'status_badge', 'registered_by', 'created_at'
    )
    list_filter = ('status', 'competition')
    search_fields = ('organization__name', 'registered_by__full_name', 'registered_by__email')
    raw_id_fields = ('organization', 'competition', 'registered_by')
    filter_horizontal = ('entries',)
    ordering = ('-created_at',)
    list_per_page = 30
    actions = [confirm_entry_groups]
    
    fieldsets = (
        ('基本情報', {
            'fields': ('organization', 'competition', 'registered_by'),
            'description': '団体と大会を選択してください'
        }),
        ('金額情報', {
            'fields': ('total_amount',),
            'description': '合計金額（エントリー数 × 参加費）'
        }),
        ('ステータス', {
            'fields': ('status',),
        }),
        ('エントリー一覧', {
            'fields': ('entries',),
            'description': 'このグループに含まれるエントリーを選択'
        }),
    )
    
    def organization_link(self, obj):
        """団体名をリンクで表示"""
        if obj.organization:
            return format_html(
                '<a href="/admin/accounts/organization/{}/change/">{}</a>',
                obj.organization.id, obj.organization.name
            )
        return '-'
    organization_link.short_description = '団体'
    organization_link.admin_order_field = 'organization__name'
    
    def competition_link(self, obj):
        """大会名をリンクで表示"""
        return format_html(
            '<a href="/admin/competitions/competition/{}/change/">{}</a>',
            obj.competition.id, obj.competition.name[:15]
        )
    competition_link.short_description = '大会'
    competition_link.admin_order_field = 'competition__name'
    
    def entry_count(self, obj):
        """エントリー数を表示"""
        count = obj.entries.count()
        if count > 0:
            return format_html(
                '<a href="/admin/entries/entry/?entrygroup__id__exact={}">{} 件</a>',
                obj.id, count
            )
        return '0 件'
    entry_count.short_description = 'エントリー数'
    
    def total_amount_display(self, obj):
        """合計金額を表示"""
        if obj.total_amount:
            formatted_amount = f'{obj.total_amount:,}'
            return format_html(
                '<span style="font-weight: bold;">¥{}</span>',
                formatted_amount
            )
        return '¥0'
    total_amount_display.short_description = '合計金額'
    total_amount_display.admin_order_field = 'total_amount'
    
    def status_badge(self, obj):
        """ステータスバッジ"""
        colors = {
            'pending': '#ffc107',
            'payment_uploaded': '#17a2b8',
            'confirmed': '#28a745',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'ステータス'
    status_badge.admin_order_field = 'status'
    
    def get_queryset(self, request):
        """クエリ最適化"""
        return super().get_queryset(request).select_related(
            'organization', 'competition', 'registered_by'
        ).prefetch_related('entries')
