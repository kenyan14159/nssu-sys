"""
番組編成モデル
"""
from auditlog.registry import auditlog
from django.db import models, transaction

from competitions.models import Race
from entries.models import Entry


class Heat(models.Model):
    """
    組モデル
    確定した組番号、開始時刻
    """
    race = models.ForeignKey(
        Race,
        on_delete=models.CASCADE,
        related_name='heats',
        verbose_name='種目'
    )
    
    heat_number = models.PositiveIntegerField('組番号')
    scheduled_start_time = models.TimeField('開始予定時刻', null=True, blank=True)
    
    # メタ情報
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    is_finalized = models.BooleanField('確定済み', default=False)
    
    class Meta:
        verbose_name = '組'
        verbose_name_plural = '組'
        ordering = ['race', 'heat_number']
        unique_together = ['race', 'heat_number']
    
    def __str__(self):
        return f"{self.race.name} {self.heat_number}組"
    
    @property
    def entry_count(self):
        return self.assignments.count()


class HeatAssignment(models.Model):
    """
    組編成モデル
    エントリーと組・腰ナンバーの紐付け
    """
    STATUS_CHOICES = [
        ('assigned', '出走予定'),
        ('dns', '欠場（DNS）'),
        ('dnf', '途中棄権（DNF）'),
        ('dq', '失格（DQ）'),
    ]
    
    heat = models.ForeignKey(
        Heat,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name='組'
    )
    entry = models.OneToOneField(
        Entry,
        on_delete=models.CASCADE,
        related_name='heat_assignment',
        verbose_name='エントリー'
    )
    
    # 腰ナンバー（レーン番号）- 各組内で1から連番
    bib_number = models.PositiveIntegerField('腰ナンバー')
    
    # ゼッケン番号（大会全体で一意）
    race_bib_number = models.PositiveIntegerField(
        'ゼッケン番号',
        null=True,
        blank=True,
        help_text='大会全体で一意のゼッケン番号'
    )
    
    # 状態
    status = models.CharField(
        'ステータス',
        max_length=10,
        choices=STATUS_CHOICES,
        default='assigned'
    )
    
    # 当日点呼
    checked_in = models.BooleanField('点呼済み', default=False)
    checked_in_at = models.DateTimeField('点呼時刻', null=True, blank=True)
    
    # メタ情報
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = '組編成'
        verbose_name_plural = '組編成'
        ordering = ['heat', 'bib_number']
        unique_together = [
            ['heat', 'bib_number'],
            ['heat', 'entry'],
        ]
    
    def __str__(self):
        return f"{self.heat} - {self.bib_number}番 {self.entry.athlete.full_name}"


