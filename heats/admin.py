"""
番組編成管理画面
初心者でも使いやすい管理画面を提供
"""
import csv
from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html

from .models import Heat, HeatAssignment


# =============================================================================
# 管理アクション
# =============================================================================

@admin.action(description="選択した組を確定")
def finalize_heats(modeladmin, request, queryset):
    """組を一括確定"""
    count = queryset.update(is_finalized=True)
    messages.success(request, f'{count}件の組を確定しました。')


@admin.action(description="選択した組の確定を解除")
def unfinalize_heats(modeladmin, request, queryset):
    """組の確定を解除"""
    count = queryset.update(is_finalized=False)
    messages.success(request, f'{count}件の組の確定を解除しました。')


@admin.action(description="選択した選手を点呼済みに変更")
def check_in_assignments(modeladmin, request, queryset):
    """選手を一括点呼済み"""
    now = timezone.now()
    count = queryset.filter(checked_in=False).update(checked_in=True, checked_in_at=now)
    messages.success(request, f'{count}名を点呼済みにしました。')


@admin.action(description="選択した選手を欠場（DNS）に変更")
def mark_dns(modeladmin, request, queryset):
    """選手を一括DNS"""
    count = queryset.update(status='dns')
    messages.warning(request, f'{count}名を欠場（DNS）にしました。')


