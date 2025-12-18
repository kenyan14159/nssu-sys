"""
決済・入金管理画面
初心者でも使いやすい管理画面を提供
振込明細画像のサムネイル表示、ワンクリック承認機能付き
"""
import csv

from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html

from .models import BankAccount, ParkingRequest, Payment

# =============================================================================
# 入金フォーム (振込金額のステップ値設定)
# =============================================================================

class PaymentAdminForm(forms.ModelForm):
    """入金管理フォーム - 振込金額のステップ値を2000円に設定"""
    
    class Meta:
        model = Payment
        fields = [
            'entry_group', 'receipt_image', 'payment_date', 'payment_amount',
            'payer_name', 'status', 'review_note', 'reviewed_by', 'reviewed_at'
        ]
        widgets = {
            'payment_amount': forms.NumberInput(attrs={'step': '2000', 'min': '0'}),
        }


# =============================================================================
# 管理アクション
# =============================================================================

@admin.action(description="選択した入金を承認（エントリー確定）")
def approve_payments(modeladmin, request, queryset):
    """入金を一括承認"""
    count = 0
    for payment in queryset.filter(status='pending'):
        payment.approve(request.user, send_email=True)
        count += 1
    messages.success(request, f'{count}件の入金を承認し、エントリーを確定しました。')


@admin.action(description="選択した入金を却下")
def reject_payments(modeladmin, request, queryset):
    """入金を一括却下"""
    count = 0
    for payment in queryset.filter(status='pending'):
        payment.reject(request.user, note='管理画面から一括却下', send_email=True)
        count += 1
    messages.warning(request, f'{count}件の入金を却下しました。')