class HeatGenerator:
    """
    自動番組編成ロジック
    """
    
    @classmethod
    @transaction.atomic
    def generate_heats(cls, race, force_regenerate=False, include_pending=False, num_heats=None):
        """
        種目の組分けを自動生成
        
        1. 種目ごとにエントリーを「申告タイム順」にソート
        2. 設定された「1組あたりの最大人数」または指定された組数で自動分割
        3. 組番号・腰ナンバー（レーン番号）を自動付与
        
        Args:
            race: 対象種目
            force_regenerate: 既存の未確定組を削除して再生成するか
            include_pending: 入金待ちのエントリーも含めるか（締切後の組編成用）
            num_heats: 組数を指定（None の場合は定員から自動計算）
        
        Returns:
            list: 生成した Heat オブジェクトのリスト
        """
        # 既存の組を削除（再生成の場合）
        if force_regenerate:
            # 既存のHeatAssignmentも削除される（CASCADE）
            Heat.objects.filter(race=race, is_finalized=False).delete()
        
        # エントリーを取得（ステータスでフィルタ）
        if include_pending:
            # 入金待ち・確定の両方を含める
            statuses = ['pending', 'payment_uploaded', 'confirmed']
        else:
            # 確定済みのみ
            statuses = ['confirmed']
        
        entries = list(Entry.objects.filter(
            race=race,
            status__in=statuses
        ).order_by('declared_time'))  # タイム順（速い順）
        
        if not entries:
            return []
        
        # 組数と1組あたりの人数を計算
        total_entries = len(entries)
        
        if num_heats:
            # 組数が指定されている場合
            capacity = (total_entries + num_heats - 1) // num_heats  # 切り上げ
        else:
            # 組定員から自動計算
            capacity = race.heat_capacity
            num_heats = (total_entries + capacity - 1) // capacity  # 切り上げ
        
        # 組分け
        heats = []
        current_heat = None
        bib_number = 0
        
        for i, entry in enumerate(entries):
            # 新しい組を作成
            if i % capacity == 0:
                heat_number = (i // capacity) + 1
                current_heat = Heat.objects.create(
                    race=race,
                    heat_number=heat_number
                )
                heats.append(current_heat)
                bib_number = 0
            
            bib_number += 1
            
            # 組編成を作成
            HeatAssignment.objects.create(
                heat=current_heat,
                entry=entry,
                bib_number=bib_number
            )
        
        return heats
    
    @classmethod
    @transaction.atomic
    def move_entry(cls, assignment, target_heat, new_bib_number=None):
        """
        選手を別の組に移動
        
        手動調整用（PM配置や大学ごとのバラつき調整）
        """
        old_heat = assignment.heat
        
        # 新しい腰ナンバーを計算
        if new_bib_number is None:
            max_bib = HeatAssignment.objects.filter(heat=target_heat).aggregate(
                models.Max('bib_number')
            )['bib_number__max'] or 0
            new_bib_number = max_bib + 1
        
        # 移動
        assignment.heat = target_heat
        assignment.bib_number = new_bib_number
        assignment.save()
        
        # 元の組の腰ナンバーを詰める
        cls.reorder_bib_numbers(old_heat)
        
        return assignment
    
    @classmethod
    def reorder_bib_numbers(cls, heat):
        """腰ナンバーを1から連番に振り直す"""
        assignments = HeatAssignment.objects.filter(heat=heat).order_by('bib_number')
        for i, assignment in enumerate(assignments, start=1):
            if assignment.bib_number != i:
                assignment.bib_number = i
                assignment.save()
    
    @classmethod
    @transaction.atomic
    def process_ncg_entries(cls, ncg_race):
        """
        NCG種目のエントリーを処理
        
        NCGロジック:
        1. タイム上位順にソート
        2. 上位N名（ncg_capacity）をNCG組に確定
        3. N+1位以下の選手は一般種目に自動移動
        
        Args:
            ncg_race: NCG種目のRaceオブジェクト
        
        Returns:
            dict: 処理結果 {'ncg_entries': [...], 'moved_entries': [...]}
        """
        if not ncg_race.is_ncg:
            raise ValueError(f'{ncg_race.name}はNCG種目ではありません')
        
        if not ncg_race.fallback_race:
            raise ValueError(f'{ncg_race.name}の移動先一般種目が設定されていません')
        
        # 確定済みエントリーを申告タイム順に取得
        entries = list(Entry.objects.filter(
            race=ncg_race,
            status='confirmed'
        ).order_by('declared_time'))
        
        ncg_capacity = ncg_race.ncg_capacity
        fallback_race = ncg_race.fallback_race
        
        # NCG組に残る選手
        ncg_entries = entries[:ncg_capacity]
        
        # 一般種目に移動する選手
        overflow_entries = entries[ncg_capacity:]
        
        moved_entries = []
        for entry in overflow_entries:
            # 元のNCG種目を記録
            entry.original_ncg_race = ncg_race
            entry.moved_from_ncg = True
            # 種目を一般種目に変更
            entry.race = fallback_race
            entry.save()
            moved_entries.append(entry)
        
        return {
            'ncg_entries': ncg_entries,
            'moved_entries': moved_entries,
            'ncg_count': len(ncg_entries),
            'moved_count': len(moved_entries),
        }
    
    @classmethod
    @transaction.atomic
    def generate_heats_with_ncg(cls, competition, force_regenerate=False):
        """
        大会全体の組分けを生成（NCG処理を含む）
        
        処理順序:
        1. NCG種目のエントリーを処理（定員超過分を一般種目に移動）
        2. 一般種目の組分けを生成
        3. NCG種目の組分けを生成
        
        Args:
            competition: 大会オブジェクト
            force_regenerate: 既存の組を削除して再生成するか
        
        Returns:
            dict: 処理結果
        """
        from competitions.models import Race
        
        results = {
            'ncg_processed': [],
            'heats_generated': [],
            'errors': [],
        }
        
        # 1. NCG種目を先に処理
        ncg_races = Race.objects.filter(
            competition=competition,
            is_ncg=True,
            is_active=True
        )
        
        for ncg_race in ncg_races:
            try:
                ncg_result = cls.process_ncg_entries(ncg_race)
                results['ncg_processed'].append({
                    'race': ncg_race.name,
                    'ncg_count': ncg_result['ncg_count'],
                    'moved_count': ncg_result['moved_count'],
                })
            except Exception as e:
                results['errors'].append({
                    'race': ncg_race.name,
                    'error': str(e),
                })
        
        # 2. 一般種目の組分けを生成
        general_races = Race.objects.filter(
            competition=competition,
            is_ncg=False,
            is_active=True
        )
        
        for race in general_races:
            try:
                heats = cls.generate_heats(race, force_regenerate=force_regenerate)
                results['heats_generated'].append({
                    'race': race.name,
                    'heat_count': len(heats),
                })
            except Exception as e:
                results['errors'].append({
                    'race': race.name,
                    'error': str(e),
                })
        
        # 3. NCG種目の組分けを生成
        for ncg_race in ncg_races:
            try:
                heats = cls.generate_heats(ncg_race, force_regenerate=force_regenerate)
                results['heats_generated'].append({
                    'race': ncg_race.name,
                    'heat_count': len(heats),
                })
            except Exception as e:
                results['errors'].append({
                    'race': ncg_race.name,
                    'error': str(e),
                })
        
        return results


class BibNumberGenerator:
    """
    ゼッケン番号自動採番ロジック
    
    ルール:
    - NCG男子: 1〜499
    - NCG女子: 500〜999
    - 一般男子: 1000〜1999
    - 一般女子: 2000〜2999
    - 腰ナンバー: 各組で1から連番
    """
    
    # ゼッケン番号の開始番号
    BIB_RANGES = {
        ('M', True): 1,      # NCG男子
        ('F', True): 500,    # NCG女子
        ('M', False): 1000,  # 一般男子
        ('F', False): 2000,  # 一般女子
        ('X', True): 3000,   # NCG混合
        ('X', False): 3500,  # 一般混合
    }
    
    @classmethod
    @transaction.atomic
    def assign_bib_numbers(cls, competition):
        """
        大会全体のゼッケン番号を採番
        
        Args:
            competition: 大会オブジェクト
        
        Returns:
            dict: 採番結果
        """
        from competitions.models import Race
        
        results = {
            'assigned': [],
            'errors': [],
        }
        
        # カウンター初期化
        counters = dict(cls.BIB_RANGES)
        
        # 種目を取得（NCG → 一般の順、タイム順）
        races = Race.objects.filter(
            competition=competition,
            is_active=True
        ).order_by('-is_ncg', 'display_order')
        
        for race in races:
            key = (race.gender, race.is_ncg)
            current_bib = counters.get(key, 4000)
            
            # 組ごとに処理
            heats = race.heats.order_by('heat_number')
            
            for heat in heats:
                assignments = heat.assignments.order_by('bib_number')
                
                for assignment in assignments:
                    # ゼッケン番号を更新
                    assignment.race_bib_number = current_bib
                    assignment.save()
                    current_bib += 1
            
            # カウンター更新
            counters[key] = current_bib
            
            results['assigned'].append({
                'race': race.name,
                'start_bib': cls.BIB_RANGES.get(key, 4000),
                'end_bib': current_bib - 1,
            })
        
        return results
    
    @classmethod
    def get_next_bib_number(cls, race):
        """
        次のゼッケン番号を取得
        
        Args:
            race: 種目オブジェクト
        
        Returns:
            int: 次のゼッケン番号
        """
        key = (race.gender, race.is_ncg)
        base_number = cls.BIB_RANGES.get(key, 4000)
        
        # 既に割り当て済みの最大番号を取得
        max_bib = HeatAssignment.objects.filter(
            heat__race=race,
            race_bib_number__isnull=False
        ).aggregate(models.Max('race_bib_number'))['race_bib_number__max']
        
        if max_bib is None:
            return base_number
        
        return max_bib + 1


# django-auditlog登録
auditlog.register(Heat)
auditlog.register(HeatAssignment)
