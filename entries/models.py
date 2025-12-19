"""
エントリーモデル
"""
from auditlog.registry import auditlog
from django.core.exceptions import ValidationError
from django.db import models, transaction

from accounts.models import Athlete, Organization, User
from competitions.models import Competition, Race


class Entry(models.Model):
    """
    エントリー申込モデル
    選手IDと種目IDの紐付け、申告タイム
    """
    STATUS_CHOICES = [
        ('pending', '申込中（入金待ち）'),
        ('payment_uploaded', '入金確認待ち'),
        ('confirmed', '確定'),
        ('cancelled', 'キャンセル'),
        ('dns', '欠場（DNS）'),
    ]
    
    # 選手・種目紐付け
    athlete = models.ForeignKey(
        Athlete,
        on_delete=models.CASCADE,
        related_name='entries',
        verbose_name='選手',
        help_text='エントリーする選手を選択してください'
    )
    race = models.ForeignKey(
        Race,
        on_delete=models.CASCADE,
        related_name='entries',
        verbose_name='種目',
        help_text='出場する種目を選択してください'
    )
    
    # 申込者（団体代表者または個人）
    registered_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='registered_entries',
        verbose_name='申込者'
    )
    
    # 申告タイム（秒単位で保存、小数点以下2桁）
    declared_time = models.DecimalField(
        '申告タイム（秒）',
        max_digits=8,
        decimal_places=2,
        help_text='秒単位で入力（右の分秒表示を参考に）'
    )
    
    # ベストタイム（参考情報）
    personal_best = models.DecimalField(
        '自己ベスト（秒）',
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='秒単位で入力（任意）'
    )
    
    # 状態管理
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text='入金確認後に「確定」に変更してください'
    )
    
    # 備考
    note = models.TextField(
        '備考', blank=True,
        help_text='特記事項があれば入力（任意）'
    )
    
    # NCGスライドフラグ（NCGから一般種目に移動された選手）
    moved_from_ncg = models.BooleanField(
        'NCGから移動',
        default=False,
        help_text='NCG定員超過により一般種目に移動された場合True'
    )
    
    # 元のNCG種目（移動元の記録用）
    original_ncg_race = models.ForeignKey(
        Race,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moved_entries',
        verbose_name='元NCG種目'
    )
    
    # メタ情報
    created_at = models.DateTimeField('申込日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = 'エントリー'
        verbose_name_plural = 'エントリー'
        ordering = ['race', 'declared_time']
        unique_together = ['athlete', 'race']
    
    def __str__(self):
        return f"{self.athlete.full_name} - {self.race.name}"
    
    def clean(self):
        """バリデーション"""
        # raceとathleteが設定されているかチェック
        if not hasattr(self, 'race') or self.race is None:
            return
        if not hasattr(self, 'athlete') or self.athlete is None:
            return
            
        # 性別チェック
        if self.race.gender != 'X' and self.athlete.gender != self.race.gender:
            raise ValidationError('選手の性別と種目の性別区分が一致しません')
        
        # 定員チェック
        if self.race.is_full and self.status == 'pending':
            raise ValidationError('この種目は定員に達しています')
        
        # 参加標準記録チェック
        if self.race.standard_time and self.declared_time:
            if self.declared_time > self.race.standard_time:
                from nitsys.constants import format_time
                standard_formatted = format_time(float(self.race.standard_time))
                declared_formatted = format_time(float(self.declared_time))
                raise ValidationError(
                    f'申告タイム({declared_formatted})が参加標準記録({standard_formatted})を超えています。'
                    f'この種目にエントリーするには{standard_formatted}以内の記録が必要です。'
                )
    
    @property
    def declared_time_display(self):
        """申告タイムを表示形式に変換（MM:SS.ss）"""
        total_seconds = float(self.declared_time)
        minutes = int(total_seconds // 60)
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:05.2f}"
    
    @classmethod
    def time_to_seconds(cls, time_str):
        """
        タイム文字列を秒に変換
        フォーマット: "MM:SS.ss" または "M:SS.ss"
        """
        try:
            parts = time_str.split(':')
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            raise ValueError("Invalid time format")
        except (ValueError, IndexError) as e:
            raise ValidationError('タイムの形式が正しくありません（例: 14:30.00）') from e
    
    @classmethod
    def seconds_to_time(cls, total_seconds):
        """秒をタイム文字列に変換"""
        minutes = int(total_seconds // 60)
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:05.2f}"


class EntryGroup(models.Model):
    """
    団体一括エントリー管理
    複数選手を一括でエントリーし、まとめて決済管理
    """
    STATUS_CHOICES = [
        ('pending', '入金待ち'),
        ('payment_uploaded', '入金確認待ち'),
        ('confirmed', '確定'),
        ('cancelled', 'キャンセル'),
    ]
    
    # 団体・大会紐付け
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='entry_groups',
        verbose_name='団体',
        null=True,
        blank=True
    )
    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name='entry_groups',
        verbose_name='大会'
    )
    
    # 申込者
    registered_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='entry_groups',
        verbose_name='申込者'
    )
    
    # エントリー紐付け
    entries = models.ManyToManyField(
        Entry,
        related_name='entry_groups',
        verbose_name='エントリー'
    )
    
    # 金額
    total_amount = models.PositiveIntegerField('合計金額', default=0)
    
    # 状態
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # 一時保存フラグ（NANS21V参考機能）
    is_draft = models.BooleanField(
        '下書き',
        default=True,
        help_text='一時保存の場合はTrue、確定処理後はFalse'
    )
    
    # メタ情報
    created_at = models.DateTimeField('申込日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = 'エントリーグループ'
        verbose_name_plural = 'エントリーグループ'
        ordering = ['-created_at']
    
    def __str__(self):
        org_name = self.organization.name if self.organization else '個人'
        return f"{org_name} - {self.competition.name} ({self.entries.count()}件)"
    
    def calculate_total(self):
        """合計金額を計算"""
        self.total_amount = self.entries.count() * self.competition.entry_fee
        self.save()
        return self.total_amount
    
    @transaction.atomic
    def confirm_all(self):
        """全エントリーを確定"""
        self.entries.update(status='confirmed')
        self.status = 'confirmed'
        self.save()


# django-auditlog登録
auditlog.register(Entry)
auditlog.register(EntryGroup)
