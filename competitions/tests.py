"""
competitions アプリのテスト
"""
from datetime import timedelta

import pytest
from django.utils import timezone

from competitions.models import Competition, Race


class TestCompetitionModel:
    """大会モデルのテスト"""
    
    def test_create_competition(self, db):
        """大会作成"""
        now = timezone.now()
        comp = Competition.objects.create(
            name='テスト大会',
            event_date=now.date() + timedelta(days=30),
            entry_start_at=now,
            entry_end_at=now + timedelta(days=14),
            entry_fee=1500,
        )
        assert comp.name == 'テスト大会'
        assert comp.entry_fee == 1500
        assert comp.default_heat_capacity == 40  # デフォルト値
    
    def test_competition_str(self, competition):
        """大会文字列表現"""
        assert '第1回テスト記録会' in str(competition)
    
    def test_can_entry_true(self, competition):
        """エントリー可能期間内"""
        assert competition.can_entry is True
    
    def test_can_entry_false_not_published(self, db):
        """非公開の場合エントリー不可"""
        now = timezone.now()
        comp = Competition.objects.create(
            name='非公開大会',
            event_date=now.date() + timedelta(days=30),
            entry_start_at=now - timedelta(days=1),
            entry_end_at=now + timedelta(days=14),
            is_published=False,
            is_entry_open=True,
        )
        assert comp.can_entry is False
    
    def test_can_entry_false_before_start(self, db):
        """エントリー開始前"""
        now = timezone.now()
        comp = Competition.objects.create(
            name='開始前大会',
            event_date=now.date() + timedelta(days=60),
            entry_start_at=now + timedelta(days=7),  # まだ開始していない
            entry_end_at=now + timedelta(days=21),
            is_published=True,
            is_entry_open=True,
        )
        assert comp.can_entry is False
    
    def test_can_entry_false_after_end(self, db):
        """エントリー締切後"""
        now = timezone.now()
        comp = Competition.objects.create(
            name='終了大会',
            event_date=now.date() + timedelta(days=30),
            entry_start_at=now - timedelta(days=14),
            entry_end_at=now - timedelta(days=1),  # 既に終了
            is_published=True,
            is_entry_open=True,
        )
        assert comp.can_entry is False
    
    def test_entry_status(self, competition):
        """エントリー状態表示"""
        assert competition.entry_status == 'エントリー受付中'


class TestRaceModel:
    """種目モデルのテスト"""
    
    def test_create_race(self, db, competition):
        """種目作成"""
        race = Race.objects.create(
            competition=competition,
            distance=3000,
            gender='F',
            heat_capacity=35,
        )
        assert race.name == '女子3000m'  # 自動生成
        assert race.heat_capacity == 35
    
    def test_race_str(self, race):
        """種目文字列表現"""
        assert '男子5000m' in str(race)
    
    def test_race_auto_name(self, db, competition):
        """種目名自動生成"""
        race = Race.objects.create(
            competition=competition,
            distance=1500,
            gender='M',
        )
        assert race.name == '男子1500m'
    
    def test_race_custom_name(self, db, competition):
        """種目名カスタム指定"""
        race = Race.objects.create(
            competition=competition,
            distance=5000,
            gender='X',
            name='オープン5000m',
        )
        assert race.name == 'オープン5000m'
    
    def test_entry_count(self, race):
        """エントリー数カウント（初期値0）"""
        assert race.entry_count == 0
    
    def test_is_full_false(self, race):
        """定員未達"""
        assert race.is_full is False
    
    def test_race_unique_together(self, db, competition):
        """同一大会・距離・性別の重複不可"""
        from django.db import IntegrityError
        Race.objects.create(
            competition=competition,
            distance=10000,
            gender='M',
        )
        with pytest.raises(IntegrityError):
            Race.objects.create(
                competition=competition,
                distance=10000,
                gender='M',  # 重複
            )


class TestCompetitionViews:
    """大会関連ビューのテスト"""
    
    def test_competition_list(self, client_logged_in, competition):
        """大会一覧ページ（ログイン必須）"""
        response = client_logged_in.get('/competitions/list/')
        assert response.status_code == 200
    
    def test_competition_detail(self, client_logged_in, competition):
        """大会詳細ページ"""
        response = client_logged_in.get(f'/competitions/{competition.pk}/')
        assert response.status_code == 200
        assert '第1回テスト記録会' in response.content.decode()
    
    def test_dashboard_requires_login(self, client):
        """ダッシュボードはログイン必須"""
        response = client.get('/competitions/')
        assert response.status_code == 302
    
    def test_dashboard_logged_in(self, client_logged_in):
        """ログイン済みでダッシュボード表示"""
        response = client_logged_in.get('/competitions/')
        assert response.status_code == 200
