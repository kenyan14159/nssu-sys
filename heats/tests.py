"""
heats アプリのテスト
"""
from decimal import Decimal

import pytest

from entries.models import Entry
from heats.models import Heat, HeatAssignment, HeatGenerator


class TestHeatModel:
    """組モデルのテスト"""
    
    def test_create_heat(self, db, race):
        """組作成"""
        heat = Heat.objects.create(
            race=race,
            heat_number=1,
        )
        assert heat.heat_number == 1
        assert not heat.is_finalized
    
    def test_heat_str(self, db, race):
        """組文字列表現"""
        heat = Heat.objects.create(
            race=race,
            heat_number=3,
        )
        assert '3組' in str(heat)
    
    def test_heat_entry_count(self, db, race):
        """組のエントリー数"""
        heat = Heat.objects.create(
            race=race,
            heat_number=1,
        )
        assert heat.entry_count == 0
    
    def test_heat_unique_together(self, db, race):
        """同一種目内で組番号の重複不可"""
        from django.db import IntegrityError
        Heat.objects.create(race=race, heat_number=1)
        with pytest.raises(IntegrityError):
            Heat.objects.create(race=race, heat_number=1)


class TestHeatAssignmentModel:
    """組編成モデルのテスト"""
    
    def test_create_assignment(self, db, race, athlete, normal_user):
        """組編成作成"""
        heat = Heat.objects.create(race=race, heat_number=1)
        entry = Entry.objects.create(
            athlete=athlete,
            race=race,
            registered_by=normal_user,
            declared_time=Decimal('870.00'),
            status='confirmed',
        )
        assignment = HeatAssignment.objects.create(
            heat=heat,
            entry=entry,
            bib_number=1,
        )
        assert assignment.status == 'assigned'
        assert not assignment.checked_in
    
    def test_assignment_str(self, db, race, athlete, normal_user):
        """組編成文字列表現"""
        heat = Heat.objects.create(race=race, heat_number=1)
        entry = Entry.objects.create(
            athlete=athlete,
            race=race,
            registered_by=normal_user,
            declared_time=Decimal('870.00'),
            status='confirmed',
        )
        assignment = HeatAssignment.objects.create(
            heat=heat,
            entry=entry,
            bib_number=5,
        )
        assert '5番' in str(assignment)
        assert '鈴木 次郎' in str(assignment)
    
    def test_assignment_status_choices(self, db, race, athlete, normal_user):
        """組編成ステータス"""
        heat = Heat.objects.create(race=race, heat_number=1)
        entry = Entry.objects.create(
            athlete=athlete,
            race=race,
            registered_by=normal_user,
            declared_time=Decimal('870.00'),
            status='confirmed',
        )
        assignment = HeatAssignment.objects.create(
            heat=heat,
            entry=entry,
            bib_number=1,
        )
        
        # DNS に変更
        assignment.status = 'dns'
        assignment.save()
        assert assignment.status == 'dns'


class TestHeatGenerator:
    """番組自動生成のテスト"""
    
    def test_generate_heats_no_entries(self, db, race):
        """エントリーなしの場合"""
        heats = HeatGenerator.generate_heats(race)
        assert heats == []
    
    def test_generate_heats_with_entries(self, db, race, organization, normal_user):
        """複数エントリーありの場合"""
        from datetime import date

        from accounts.models import Athlete
        
        # 複数選手・エントリーを作成
        athletes = []
        entries = []
        for i in range(5):
            athlete = Athlete.objects.create(
                organization=organization,
                last_name=f'選手{i}',
                first_name='太郎',
                last_name_kana=f'センシュ{i}',
                first_name_kana='タロウ',
                gender='M',
                birth_date=date(2000, 1, 1),
            )
            athletes.append(athlete)
            
            entry = Entry.objects.create(
                athlete=athlete,
                race=race,
                registered_by=normal_user,
                declared_time=Decimal(str(850 + i * 10)),  # タイム順
                status='confirmed',
            )
            entries.append(entry)
        
        # 組生成
        heats = HeatGenerator.generate_heats(race)
        
        assert len(heats) == 1  # 5人なので1組
        assert heats[0].assignments.count() == 5
    
    def test_generate_heats_multiple_heats(self, db, competition, organization, normal_user):
        """複数組に分割される場合"""
        from datetime import date

        from accounts.models import Athlete
        from competitions.models import Race
        
        # 定員3名の種目
        race = Race.objects.create(
            competition=competition,
            distance=1500,
            gender='M',
            heat_capacity=3,  # 1組3名
        )
        
        # 7人作成 → 3組になるはず
        for i in range(7):
            athlete = Athlete.objects.create(
                organization=organization,
                last_name=f'ランナー{i}',
                first_name='次郎',
                last_name_kana=f'ランナー{i}',
                first_name_kana='ジロウ',
                gender='M',
                birth_date=date(2000, 1, 1),
            )
            Entry.objects.create(
                athlete=athlete,
                race=race,
                registered_by=normal_user,
                declared_time=Decimal(str(240 + i * 5)),
                status='confirmed',
            )
        
        heats = HeatGenerator.generate_heats(race)
        
        assert len(heats) == 3  # 3組
        assert heats[0].assignments.count() == 3
        assert heats[1].assignments.count() == 3
        assert heats[2].assignments.count() == 1


