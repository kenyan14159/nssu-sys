"""
決済・入金管理モデル
"""
import os
import uuid

from auditlog.registry import auditlog
from django.db import models, transaction
from django.utils import timezone

from accounts.models import Organization, User
from competitions.models import Competition
from entries.models import EntryGroup


def payment_image_path(instance, filename):
    """振込明細画像の保存パス生成"""
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('payments', str(instance.entry_group.competition.id), new_filename)


class Payment(models.Model):
    """
    決済モデル
    振込画像パス、承認ステータスフラグ
    """
    STATUS_CHOICES = [
        ('pending', '確認待ち'),
        ('approved', '承認済み'),
        ('rejected', '却下'),
    ]
    
    # エントリーグループ紐付け
    entry_group = models.OneToOneField(
        EntryGroup,
        on_delete=models.CASCADE,
        related_name='payment',
        verbose_name='エントリーグループ'
    )
    
    # 振込明細画像
    receipt_image = models.ImageField(
        '振込明細画像',
        upload_to=payment_image_path,
        help_text='振込完了後、振込明細書またはネットバンキングのスクリーンショットをアップロードしてください'
    )
    
    # 入金情報
    payment_date = models.DateField('振込日', null=True, blank=True)
    payment_amount = models.PositiveIntegerField('振込金額', null=True, blank=True)
    payer_name = models.CharField('振込名義', max_length=100, blank=True)
    
    # 承認状態
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # 承認情報
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_payments',
        verbose_name='確認者'
    )
    reviewed_at = models.DateTimeField('確認日時', null=True, blank=True)
    review_note = models.TextField('確認メモ', blank=True)
    
    # メタ情報
    uploaded_at = models.DateTimeField('アップロード日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = '入金情報'
        verbose_name_plural = '入金情報'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.entry_group} - {self.get_status_display()}"
    
    def approve(self, reviewer, send_email=True):
        """入金を承認"""
        self.status = 'approved'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save()
        
        # エントリーグループのステータスも更新
        self.entry_group.confirm_all()
        
        # メール通知
        if send_email:
            from payments.notifications import send_payment_approved_email
            send_payment_approved_email(self)
    
    def reject(self, reviewer, note='', send_email=True):
        """入金を却下"""
        self.status = 'rejected'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_note = note
        self.save()
        
        # エントリーグループのステータスも更新
        self.entry_group.status = 'pending'
        self.entry_group.save()
        
        # メール通知
        if send_email:
            from payments.notifications import send_payment_rejected_email
            send_payment_rejected_email(self, note)
    
    @transaction.atomic
    def force_approve(self, reviewer, note='当日現場確認'):
        """
        強制承認（トラブルデスク用）
        振込明細画像なしでも承認可能
        """
        self.status = 'approved'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_note = f'[強制承認] {note}'
        self.save()
        
        # エントリーグループのステータスも更新
        self.entry_group.confirm_all()


class BankAccount(models.Model):
    """
    振込先口座情報
    """
    bank_name = models.CharField('銀行名', max_length=100)
    branch_name = models.CharField('支店名', max_length=100)
    account_type = models.CharField(
        '口座種別',
        max_length=10,
        choices=[('ordinary', '普通'), ('current', '当座')],
        default='ordinary'
    )
    account_number = models.CharField('口座番号', max_length=20)
    account_holder = models.CharField('口座名義', max_length=100)
    
    is_active = models.BooleanField('有効', default=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    
    class Meta:
        verbose_name = '振込先口座'
        verbose_name_plural = '振込先口座'
    
    def __str__(self):
        return f"{self.bank_name} {self.branch_name} {self.account_number}"


class ParkingRequest(models.Model):
    """
    車両・駐車場申請モデル
    ユーザーが希望台数を申請し、管理者がCSVで駐車場を割り当てる
    """
    VEHICLE_STATUS_CHOICES = [
        ('requested', '申請中'),
        ('assigned', '割当済'),
        ('rejected', '却下'),
    ]
    
    # 団体・大会紐付け
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='parking_requests',
        verbose_name='団体'
    )
    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name='parking_requests',
        verbose_name='大会'
    )
    
    # ユーザーが入力する希望
    requested_large_bus = models.PositiveIntegerField(
        '大型バス希望数',
        default=0,
        help_text='大型バス（45人以上乗り）の希望台数'
    )
    requested_medium_bus = models.PositiveIntegerField(
        '中型バス希望数',
        default=0,
        help_text='マイクロバス・中型バスの希望台数'
    )
    requested_car = models.PositiveIntegerField(
        '乗用車希望数',
        default=0,
        help_text='普通乗用車の希望台数'
    )
    request_note = models.TextField(
        '備考・連絡事項',
        blank=True,
        help_text='駐車に関する要望があれば記入してください'
    )
    
    # 管理者がCSVで流し込む確定データ
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=VEHICLE_STATUS_CHOICES,
        default='requested'
    )
    assigned_parking_lot = models.CharField(
        '割当駐車場',
        max_length=100,
        blank=True,
        help_text='例: A駐車場、第2グラウンド横'
    )
    assigned_large_bus = models.PositiveIntegerField(
        '大型バス割当数',
        default=0
    )
    assigned_medium_bus = models.PositiveIntegerField(
        '中型バス割当数',
        default=0
    )
    assigned_car = models.PositiveIntegerField(
        '乗用車割当数',
        default=0
    )
    entry_time = models.TimeField(
        '入庫時間',
        null=True,
        blank=True,
        help_text='許可される入庫開始時間'
    )
    exit_time = models.TimeField(
        '出庫時間',
        null=True,
        blank=True,
        help_text='出庫期限時間'
    )
    assignment_note = models.TextField(
        '管理者メモ',
        blank=True,
        help_text='割当に関する注意事項など'
    )
    
    # 申込者
    requested_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='parking_requests',
        verbose_name='申込者'
    )
    
    # メタ情報
    created_at = models.DateTimeField('申請日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = '駐車場申請'
        verbose_name_plural = '駐車場申請'
        unique_together = ['organization', 'competition']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.organization.name} - {self.competition.name}"
    
    @property
    def total_requested(self):
        """希望台数の合計"""
        return self.requested_large_bus + self.requested_medium_bus + self.requested_car
    
    @property
    def total_assigned(self):
        """割当台数の合計"""
        return self.assigned_large_bus + self.assigned_medium_bus + self.assigned_car
    
    @property
    def is_assigned(self):
        """割当済みかどうか"""
        return self.status == 'assigned' and self.assigned_parking_lot
    
    def get_permit_info(self):
        """駐車許可証用の情報を取得"""
        return {
            'organization_name': self.organization.name,
            'competition_name': self.competition.name,
            'event_date': self.competition.event_date,
            'parking_lot': self.assigned_parking_lot,
            'entry_time': self.entry_time,
            'exit_time': self.exit_time,
            'large_bus': self.assigned_large_bus,
            'medium_bus': self.assigned_medium_bus,
            'car': self.assigned_car,
        }


# django-auditlog登録
auditlog.register(Payment)
auditlog.register(ParkingRequest)
