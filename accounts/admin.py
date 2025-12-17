"""
ユーザー・団体・選手管理画面
初心者でも使いやすい管理画面を提供
"""
import csv

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.http import HttpResponse
from django.utils.html import format_html

from .models import Athlete, Organization, User

# =============================================================================
# 管理アクション
# =============================================================================

@admin.action(description="選択した選手をCSVでエクスポート")
def export_athletes_csv(modeladmin, request, queryset):
    """選手をCSVでエクスポート"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="athletes.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        '氏名', 'フリガナ', '英語名', '性別', '生年月日', 
        '学年', '国籍', '登録陸協', 'JAAF ID', '所属団体', '有効'
    ])
    
    for athlete in queryset.select_related('organization'):
        writer.writerow([
            athlete.full_name,
            athlete.full_name_kana,
            athlete.full_name_en,
            athlete.get_gender_display(),
            athlete.birth_date,
            athlete.get_grade_display() if athlete.grade else '',
            athlete.get_nationality_display() if athlete.nationality else 'JPN',
            athlete.get_registered_pref_display() if athlete.registered_pref else '',
            athlete.jaaf_id or '',
            athlete.organization.name if athlete.organization else '',
            '有効' if athlete.is_active else '無効',
        ])
    
    return response


@admin.action(description="選択した選手を有効化")
def activate_athletes(modeladmin, request, queryset):
    """選手を一括有効化"""
    count = queryset.update(is_active=True)
    messages.success(request, f'{count}名の選手を有効化しました。')


@admin.action(description="選択した選手を無効化")
def deactivate_athletes(modeladmin, request, queryset):
    """選手を一括無効化"""
    count = queryset.update(is_active=False)
    messages.success(request, f'{count}名の選手を無効化しました。')


@admin.action(description="選択した団体をCSVでエクスポート")
def export_organizations_csv(modeladmin, request, queryset):
    """団体をCSVでエクスポート"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="organizations.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        '団体名', 'フリガナ', '略称', '代表者名', 'メール', '電話番号', '有効'
    ])
    
    for org in queryset:
        writer.writerow([
            org.name,
            org.name_kana,
            org.short_name,
            org.representative_name,
            org.representative_email,
            org.representative_phone,
            '有効' if org.is_active else '無効',
        ])
    
    return response


# =============================================================================
# ユーザー管理
# =============================================================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """ユーザー管理画面"""
    list_display = (
        'email', 'full_name', 'organization_link', 
        'is_admin_badge', 'is_active_badge', 'last_login'
    )
    list_filter = ('is_admin', 'is_active', 'is_individual', 'organization')
    search_fields = ('email', 'full_name', 'full_name_kana', 'organization__name')
    ordering = ('-date_joined',)
    list_per_page = 30
    
    fieldsets = (
        (None, {
            'fields': ('email', 'password'),
            'description': 'ログインに使用するメールアドレスとパスワード'
        }),
        ('個人情報', {
            'fields': ('full_name', 'full_name_kana', 'phone'),
            'description': '担当者の連絡先情報'
        }),
        ('所属情報', {
            'fields': ('organization', 'is_individual', 'organization_type', 'affiliation_name'),
            'description': '団体ユーザーか個人参加かを選択'
        }),
        ('団体担当者情報（任意）', {
            'fields': ('coach_name', 'contact_person', 'postal_code', 'address'),
            'classes': ('collapse',),
            'description': '団体の監督・連絡責任者情報'
        }),
        ('権限設定', {
            'fields': ('is_admin', 'is_active', 'is_staff', 'is_superuser'),
            'description': '管理者権限を付与するとすべての機能にアクセスできます'
        }),
        ('日時情報', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',),
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'full_name_kana', 'phone', 'password1', 'password2'),
            'description': '新しいユーザーを作成します'
        }),
    )
    
    readonly_fields = ('last_login', 'date_joined')
    
    def organization_link(self, obj):
        """団体名をリンクで表示"""
        if obj.organization:
            return format_html(
                '<a href="/admin/accounts/organization/{}/change/">{}</a>',
                obj.organization.id, obj.organization.name
            )
        return '個人' if obj.is_individual else '-'
    organization_link.short_description = '所属団体'
    organization_link.admin_order_field = 'organization__name'
    
    def is_admin_badge(self, obj):
        """管理者バッジ"""
        if obj.is_superuser:
            return format_html('<span style="color: #dc3545; font-weight: bold;">スーパー管理者</span>')
        if obj.is_admin:
            return format_html('<span style="color: #007bff; font-weight: bold;">管理者</span>')
        return format_html('<span style="color: #6c757d;">一般</span>')
    is_admin_badge.short_description = '権限'
    is_admin_badge.admin_order_field = 'is_admin'
    
    def is_active_badge(self, obj):
        """有効/無効バッジ"""
        if obj.is_active:
            return format_html('<span style="color: #28a745;">✓ 有効</span>')
        return format_html('<span style="color: #dc3545;">✗ 無効</span>')
    is_active_badge.short_description = '状態'
    is_active_badge.admin_order_field = 'is_active'


