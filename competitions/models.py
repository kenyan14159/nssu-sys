"""
大会・種目モデル
"""
from auditlog.registry import auditlog
from django.db import models
from django.utils import timezone


class Competition(models.Model):
    """
    大会モデル
    大会名、開催日、エントリー期間設定
    """
    name = models.CharField(
        '大会名', max_length=200,
        help_text='例: 第325回日体大長距離競技会'
    )
    description = models.TextField(
        '大会説明', blank=True,
        help_text='大会の詳細情報や注意事項を記載（任意）'
    )
    
    # 開催情報
    event_date = models.DateField(
        '開催日（初日）',
        help_text='大会の開始日（形式: YYYY-MM-DD）'
    )
    event_end_date = models.DateField(
        '開催日（最終日）',
        null=True,
        blank=True,
        help_text='2日間以上の大会の場合は最終日を指定（1日開催の場合は空欄）'
    )
    venue = models.CharField(
        '会場', max_length=200, 
        default='日本体育大学横浜・健志台キャンパス陸上競技場',
        help_text='開催場所の正式名称'
    )
    
    # エントリー期間
    entry_start_at = models.DateTimeField(
        'エントリー開始日時',
        help_text='この日時からエントリーを受け付けます'
    )
    entry_end_at = models.DateTimeField(
        'エントリー締切日時',
        help_text='この日時でエントリー受付を終了します'
    )
    
    # 参加費設定
    entry_fee = models.PositiveIntegerField(
        '参加費（円）', default=2000,
        help_text='1人あたりの参加費。例: 2000'
    )
    
    # 組定員設定（デフォルト値）
    default_heat_capacity = models.PositiveIntegerField(
        '1組あたりの定員（デフォルト）', default=40,
        help_text='種目で個別設定しない場合に使用される定員数'
    )
    
    # 状態管理
    is_published = models.BooleanField(
        '公開中', default=False,
        help_text='チェックすると参加者から大会が見えるようになります'
    )
    is_entry_open = models.BooleanField(
        'エントリー受付中', default=False,
        help_text='チェックするとエントリーを受け付けます（期間内のみ有効）'
    )
    
    # メタ情報
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = '大会'
        verbose_name_plural = '大会'
        ordering = ['-event_date']
    
    def __str__(self):
        if self.event_end_date:
            return f"{self.name} ({self.event_date} 〜 {self.event_end_date})"
        return f"{self.name} ({self.event_date})"
    
    @property
    def event_date_display(self):
        """開催日の表示形式"""
        if self.event_end_date:
            # 同じ月の場合は省略表示
            if self.event_date.month == self.event_end_date.month:
                return f"{self.event_date.year}年{self.event_date.month}月{self.event_date.day}日〜{self.event_end_date.day}日"
            else:
                return f"{self.event_date.year}年{self.event_date.month}月{self.event_date.day}日〜{self.event_end_date.month}月{self.event_end_date.day}日"
        return f"{self.event_date.year}年{self.event_date.month}月{self.event_date.day}日"
    
    @property
    def is_multi_day(self):
        """複数日開催かどうか"""
        return self.event_end_date is not None
    
    @property
    def can_entry(self):
        """エントリー可能かどうか"""
        now = timezone.now()
        return (
            self.is_published and
            self.is_entry_open and
            self.entry_start_at <= now <= self.entry_end_at
        )
    
    @property
    def entry_status(self):
        """エントリー状態の表示"""
        now = timezone.now()
        if not self.is_published:
            return '非公開'
        if now < self.entry_start_at:
            return 'エントリー開始前'
        if now > self.entry_end_at:
            return 'エントリー終了'
        if self.is_entry_open:
            return 'エントリー受付中'
        return '一時停止中'


class Race(models.Model):
    """
    種目モデル
    男子5000m、女子3000m、組定員設定など
    """
    DISTANCE_CHOICES = [
        (800, '800m'),
        (1500, '1500m'),
        (3000, '3000m'),
        (5000, '5000m'),
        (10000, '10000m'),
    ]
    
    GENDER_CHOICES = [
        ('M', '男子'),
        ('F', '女子'),
        ('X', '混合'),
    ]
    
    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name='races',
        verbose_name='大会'
    )
    
    # 種目情報
    distance = models.PositiveIntegerField('距離（m）', choices=DISTANCE_CHOICES)
    gender = models.CharField('性別区分', max_length=1, choices=GENDER_CHOICES)
    name = models.CharField(
        '種目名', max_length=100, blank=True,
        help_text='空欄の場合は自動生成（例: 男子5000m）。NCG種目などは手動入力可能'
    )
    
    # 定員設定
    heat_capacity = models.PositiveIntegerField('1組あたりの定員', default=40)
    max_entries = models.PositiveIntegerField('エントリー上限', default=50, null=True, blank=True)
    
    # 表示順
    display_order = models.PositiveIntegerField('表示順', default=0)
    
    # 開始予定時刻
    scheduled_start_time = models.TimeField(
        '開始予定時刻',
        null=True,
        blank=True,
        help_text='例: 10:30、14:00'
    )
    
    # NCG（NITTAI CHALLENGE GAMES）フラグ
    is_ncg = models.BooleanField('NCG種目', default=False, help_text='NITTAI CHALLENGE GAMES対象種目')
    ncg_capacity = models.PositiveIntegerField('NCG定員', default=35, help_text='NCG組に入れる上位人数')
    
    # 参加標準記録（秒単位、設定しない場合はNone）
    standard_time = models.DecimalField(
        '参加標準記録（秒）',
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='この記録より遅い申告タイムはエントリー不可。例: 15分30秒 → 930.00'
    )
    
    # 対応する一般種目（NCGから溢れた選手の移動先）
    fallback_race = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ncg_source',
        verbose_name='一般種目（NCG溢れ移動先）',
        help_text='NCG定員超過時に選手を移動する一般種目'
    )
    
    # メタ情報
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    is_active = models.BooleanField('有効', default=True)
    
    class Meta:
        verbose_name = '種目'
        verbose_name_plural = '種目'
        ordering = ['display_order', 'distance']
        unique_together = ['competition', 'name']  # 種目名でユニークに変更（NCG等の対応）
    
    def __str__(self):
        return f"{self.competition.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.name:
            gender_name = dict(self.GENDER_CHOICES).get(self.gender, '')
            distance_name = dict(self.DISTANCE_CHOICES).get(self.distance, f'{self.distance}m')
            self.name = f"{gender_name}{distance_name}"
        super().save(*args, **kwargs)
    
    @property
    def entry_count(self):
        """確定エントリー数"""
        return self.entries.filter(status='confirmed').count()
    
    @property
    def is_full(self):
        """定員に達しているか"""
        if self.max_entries:
            return self.entry_count >= self.max_entries
        return False


# django-auditlog登録
auditlog.register(Competition)
auditlog.register(Race)