class TestNCGLogic:
    """NCG（ネクストジェネレーションチャレンジ）ロジックのテスト"""
    
    def test_ncg_entries_within_capacity(self, db, competition, organization, normal_user):
        """NCG定員以内の場合はスライドなし"""
        from datetime import date

        from accounts.models import Athlete
        from competitions.models import Race
        
        # NCG種目を作成（定員3名）
        ncg_race = Race.objects.create(
            competition=competition,
            name='男子5000m NCG',
            distance=5000,
            gender='M',
            heat_capacity=30,
            is_ncg=True,
            ncg_capacity=3,
            standard_time=Decimal('900.00'),
        )
        
        # 一般種目（フォールバック先）
        general_race = Race.objects.create(
            competition=competition,
            name='男子5000m',
            distance=5000,
            gender='M',
            heat_capacity=30,
        )
        ncg_race.fallback_race = general_race
        ncg_race.save()
        
        # 3名エントリー（定員ちょうど）
        for i in range(3):
            athlete = Athlete.objects.create(
                organization=organization,
                last_name=f'NCG選手{i}',
                first_name='太郎',
                last_name_kana=f'エヌシージーセンシュ{i}',
                first_name_kana='タロウ',
                gender='M',
                birth_date=date(2000, 1, 1),
            )
            Entry.objects.create(
                athlete=athlete,
                race=ncg_race,
                registered_by=normal_user,
                declared_time=Decimal(str(850 + i * 10)),
                status='confirmed',
            )
        
        # NCGエントリー処理
        HeatGenerator.process_ncg_entries(ncg_race)
        
        # 全員NCG種目のまま
        assert ncg_race.entries.count() == 3
        assert general_race.entries.count() == 0
    
    def test_ncg_entries_over_capacity_slide_to_general(self, db, competition, organization, normal_user):
        """NCG定員超過の場合は下位がスライド"""
        from datetime import date

        from accounts.models import Athlete
        from competitions.models import Race
        
        # NCG種目（定員3名）
        ncg_race = Race.objects.create(
            competition=competition,
            name='男子5000m NCG',
            distance=5000,
            gender='M',
            heat_capacity=30,
            is_ncg=True,
            ncg_capacity=3,
            standard_time=Decimal('900.00'),
        )
        
        # 一般種目
        general_race = Race.objects.create(
            competition=competition,
            name='男子5000m',
            distance=5000,
            gender='M',
            heat_capacity=30,
        )
        ncg_race.fallback_race = general_race
        ncg_race.save()
        
        # 5名エントリー（2名超過）
        athletes = []
        for i in range(5):
            athlete = Athlete.objects.create(
                organization=organization,
                last_name=f'NCG選手{i}',
                first_name='太郎',
                last_name_kana=f'エヌシージーセンシュ{i}',
                first_name_kana='タロウ',
                gender='M',
                birth_date=date(2000, 1, 1),
            )
            athletes.append(athlete)
            Entry.objects.create(
                athlete=athlete,
                race=ncg_race,
                registered_by=normal_user,
                declared_time=Decimal(str(850 + i * 10)),  # タイム順：850, 860, 870, 880, 890
                status='confirmed',
            )
        
        # NCGエントリー処理
        HeatGenerator.process_ncg_entries(ncg_race)
        
        # NCGに3名、一般に2名
        assert ncg_race.entries.count() == 3
        assert general_race.entries.count() == 2
        
        # スライドされたエントリーのフラグ確認
        slid_entries = Entry.objects.filter(moved_from_ncg=True)
        assert slid_entries.count() == 2
        
        # 遅いタイム（880, 890）の選手がスライド
        slid_athletes = [e.athlete for e in slid_entries]
        assert athletes[3] in slid_athletes
        assert athletes[4] in slid_athletes
    
    def test_ncg_no_fallback_race(self, db, competition, organization, normal_user):
        """フォールバック先がない場合は例外が発生"""
        from datetime import date

        import pytest

        from accounts.models import Athlete
        from competitions.models import Race
        
        # NCG種目（フォールバックなし）
        ncg_race = Race.objects.create(
            competition=competition,
            name='男子5000m NCG',
            distance=5000,
            gender='M',
            heat_capacity=30,
            is_ncg=True,
            ncg_capacity=2,
            standard_time=Decimal('900.00'),
        )
        
        # 3名エントリー（1名超過だがフォールバックなし）
        for i in range(3):
            athlete = Athlete.objects.create(
                organization=organization,
                last_name=f'NCG選手{i}',
                first_name='太郎',
                last_name_kana=f'エヌシージーセンシュ{i}',
                first_name_kana='タロウ',
                gender='M',
                birth_date=date(2000, 1, 1),
            )
            Entry.objects.create(
                athlete=athlete,
                race=ncg_race,
                registered_by=normal_user,
                declared_time=Decimal(str(850 + i * 10)),
                status='confirmed',
            )
        
        # フォールバック先がないためValueErrorが発生
        with pytest.raises(ValueError) as excinfo:
            HeatGenerator.process_ncg_entries(ncg_race)
        
        assert '移動先一般種目が設定されていません' in str(excinfo.value)


class TestHeatViews:
    """番組編成関連ビューのテスト"""
    
    def test_heat_management_requires_admin(self, client_logged_in, competition):
        """番組編成管理は管理者のみ"""
        response = client_logged_in.get(f'/heats/competition/{competition.pk}/')
        assert response.status_code == 302  # リダイレクト
    
    def test_heat_management_admin(self, client_admin, competition):
        """管理者は番組編成管理可能"""
        response = client_admin.get(f'/heats/competition/{competition.pk}/')
        assert response.status_code == 200
    
    def test_heat_list_requires_admin(self, client_logged_in, race):
        """組一覧は管理者のみ"""
        response = client_logged_in.get(f'/heats/race/{race.pk}/')
        assert response.status_code == 302