# =============================================================================
# 団体管理
# =============================================================================

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """団体管理画面"""
    list_display = (
        'name', 'short_name', 'athlete_count', 
        'representative_name', 'representative_email', 'is_active_badge'
    )
    list_filter = ('is_active',)
    search_fields = ('name', 'name_kana', 'short_name', 'representative_name')
    ordering = ('name_kana',)
    list_per_page = 30
    actions = [export_organizations_csv]
    
    fieldsets = (
        ('団体基本情報', {
            'fields': ('name', 'name_kana', 'short_name'),
            'description': '団体の正式名称とフリガナを入力してください'
        }),
        ('代表者情報', {
            'fields': ('representative_name', 'representative_email', 'representative_phone'),
            'description': '大会からの連絡を受ける代表者の情報'
        }),
        ('住所情報（任意）', {
            'fields': ('postal_code', 'address'),
            'classes': ('collapse',),
        }),
        ('陸連登録情報（任意）', {
            'fields': ('jaaf_code',),
            'classes': ('collapse',),
        }),
        ('ステータス', {
            'fields': ('is_active',),
        }),
    )
    
    def athlete_count(self, obj):
        """所属選手数"""
        count = obj.athletes.filter(is_active=True).count()
        if count > 0:
            return format_html(
                '<a href="/admin/accounts/athlete/?organization__id__exact={}">{} 名</a>',
                obj.id, count
            )
        return '0 名'
    athlete_count.short_description = '選手数'
    
    def is_active_badge(self, obj):
        """有効/無効バッジ"""
        if obj.is_active:
            return format_html('<span style="color: #28a745;">✓ 有効</span>')
        return format_html('<span style="color: #dc3545;">✗ 無効</span>')
    is_active_badge.short_description = '状態'
    is_active_badge.admin_order_field = 'is_active'


# =============================================================================
# 選手管理
# =============================================================================

@admin.register(Athlete)
class AthleteAdmin(admin.ModelAdmin):
    """選手管理画面（大幅強化版）"""
    list_display = (
        'full_name', 'full_name_kana', 'organization_link', 'gender_badge',
        'birth_date', 'grade_display', 'registered_pref', 'jaaf_id', 'is_active_badge'
    )
    list_filter = (
        'is_active', 'gender', 'organization', 
        'grade', 'nationality', 'registered_pref'
    )
    search_fields = (
        'last_name', 'first_name', 'last_name_kana', 'first_name_kana',
        'last_name_en', 'first_name_en', 'jaaf_id', 'organization__name'
    )
    ordering = ('organization__name_kana', 'last_name_kana', 'first_name_kana')
    list_per_page = 50
    actions = [export_athletes_csv, activate_athletes, deactivate_athletes]
    
    fieldsets = (
        ('氏名（漢字）', {
            'fields': (('last_name', 'first_name'),),
            'description': '選手の氏名を漢字で入力してください'
        }),
        ('氏名（カナ）', {
            'fields': (('last_name_kana', 'first_name_kana'),),
            'description': '全角カタカナで入力してください（例：ヤマダ タロウ）'
        }),
        ('氏名（ローマ字）', {
            'fields': (('last_name_en', 'first_name_en'),),
            'description': '姓は大文字（例: YAMADA）、名は先頭のみ大文字（例: Taro）で入力'
        }),
        ('基本情報', {
            'fields': ('gender', 'birth_date', 'grade', 'nationality'),
            'description': '性別と生年月日は必須です'
        }),
        ('陸連登録情報（必須）', {
            'fields': ('registered_pref', 'jaaf_id'),
            'description': '⚠️ 登録陸協・JAAF IDの記載がないと公認申請ができません。必ず記入してください。'
        }),
        ('所属', {
            'fields': ('organization', 'user'),
            'description': '所属団体を選択してください'
        }),
        ('ステータス', {
            'fields': ('is_active',),
            'description': '無効にすると、この選手はエントリーできなくなります'
        }),
    )
    
    def organization_link(self, obj):
        """団体名をリンクで表示"""
        if obj.organization:
            return format_html(
                '<a href="/admin/accounts/organization/{}/change/">{}</a>',
                obj.organization.id, 
                obj.organization.short_name or obj.organization.name[:10]
            )
        return '-'
    organization_link.short_description = '団体'
    organization_link.admin_order_field = 'organization__name_kana'
    
    def gender_badge(self, obj):
        """性別バッジ"""
        if obj.gender == 'M':
            return format_html('<span style="color: #007bff;">♂ 男</span>')
        elif obj.gender == 'F':
            return format_html('<span style="color: #e83e8c;">♀ 女</span>')
        return '-'
    gender_badge.short_description = '性別'
    gender_badge.admin_order_field = 'gender'
    
    def grade_display(self, obj):
        """学年表示"""
        if obj.grade:
            return obj.get_grade_display()
        return '-'
    grade_display.short_description = '学年'
    grade_display.admin_order_field = 'grade'
    
    def is_active_badge(self, obj):
        """有効/無効バッジ"""
        if obj.is_active:
            return format_html('<span style="color: #28a745;">✓</span>')
        return format_html('<span style="color: #dc3545;">✗</span>')
    is_active_badge.short_description = '有効'
    is_active_badge.admin_order_field = 'is_active'
    
    def get_queryset(self, request):
        """クエリ最適化"""
        return super().get_queryset(request).select_related('organization', 'user')