@admin.action(description="選択した入金情報をCSVでエクスポート")
def export_payments_csv(modeladmin, request, queryset):
    """入金情報をCSVでエクスポート"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="payments.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        '団体名', '大会名', '振込金額', '振込名義', '振込日',
        'ステータス', '確認者', '確認日時', 'アップロード日時'
    ])
    
    for payment in queryset.select_related('entry_group', 'entry_group__organization', 'entry_group__competition', 'reviewed_by'):
        writer.writerow([
            payment.entry_group.organization.name if payment.entry_group.organization else '',
            payment.entry_group.competition.name,
            payment.payment_amount or '',
            payment.payer_name,
            payment.payment_date or '',
            payment.get_status_display(),
            payment.reviewed_by.full_name if payment.reviewed_by else '',
            payment.reviewed_at.strftime('%Y-%m-%d %H:%M') if payment.reviewed_at else '',
            payment.uploaded_at.strftime('%Y-%m-%d %H:%M'),
        ])
    
    return response


@admin.action(description="選択した駐車申請を割当済みに変更")
def assign_parking(modeladmin, request, queryset):
    """駐車申請を一括割当済み"""
    count = queryset.update(status='assigned')
    messages.success(request, f'{count}件の駐車申請を割当済みにしました。')


# =============================================================================
# 入金管理
# =============================================================================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """入金管理画面（大幅強化版）"""
    form = PaymentAdminForm
    
    list_display = (
        'organization_name', 'competition_name', 'receipt_thumbnail',
        'payment_amount_display', 'payer_name', 'status_badge',
        'action_buttons', 'uploaded_at'
    )
    list_filter = ('status', 'entry_group__competition')
    search_fields = ('payer_name', 'entry_group__organization__name')
    raw_id_fields = ('entry_group', 'reviewed_by')
    readonly_fields = ('uploaded_at', 'reviewed_at', 'receipt_preview')
    ordering = ('-uploaded_at',)
    list_per_page = 30
    actions = [approve_payments, reject_payments, export_payments_csv]
    
    fieldsets = (
        ('エントリーグループ情報', {
            'fields': ('entry_group',),
            'description': '対象のエントリーグループを選択してください'
        }),
        ('振込明細画像', {
            'fields': ('receipt_image', 'receipt_preview'),
            'description': '振込完了後にアップロードされた画像'
        }),
        ('入金情報', {
            'fields': ('payment_date', 'payment_amount', 'payer_name'),
            'description': '振込日、金額、振込名義を確認してください'
        }),
        ('確認ステータス', {
            'fields': ('status', 'review_note'),
            'description': '承認するとエントリーが確定します。却下する場合は理由を記入してください。'
        }),
        ('確認情報', {
            'fields': ('reviewed_by', 'reviewed_at', 'uploaded_at'),
            'classes': ('collapse',),
        }),
    )
    
    def organization_name(self, obj):
        """団体名を表示"""
        if obj.entry_group.organization:
            return format_html(
                '<a href="/admin/accounts/organization/{}/change/">{}</a>',
                obj.entry_group.organization.id,
                obj.entry_group.organization.short_name or obj.entry_group.organization.name[:10]
            )
        return '-'
    organization_name.short_description = '団体'
    organization_name.admin_order_field = 'entry_group__organization__name'
    
    def competition_name(self, obj):
        """大会名を表示"""
        return obj.entry_group.competition.name[:12]
    competition_name.short_description = '大会'
    
    def receipt_thumbnail(self, obj):
        """振込明細画像のサムネイル"""
        if obj.receipt_image:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width: 80px; max-height: 60px; border: 1px solid #ddd; border-radius: 4px;" />'
                '</a>',
                obj.receipt_image.url, obj.receipt_image.url
            )
        return format_html('<span style="color: #6c757d;">画像なし</span>')
    receipt_thumbnail.short_description = '明細画像'
    
    def receipt_preview(self, obj):
        """振込明細画像のプレビュー（詳細画面用）"""
        if obj.receipt_image:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width: 400px; max-height: 300px; border: 1px solid #ddd; border-radius: 8px;" />'
                '</a><br><small>クリックで拡大表示</small>',
                obj.receipt_image.url, obj.receipt_image.url
            )
        return format_html('<span style="color: #6c757d;">画像がアップロードされていません</span>')
    receipt_preview.short_description = '画像プレビュー'
    
    def payment_amount_display(self, obj):
        """振込金額を表示"""
        if obj.payment_amount:
            # format_htmlではカンマ区切りフォーマットが使えないため、事前にフォーマット
            formatted_amount = f'{obj.payment_amount:,}'
            return format_html(
                '<span style="font-weight: bold;">¥{}</span>',
                formatted_amount
            )
        return format_html('<span style="color: #6c757d;">未入力</span>')
    payment_amount_display.short_description = '金額'
    payment_amount_display.admin_order_field = 'payment_amount'
    
    def status_badge(self, obj):
        """ステータスバッジ"""
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545',
        }
        icons = {
            'pending': '⏳',
            'approved': '✓',
            'rejected': '✗',
        }
        color = colors.get(obj.status, '#6c757d')
        icon = icons.get(obj.status, '')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    status_badge.short_description = 'ステータス'
    status_badge.admin_order_field = 'status'
    
    def action_buttons(self, obj):
        """アクションボタン（一覧画面用）"""
        if obj.status == 'pending':
            return format_html(
                '<a href="/admin/payments/payment/{}/change/" '
                'class="button" style="background: #28a745; color: white; padding: 4px 8px; '
                'border-radius: 4px; text-decoration: none; margin-right: 4px;">確認</a>',
                obj.id
            )
        elif obj.status == 'approved':
            return format_html('<span style="color: #28a745;">✓ 承認済</span>')
        else:
            return format_html('<span style="color: #dc3545;">✗ 却下</span>')
    action_buttons.short_description = '操作'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'entry_group', 'entry_group__organization', 
            'entry_group__competition', 'reviewed_by'
        )
    
    def save_model(self, request, obj, form, change):
        """ステータス変更時にentry_groupのステータスも更新"""
        # 既存オブジェクトの場合、ステータスが変更されたかチェック
        if change and 'status' in form.changed_data:
            if obj.status == 'approved':
                # 承認時
                obj.reviewed_by = request.user
                obj.reviewed_at = timezone.now()
                # EntryGroupとエントリーも確定
                obj.entry_group.confirm_all()
                messages.success(request, '入金を承認し、エントリーを確定しました。')
            elif obj.status == 'rejected':
                # 却下時
                obj.reviewed_by = request.user
                obj.reviewed_at = timezone.now()
                obj.entry_group.status = 'pending'
                obj.entry_group.save()
                obj.entry_group.entries.update(status='pending')
                messages.warning(request, '入金を却下しました。エントリーは入金待ち状態に戻りました。')
        super().save_model(request, obj, form, change)


# =============================================================================
# 振込先口座管理
# =============================================================================

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    """振込先口座管理画面"""
    list_display = (
        'bank_name', 'branch_name', 'account_type_display', 
        'account_number', 'account_holder', 'is_active_badge'
    )
    list_filter = ('is_active', 'account_type')
    ordering = ('-is_active', 'bank_name')
    
    fieldsets = (
        ('口座情報', {
            'fields': ('bank_name', 'branch_name', 'account_type', 'account_number', 'account_holder'),
            'description': '参加者に案内する振込先口座情報を入力してください'
        }),
        ('ステータス', {
            'fields': ('is_active',),
            'description': '有効な口座のみが参加者に表示されます'
        }),
    )
    
    def account_type_display(self, obj):
        """口座種別を表示"""
        return obj.get_account_type_display()
    account_type_display.short_description = '種別'
    
    def is_active_badge(self, obj):
        """有効/無効バッジ"""
        if obj.is_active:
            return format_html('<span style="color: #28a745;">✓ 有効</span>')
        return format_html('<span style="color: #dc3545;">✗ 無効</span>')
    is_active_badge.short_description = '状態'


# =============================================================================
# 駐車場申請管理
# =============================================================================

@admin.register(ParkingRequest)
class ParkingRequestAdmin(admin.ModelAdmin):
    """駐車場申請管理画面（大幅強化版）"""
    list_display = (
        'organization_link', 'competition_name', 'status_badge', 
        'total_requested_display', 'total_assigned_display',
        'assigned_parking_lot', 'entry_exit_time'
    )
    list_filter = ('status', 'competition', 'assigned_parking_lot')
    search_fields = ('organization__name', 'organization__short_name')
    raw_id_fields = ('organization', 'competition', 'requested_by')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    list_per_page = 30
    actions = [assign_parking]
    
    fieldsets = (
        ('基本情報', {
            'fields': ('organization', 'competition', 'requested_by', 'status'),
            'description': '駐車申請の基本情報'
        }),
        ('希望台数（ユーザー入力）', {
            'fields': ('requested_large_bus', 'requested_medium_bus', 'requested_car', 'request_note'),
            'description': '申請者が入力した希望台数と備考'
        }),
        ('割当情報（管理者入力）', {
            'fields': (
                'assigned_parking_lot', 
                'assigned_large_bus', 'assigned_medium_bus', 'assigned_car',
                'entry_time', 'exit_time', 'assignment_note'
            ),
            'description': '割り当てる駐車場と台数、入退場時間を設定してください'
        }),
        ('メタ情報', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def organization_link(self, obj):
        """団体名をリンクで表示"""
        return format_html(
            '<a href="/admin/accounts/organization/{}/change/">{}</a>',
            obj.organization.id, 
            obj.organization.short_name or obj.organization.name[:10]
        )
    organization_link.short_description = '団体'
    organization_link.admin_order_field = 'organization__name'
    
    def competition_name(self, obj):
        """大会名を表示"""
        return obj.competition.name[:12]
    competition_name.short_description = '大会'
    
    def status_badge(self, obj):
        """ステータスバッジ"""
        colors = {
            'requested': '#ffc107',
            'assigned': '#28a745',
            'rejected': '#dc3545',
        }
        icons = {
            'requested': '⏳',
            'assigned': '✓',
            'rejected': '✗',
        }
        color = colors.get(obj.status, '#6c757d')
        icon = icons.get(obj.status, '')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    status_badge.short_description = 'ステータス'
    status_badge.admin_order_field = 'status'
    
    def total_requested_display(self, obj):
        """希望台数を表示"""
        return format_html(
            '🚌{} 🚐{} 🚗{}',
            obj.requested_large_bus, obj.requested_medium_bus, obj.requested_car
        )
    total_requested_display.short_description = '希望'
    
    def total_assigned_display(self, obj):
        """割当台数を表示"""
        if obj.status == 'assigned':
            return format_html(
                '<span style="color: #28a745;">🚌{} 🚐{} 🚗{}</span>',
                obj.assigned_large_bus, obj.assigned_medium_bus, obj.assigned_car
            )
        return format_html('<span style="color: #6c757d;">-</span>')
    total_assigned_display.short_description = '割当'
    
    def entry_exit_time(self, obj):
        """入退場時間を表示"""
        if obj.entry_time and obj.exit_time:
            return format_html(
                '{} ～ {}',
                obj.entry_time.strftime('%H:%M'),
                obj.exit_time.strftime('%H:%M')
            )
        return '-'
    entry_exit_time.short_description = '入退場'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organization', 'competition')
