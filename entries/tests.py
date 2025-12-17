"""
entries アプリのテスト
"""
from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from accounts.models import Athlete
from entries.models import Entry, EntryGroup


class TestEntryModel:
    """エントリーモデルのテスト"""
    
    def test_create_entry(self, db, athlete, race, normal_user):
        """エントリー作成"""
        entry = Entry.objects.create(
            athlete=athlete,
            race=race,
            registered_by=normal_user,
            declared_time=Decimal('870.00'),  # 14:30.00
        )
        assert entry.status == 'pending'
        assert entry.declared_time == Decimal('870.00')
    
    def test_entry_str(self, db, athlete, race, normal_user):
        """エントリー文字列表現"""
        entry = Entry.objects.create(
            athlete=athlete,
            race=race,
            registered_by=normal_user,
            declared_time=Decimal('900.00'),
        )
        assert '鈴木 次郎' in str(entry)
        assert '男子5000m' in str(entry)
    
    def test_declared_time_display(self, db, athlete, race, normal_user):
        """申告タイム表示形式"""
        entry = Entry.objects.create(
            athlete=athlete,
            race=race,
            registered_by=normal_user,
            declared_time=Decimal('870.50'),  # 14:30.50
        )
        assert entry.declared_time_display == '14:30.50'
    
    def test_time_to_seconds(self):
        """タイム文字列→秒変換"""
        assert Entry.time_to_seconds('14:30.00') == 870.0
        assert Entry.time_to_seconds('5:00.00') == 300.0
        assert Entry.time_to_seconds('30:00.00') == 1800.0
    
    def test_seconds_to_time(self):
        """秒→タイム文字列変換"""
        assert Entry.seconds_to_time(870.0) == '14:30.00'
        assert Entry.seconds_to_time(300.5) == '5:00.50'
    
    def test_entry_unique_athlete_race(self, db, athlete, race, normal_user):
        """同一選手・種目の重複エントリー不可"""
        from django.db import IntegrityError
        Entry.objects.create(
            athlete=athlete,
            race=race,
            registered_by=normal_user,
            declared_time=Decimal('870.00'),
        )
        with pytest.raises(IntegrityError):
            Entry.objects.create(
                athlete=athlete,
                race=race,  # 同じ種目
                registered_by=normal_user,
                declared_time=Decimal('860.00'),
            )
    
    def test_entry_gender_validation(self, db, organization, race, normal_user):
        """性別バリデーション（男子種目に女子選手）"""
        female_athlete = Athlete.objects.create(
            organization=organization,
            last_name='女性',
            first_name='選手',
            last_name_kana='ジョセイ',
            first_name_kana='センシュ',
            gender='F',  # 女子
            birth_date=date(2000, 1, 1),
        )
        entry = Entry(
            athlete=female_athlete,
            race=race,  # 男子種目
            registered_by=normal_user,
            declared_time=Decimal('900.00'),
        )
        with pytest.raises(ValidationError, match='性別'):
            entry.clean()
    
    def test_entry_status_choices(self, db, athlete, race, normal_user):
        """エントリーステータス変更"""
        entry = Entry.objects.create(
            athlete=athlete,
            race=race,
            registered_by=normal_user,
            declared_time=Decimal('870.00'),
        )
        
        # ステータス遷移
        entry.status = 'payment_uploaded'
        entry.save()
        assert entry.status == 'payment_uploaded'
        
        entry.status = 'confirmed'
        entry.save()
        assert entry.status == 'confirmed'


class TestEntryGroupModel:
    """エントリーグループモデルのテスト"""
    
    def test_create_entry_group(self, db, organization, competition, normal_user):
        """エントリーグループ作成"""
        group = EntryGroup.objects.create(
            organization=organization,
            competition=competition,
            registered_by=normal_user,
            total_amount=5000,
        )
        assert group.status == 'pending'
        assert group.total_amount == 5000


class TestEntryViews:
    """エントリー関連ビューのテスト"""
    
    def test_entry_cart_requires_login(self, client, competition):
        """カートページはログイン必須"""
        response = client.get(f'/entries/competition/{competition.pk}/cart/')
        assert response.status_code == 302
    
    def test_entry_cart_logged_in(self, client_logged_in, competition):
        """ログイン済みでカート表示"""
        response = client_logged_in.get(f'/entries/competition/{competition.pk}/cart/')
        assert response.status_code == 200
    
    def test_entry_create_requires_login(self, client, competition, race):
        """エントリー作成はログイン必須"""
        response = client.get(f'/entries/competition/{competition.pk}/race/{race.pk}/create/')
        assert response.status_code == 302
