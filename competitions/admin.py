"""
大会・種目管理画面
初心者でも使いやすい管理画面を提供
"""
import csv
from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils.html import format_html
from django.utils import timezone

from .models import Competition, Race


# =============================================================================
# 管理アクション
# =============================================================================

@admin.action(description="選択した大会を公開")
def publish_competitions(modeladmin, request, queryset):
    """大会を一括公開"""
    count = queryset.update(is_published=True)
    messages.success(request, f'{count}件の大会を公開しました。')


@admin.action(description="選択した大会を非公開")
def unpublish_competitions(modeladmin, request, queryset):
    """大会を一括非公開"""
    count = queryset.update(is_published=False)
    messages.success(request, f'{count}件の大会を非公開にしました。')


@admin.action(description="選択した大会のエントリーを開始")
def open_entry(modeladmin, request, queryset):
    """エントリー受付開始"""
    count = queryset.update(is_entry_open=True)
    messages.success(request, f'{count}件の大会のエントリー受付を開始しました。')


@admin.action(description="選択した大会のエントリーを停止")
def close_entry(modeladmin, request, queryset):
    """エントリー受付停止"""
    count = queryset.update(is_entry_open=False)
    messages.success(request, f'{count}件の大会のエントリー受付を停止しました。')


@admin.action(description="選択した種目をCSVでエクスポート")
def export_races_csv(modeladmin, request, queryset):
    """種目をCSVでエクスポート"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="races.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        '大会名', '種目名', '距離', '性別', '組定員', '表示順', 'NCG種目', '有効'
    ])
    
    for race in queryset.select_related('competition'):
        writer.writerow([
            race.competition.name,
            race.name,
            race.get_distance_display(),
            race.get_gender_display(),
            race.heat_capacity,
            race.display_order,
            'はい' if race.is_ncg else 'いいえ',
            '有効' if race.is_active else '無効',
        ])
    
    return response


@admin.action(description="🔄 選択した種目の組編成を自動生成（タイム順）")
def generate_heats_for_races(modeladmin, request, queryset):
    """選択した種目の組を自動生成"""
    from heats.models import HeatGenerator
    
    total_heats = 0
    total_entries = 0
    errors = []
    
    for race in queryset:
        try:
            # 入金待ち・確認待ちも含めて組編成
            heats = HeatGenerator.generate_heats(
                race, 
                force_regenerate=True,
                include_pending=True  # 全エントリーを対象
            )
            heat_count = len(heats)
            entry_count = sum(h.assignments.count() for h in heats)
            total_heats += heat_count
            total_entries += entry_count
            
            if heat_count > 0:
                messages.success(
                    request, 
                    f'✓ {race.name}: {heat_count}組生成（{entry_count}名）'
                )
            else:
                messages.warning(
                    request, 
                    f'⚠ {race.name}: エントリーがありません'
                )
        except Exception as e:
            errors.append(f'{race.name}: {str(e)}')
    
    if errors:
        for error in errors:
            messages.error(request, f'✗ {error}')
    
    if total_heats > 0:
        messages.info(request, f'合計: {total_heats}組、{total_entries}名を組編成しました')


# =============================================================================
# 種目インライン（大会画面から編集可能）
# =============================================================================

class RaceInline(admin.TabularInline):
    """種目インライン編集（シンプル版）"""
    model = Race
    extra = 3  # 初期表示で3行を表示
    max_num = 20  # 最大20種目まで
    fields = ('distance', 'gender', 'is_ncg', 'is_active')
    ordering = ('display_order',)
    show_change_link = True
    template = 'admin/edit_inline/tabular.html'  # Django標準テンプレートを明示的に使用
    
    class Media:
        """jazzminとの互換性のためのJavaScript"""
        js = ('admin/js/vendor/jquery/jquery.js', 'admin/js/jquery.init.js', 'admin/js/inlines.js')
    
    def formfield_for_choice_field(self, db_field, request, **kwargs):
        """混合性別を除外"""
        if db_field.name == 'gender':
            kwargs['choices'] = [
                ('M', '男子'),
                ('F', '女子'),
            ]
        return super().formfield_for_choice_field(db_field, request, **kwargs)


# =============================================================================
# 大会管理
# =============================================================================

@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    """大会管理画面（大幅強化版）"""
    list_display = (
        'name', 'event_date_display', 'entry_period_display', 
        'entry_count', 'is_published_badge', 'is_entry_open_badge'
    )
    list_filter = ('is_published', 'is_entry_open', 'event_date')
    search_fields = ('name', 'venue')
    date_hierarchy = 'event_date'
    ordering = ('-event_date',)
    list_per_page = 20
    inlines = [RaceInline]
    actions = [publish_competitions, unpublish_competitions, open_entry, close_entry]
    
    def get_inlines(self, request, obj):
        """新規追加時は種目インラインを非表示にする"""
        if obj is None:
            return []
        return self.inlines
    
    fieldsets = (
        ('大会基本情報', {
            'fields': ('name', 'description', ('event_date', 'event_end_date'), 'venue'),
            'description': '大会の基本情報を入力してください。2日間開催の場合は「開催日（最終日）」も入力してください。'
        }),
        ('エントリー期間', {
            'fields': ('entry_start_at', 'entry_end_at'),
            'description': 'エントリーの受付開始日時と締切日時を設定します'
        }),
        ('参加費・定員設定', {
            'fields': ('entry_fee', 'default_heat_capacity'),
            'description': '参加費（円）と1組あたりのデフォルト定員を設定'
        }),
        ('公開設定', {
            'fields': ('is_published', 'is_entry_open'),
            'description': '「公開中」にチェックを入れると参加者に表示されます。「エントリー受付中」にチェックを入れるとエントリーが可能になります。'
        }),
    )
    
    def event_date_display(self, obj):
        """開催日を表示（2日間対応）"""
        if obj.event_end_date:
            return format_html(
                '{} ～ {}',
                obj.event_date.strftime('%m/%d'),
                obj.event_end_date.strftime('%m/%d')
            )
        return obj.event_date.strftime('%Y/%m/%d')
    event_date_display.short_description = '開催日'
    event_date_display.admin_order_field = 'event_date'
    
    def entry_period_display(self, obj):
        """エントリー期間を表示"""
        now = timezone.now()
        start = obj.entry_start_at.strftime('%m/%d %H:%M')
        end = obj.entry_end_at.strftime('%m/%d %H:%M')
        
        if now < obj.entry_start_at:
            color = '#6c757d'
            status = '開始前'
        elif now > obj.entry_end_at:
            color = '#dc3545'
            status = '終了'
        else:
            color = '#28a745'
            status = '期間中'
        
        return format_html(
            '<span style="color: {};">{} ～ {}<br><small>({})</small></span>',
            color, start, end, status
        )
    entry_period_display.short_description = 'エントリー期間'
    
    def entry_count(self, obj):
        """エントリー数を表示"""
        from entries.models import Entry
        count = Entry.objects.filter(race__competition=obj).exclude(status='cancelled').count()
        confirmed = Entry.objects.filter(race__competition=obj, status='confirmed').count()
        
        if count > 0:
            return format_html(
                '<a href="/admin/entries/entry/?race__competition__id__exact={}">'
                '<strong>{}</strong> 件<br><small>(確定: {})</small></a>',
                obj.id, count, confirmed
            )
        return '0 件'
    entry_count.short_description = 'エントリー数'
    
    def is_published_badge(self, obj):
        """公開状態バッジ"""
        if obj.is_published:
            return format_html('<span style="color: #28a745; font-weight: bold;">✓ 公開中</span>')
        return format_html('<span style="color: #6c757d;">非公開</span>')
    is_published_badge.short_description = '公開'
    is_published_badge.admin_order_field = 'is_published'
    
    def is_entry_open_badge(self, obj):
        """エントリー受付状態バッジ"""
        if obj.is_entry_open:
            return format_html('<span style="color: #007bff; font-weight: bold;">受付中</span>')
        return format_html('<span style="color: #dc3545;">停止</span>')
    is_entry_open_badge.short_description = 'エントリー'
    is_entry_open_badge.admin_order_field = 'is_entry_open'


# =============================================================================
# 種目管理
# =============================================================================

@admin.register(Race)
class RaceAdmin(admin.ModelAdmin):
    """種目管理画面（大幅強化版）"""
    list_display = (
        'name', 'competition_link', 'distance_display', 'gender_badge',
        'entry_count', 'heat_count', 'heat_capacity', 'ncg_badge', 'standard_time_display', 'is_active_badge'
    )
    list_filter = ('competition', 'gender', 'distance', 'is_ncg', 'is_active')
    search_fields = ('name', 'competition__name')
    ordering = ('competition', 'display_order')
    list_per_page = 30
    actions = [export_races_csv, generate_heats_for_races]
    
    fieldsets = (
        ('基本情報', {
            'fields': ('competition', 'name', 'distance', 'gender', 'display_order'),
            'description': '種目の基本情報を入力してください。表示順は小さい数字ほど上に表示されます。'
        }),
        ('組編成設定', {
            'fields': ('heat_capacity', 'max_entries'),
            'description': '1組あたりの定員、エントリー上限を設定します'
        }),
        ('NCG設定', {
            'fields': ('is_ncg', 'ncg_capacity', 'standard_time', 'fallback_race', 'scheduled_start_time'),
            'description': 'NCG（NITTAI CHALLENGE GAMES）種目の設定。NCG定員を超えた選手は一般種目にスライドします。'
        }),
        ('ステータス', {
            'fields': ('is_active',),
            'description': '無効にすると、この種目は表示されなくなります'
        }),
    )
    
    def competition_link(self, obj):
        """大会名をリンクで表示"""
        return format_html(
            '<a href="/admin/competitions/competition/{}/change/">{}</a>',
            obj.competition.id, obj.competition.name[:15]
        )
    competition_link.short_description = '大会'
    competition_link.admin_order_field = 'competition__name'
    
    def distance_display(self, obj):
        """距離を表示"""
        return obj.get_distance_display()
    distance_display.short_description = '距離'
    distance_display.admin_order_field = 'distance'
    
    def gender_badge(self, obj):
        """性別バッジ"""
        if obj.gender == 'M':
            return format_html('<span style="color: #007bff;">♂ 男子</span>')
        elif obj.gender == 'F':
            return format_html('<span style="color: #e83e8c;">♀ 女子</span>')
        return format_html('<span style="color: #6c757d;">混合</span>')
    gender_badge.short_description = '性別'
    gender_badge.admin_order_field = 'gender'
    
    def entry_count(self, obj):
        """エントリー数を表示"""
        count = obj.entries.exclude(status='cancelled').count()
        if count > 0:
            return format_html(
                '<a href="/admin/entries/entry/?race__id__exact={}">{} 名</a>',
                obj.id, count
            )
        return '0 名'
    entry_count.short_description = 'エントリー'
    
    def heat_count(self, obj):
        """組数を表示"""
        count = obj.heats.count()
        if count > 0:
            return format_html(
                '<a href="/admin/heats/heat/?race__id__exact={}">{} 組</a>',
                obj.id, count
            )
        return format_html('<span style="color: #6c757d;">未編成</span>')
    heat_count.short_description = '組数'
    
    def ncg_badge(self, obj):
        """NCGバッジ"""
        if obj.is_ncg:
            return format_html('<span style="color: #ffc107; font-weight: bold;">NCG</span>')
        return '-'
    ncg_badge.short_description = 'NCG'
    ncg_badge.admin_order_field = 'is_ncg'
    
    def standard_time_display(self, obj):
        """標準記録を分:秒形式で表示"""
        if obj.standard_time:
            total_seconds = float(obj.standard_time)
            minutes = int(total_seconds // 60)
            seconds = total_seconds % 60
            return f"{minutes}:{seconds:05.2f}"
        return "-"
    standard_time_display.short_description = '標準記録'
    
    def is_active_badge(self, obj):
        """有効/無効バッジ"""
        if obj.is_active:
            return format_html('<span style="color: #28a745;">✓</span>')
        return format_html('<span style="color: #dc3545;">✗</span>')
    is_active_badge.short_description = '有効'
    is_active_badge.admin_order_field = 'is_active'
    
    def get_queryset(self, request):
        """クエリ最適化"""
        return super().get_queryset(request).select_related('competition', 'fallback_race')