@admin.action(description="選択した組をCSVでエクスポート（スタートリスト）")
def export_heat_csv(modeladmin, request, queryset):
    """組をCSVでエクスポート"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="heats.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        '種目名', '組番号', '腰番号', 'ゼッケン', '選手名', 'フリガナ',
        '団体名', '申告タイム', 'ステータス', '点呼'
    ])
    
    for heat in queryset.prefetch_related('assignments__entry__athlete', 'assignments__entry__athlete__organization'):
        for assignment in heat.assignments.all().order_by('bib_number'):
            athlete = assignment.entry.athlete
            writer.writerow([
                heat.race.name,
                heat.heat_number,
                assignment.bib_number,
                assignment.race_bib_number or '',
                athlete.full_name,
                athlete.full_name_kana,
                athlete.organization.name if athlete.organization else '',
                assignment.entry.declared_time_display,
                assignment.get_status_display(),
                '済' if assignment.checked_in else '未',
            ])
    
    return response


# =============================================================================
# 組編成インライン
# =============================================================================

class HeatAssignmentInline(admin.TabularInline):
    """組編成インライン編集"""
    model = HeatAssignment
    extra = 0
    raw_id_fields = ('entry',)
    readonly_fields = ('athlete_name', 'organization_name', 'declared_time', 'checked_in', 'checked_in_at')
    fields = ('bib_number', 'race_bib_number', 'athlete_name', 'organization_name', 'declared_time', 'status', 'checked_in', 'checked_in_at')
    ordering = ('bib_number',)
    
    def athlete_name(self, obj):
        """選手名を表示"""
        return obj.entry.athlete.full_name
    athlete_name.short_description = '選手'
    
    def organization_name(self, obj):
        """団体名を表示"""
        if obj.entry.athlete.organization:
            return obj.entry.athlete.organization.short_name or obj.entry.athlete.organization.name[:8]
        return '-'
    organization_name.short_description = '団体'
    
    def declared_time(self, obj):
        """申告タイムを表示"""
        return obj.entry.declared_time_display
    declared_time.short_description = '申告タイム'


# =============================================================================
# 組管理
# =============================================================================

@admin.register(Heat)
class HeatAdmin(admin.ModelAdmin):
    """組管理画面（大幅強化版）"""
    list_display = (
        'race_link', 'heat_number', 'entry_count_display',
        'scheduled_start_time', 'check_in_status', 'is_finalized_badge'
    )
    list_filter = ('race__competition', 'race', 'is_finalized')
    search_fields = ('race__name', 'race__competition__name')
    inlines = [HeatAssignmentInline]
    ordering = ('race__competition', 'race__display_order', 'heat_number')
    list_per_page = 30
    actions = [finalize_heats, unfinalize_heats, export_heat_csv]
    
    fieldsets = (
        ('組情報', {
            'fields': ('race', 'heat_number', 'scheduled_start_time'),
            'description': '種目と組番号を設定してください'
        }),
        ('ステータス', {
            'fields': ('is_finalized',),
            'description': '確定すると変更できなくなります'
        }),
    )
    
    def race_link(self, obj):
        """種目名をリンクで表示"""
        return format_html(
            '<a href="/admin/competitions/race/{}/change/">{}</a>',
            obj.race.id, obj.race.name
        )
    race_link.short_description = '種目'
    race_link.admin_order_field = 'race__name'
    
    def entry_count_display(self, obj):
        """エントリー数を表示"""
        count = obj.assignments.count()
        if count > 0:
            return format_html('<strong>{}</strong> 名', count)
        return '0 名'
    entry_count_display.short_description = '人数'
    
    def check_in_status(self, obj):
        """点呼状況を表示"""
        total = obj.assignments.count()
        if total == 0:
            return '-'
        checked = obj.assignments.filter(checked_in=True).count()
        dns = obj.assignments.filter(status='dns').count()
        
        if checked == total:
            return format_html('<span style="color: #28a745;">✓ 全員点呼済</span>')
        elif checked > 0:
            return format_html(
                '<span style="color: #ffc107;">{}/{} (DNS: {})</span>',
                checked, total, dns
            )
        return format_html('<span style="color: #6c757d;">0/{}</span>', total)
    check_in_status.short_description = '点呼'
    
    def is_finalized_badge(self, obj):
        """確定バッジ"""
        if obj.is_finalized:
            return format_html('<span style="color: #28a745; font-weight: bold;">✓ 確定</span>')
        return format_html('<span style="color: #6c757d;">未確定</span>')
    is_finalized_badge.short_description = '状態'
    is_finalized_badge.admin_order_field = 'is_finalized'
    
    def get_queryset(self, request):
        """クエリ最適化"""
        return super().get_queryset(request).select_related(
            'race', 'race__competition'
        ).prefetch_related('assignments')


# =============================================================================
# 組編成詳細管理
# =============================================================================

@admin.register(HeatAssignment)
class HeatAssignmentAdmin(admin.ModelAdmin):
    """組編成詳細管理画面（大幅強化版）"""
    list_display = (
        'heat_display', 'bib_number', 'race_bib_number',
        'athlete_link', 'organization_name', 'declared_time_display',
        'status_badge', 'check_in_badge'
    )
    list_filter = ('heat__race__competition', 'heat__race', 'status', 'checked_in')
    search_fields = (
        'entry__athlete__last_name', 'entry__athlete__first_name',
        'entry__athlete__last_name_kana', 'entry__athlete__first_name_kana',
        'entry__athlete__organization__name'
    )
    raw_id_fields = ('heat', 'entry')
    readonly_fields = ('checked_in_at',)
    ordering = ('heat__race', 'heat__heat_number', 'bib_number')
    list_per_page = 50
    actions = [check_in_assignments, mark_dns]
    
    fieldsets = (
        ('割り当て情報', {
            'fields': ('heat', 'entry', 'bib_number', 'race_bib_number'),
            'description': '組と選手を紐付けて、腰番号を設定します'
        }),
        ('ステータス', {
            'fields': ('status',),
            'description': '出走予定、欠場、途中棄権、失格を設定'
        }),
        ('点呼情報', {
            'fields': ('checked_in', 'checked_in_at'),
            'description': '当日の点呼状況'
        }),
    )
    
    def heat_display(self, obj):
        """組情報を表示"""
        return format_html(
            '<a href="/admin/heats/heat/{}/change/">{} {}組</a>',
            obj.heat.id, obj.heat.race.name[:8], obj.heat.heat_number
        )
    heat_display.short_description = '組'
    heat_display.admin_order_field = 'heat__heat_number'
    
    def athlete_link(self, obj):
        """選手名をリンクで表示"""
        return format_html(
            '<a href="/admin/accounts/athlete/{}/change/">{}</a>',
            obj.entry.athlete.id, obj.entry.athlete.full_name
        )
    athlete_link.short_description = '選手'
    athlete_link.admin_order_field = 'entry__athlete__last_name_kana'
    
    def organization_name(self, obj):
        """団体名を表示"""
        if obj.entry.athlete.organization:
            return obj.entry.athlete.organization.short_name or obj.entry.athlete.organization.name[:8]
        return '-'
    organization_name.short_description = '団体'
    
    def declared_time_display(self, obj):
        """申告タイムを表示"""
        return obj.entry.declared_time_display
    declared_time_display.short_description = '申告タイム'
    
    def status_badge(self, obj):
        """ステータスバッジ"""
        colors = {
            'assigned': '#28a745',
            'dns': '#dc3545',
            'dnf': '#ffc107',
            'dq': '#6c757d',
        }
        icons = {
            'assigned': '✓',
            'dns': '🚫',
            'dnf': '⚠',
            'dq': '✗',
        }
        color = colors.get(obj.status, '#6c757d')
        icon = icons.get(obj.status, '')
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    status_badge.short_description = 'ステータス'
    status_badge.admin_order_field = 'status'
    
    def check_in_badge(self, obj):
        """点呼バッジ"""
        if obj.checked_in:
            time_str = obj.checked_in_at.strftime('%H:%M') if obj.checked_in_at else ''
            return format_html(
                '<span style="color: #28a745;">✓ {}</span>',
                time_str
            )
        return format_html('<span style="color: #dc3545;">未点呼</span>')
    check_in_badge.short_description = '点呼'
    check_in_badge.admin_order_field = 'checked_in'
    
    def get_queryset(self, request):
        """クエリ最適化"""
        return super().get_queryset(request).select_related(
            'heat', 'heat__race', 'heat__race__competition',
            'entry', 'entry__athlete', 'entry__athlete__organization'
        )
