"""
conftest.py - pytest フィクスチャ設定
"""
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import Athlete, Organization
from competitions.models import Competition, Race

User = get_user_model()


@pytest.fixture
def organization(db):
    """テスト用団体"""
    return Organization.objects.create(
        name='テスト大学',
        name_kana='テストダイガク',
        short_name='テスト大',
        representative_name='山田太郎',
        representative_email='yamada@test-univ.ac.jp',
        representative_phone='03-1234-5678',
    )


@pytest.fixture
def admin_user(db):
    """管理者ユーザー"""
    return User.objects.create_superuser(
        email='admin@test.com',
        password='testpass123',
        full_name='管理者',
        full_name_kana='カンリシャ',
        phone='090-0000-0000',
    )


@pytest.fixture
def normal_user(db, organization):
    """一般ユーザー（団体代表者）"""
    return User.objects.create_user(
        email='user@test.com',
        password='testpass123',
        full_name='田中花子',
        full_name_kana='タナカハナコ',
        phone='090-1111-1111',
        organization=organization,
    )


@pytest.fixture
def individual_user(db):
    """個人参加ユーザー"""
    return User.objects.create_user(
        email='individual@test.com',
        password='testpass123',
        full_name='佐藤一郎',
        full_name_kana='サトウイチロウ',
        phone='090-2222-2222',
        is_individual=True,
    )


@pytest.fixture
def athlete(db, organization):
    """テスト用選手"""
    return Athlete.objects.create(
        organization=organization,
        last_name='鈴木',
        first_name='次郎',
        last_name_kana='スズキ',
        first_name_kana='ジロウ',
        gender='M',
        birth_date=date(2000, 4, 1),
        jaaf_id='T123456',
    )


@pytest.fixture
def competition(db):
    """テスト用大会"""
    now = timezone.now()
    return Competition.objects.create(
        name='第1回テスト記録会',
        description='テスト用の記録会です',
        event_date=now.date() + timedelta(days=30),
        entry_start_at=now - timedelta(days=7),
        entry_end_at=now + timedelta(days=14),
        entry_fee=1000,
        default_heat_capacity=40,
        is_published=True,
        is_entry_open=True,
    )


@pytest.fixture
def race(db, competition):
    """テスト用種目"""
    return Race.objects.create(
        competition=competition,
        distance=5000,
        gender='M',
        name='男子5000m',
        heat_capacity=40,
        max_entries=200,
        display_order=1,
    )


@pytest.fixture
def client_logged_in(client, normal_user):
    """ログイン済みクライアント"""
    client.login(email='user@test.com', password='testpass123')
    return client


@pytest.fixture
def client_admin(client, admin_user):
    """管理者ログイン済みクライアント"""
    client.login(email='admin@test.com', password='testpass123')
    return client
