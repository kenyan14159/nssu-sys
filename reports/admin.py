"""
帳票出力履歴管理画面
初心者でも使いやすい管理画面を提供
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import ReportLog


# =============================================================================
# 帳票出力履歴管理
# =============================================================================

@admin.register(ReportLog)
class ReportLogAdmin(admin.ModelAdmin):
    """帳票出力履歴管理画面（強化版）"""
    list_display = (
        'report_type_badge', 'competition_link', 'race_name',
        'generated_by_name', 'generated_at'
    )
    list_filter = ('report_type', 'competition')
    search_fields = ('competition__name', 'race__name', 'generated_by__full_name')
    raw_id_fields = ('competition', 'race', 'generated_by')
    readonly_fields = ('generated_at',)
    ordering = ('-generated_at',)
    list_per_page = 30
    
    fieldsets = (
        ('帳票情報', {
            'fields': ('report_type', 'competition', 'race'),
            'description': '出力された帳票の種類と対象大会・種目'
        }),
        ('出力者情報', {
            'fields': ('generated_by', 'generated_at'),
            'description': '誰がいつ出力したか'
        }),
    )
    
    def report_type_badge(self, obj):
        """レポートタイプをバッジで表示"""
        colors = {
            'start_list': '#007bff',
            'roll_call': '#28a745',
            'backup': '#6c757d',
            'result': '#17a2b8',
        }
        icons = {
            'start_list': '📋',
            'roll_call': '✅',
            'backup': '💾',
            'result': '🏆',
        }
        color = colors.get(obj.report_type, '#6c757d')
        icon = icons.get(obj.report_type, '📄')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{} {}</span>',
            color, icon, obj.get_report_type_display()
        )
    report_type_badge.short_description = '帳票種類'
    report_type_badge.admin_order_field = 'report_type'
    
    def competition_link(self, obj):
        """大会名をリンクで表示"""
        if obj.competition:
            return format_html(
                '<a href="/admin/competitions/competition/{}/change/">{}</a>',
                obj.competition.id, obj.competition.name[:15]
            )
        return '-'
    competition_link.short_description = '大会'
    competition_link.admin_order_field = 'competition__name'
    
    def race_name(self, obj):
        """種目名を表示"""
        if obj.race:
            return obj.race.name
        return '全種目'
    race_name.short_description = '種目'
    
    def generated_by_name(self, obj):
        """出力者名を表示"""
        if obj.generated_by:
            return obj.generated_by.full_name
        return '-'
    generated_by_name.short_description = '出力者'
    generated_by_name.admin_order_field = 'generated_by__full_name'
    
    def get_queryset(self, request):
        """クエリ最適化"""
        return super().get_queryset(request).select_related(
            'competition', 'race', 'generated_by'
        )
