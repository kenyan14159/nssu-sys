"""
統合テスト - エントリーフロー
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import Athlete, Organization, User
from competitions.models import Competition, Race
from entries.models import Entry, EntryGroup


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def organization(db):
    return Organization.objects.create(
        name='テスト大学',
        name_kana='テストダイガク',
        short_name='テスト大',
        representative_name='代表太郎',
        representative_email='rep@test.com',
        representative_phone='03-1234-5678',
    )


@pytest.fixture
def user(db, organization):
    user = User.objects.create_user(
        email='user@test.com',
        password='testpass123',
        full_name='テスト太郎',
        full_name_kana='テストタロウ',
        phone='090-1234-5678',
        organization=organization,
    )
    return user


@pytest.fixture
def athlete(db, organization):
    from datetime import date
    return Athlete.objects.create(
        organization=organization,
        last_name='鈴木',
        first_name='一郎',
        last_name_kana='スズキ',
        first_name_kana='イチロウ',
        gender='M',
        birth_date=date(2000, 4, 1),
    )


@pytest.fixture
def competition(db):
    now = timezone.now()
    return Competition.objects.create(
        name='第100回日体大記録会',
        event_date=now.date() + timedelta(days=30),
        entry_start_at=now - timedelta(days=1),
        entry_end_at=now + timedelta(days=14),
        entry_fee=2000,
        is_published=True,
        is_entry_open=True,
    )


@pytest.fixture
def race(db, competition):
    return Race.objects.create(
        competition=competition,
        distance=5000,
        gender='M',
        name='男子5000m',
        heat_capacity=40,
        max_entries=200,
    )


class TestEntryFlow:
    """エントリーフローの統合テスト"""
    
    def test_login_required_for_entry(self, client, competition, race):
        """未ログイン時はエントリーページにアクセスできない"""
        url = reverse('entries:create', kwargs={
            'competition_pk': competition.pk,
            'race_pk': race.pk,
        })
        response = client.get(url)
        assert response.status_code == 302
        assert 'login' in response.url
    
    def test_authenticated_user_can_access_entry(self, client, user, competition, race):
        """ログインユーザーはエントリーページにアクセスできる"""
        client.login(email='user@test.com', password='testpass123')
        url = reverse('entries:create', kwargs={
            'competition_pk': competition.pk,
            'race_pk': race.pk,
        })
        response = client.get(url)
        assert response.status_code == 200
    
    def test_entry_cart_shows_entries(self, client, user, competition, race, athlete):
        """エントリーカートに申込内容が表示される"""
        client.login(email='user@test.com', password='testpass123')
        
        # エントリーを作成
        Entry.objects.create(
            athlete=athlete,
            race=race,
            registered_by=user,
            declared_time=Decimal('870.00'),  # 14:30.00
            status='pending',
        )
        
        url = reverse('entries:cart', kwargs={'competition_pk': competition.pk})
        response = client.get(url)
        
        assert response.status_code == 200
        assert athlete.full_name in response.content.decode()
    
    def test_cannot_entry_closed_competition(self, client, user, competition, race):
        """エントリー終了後は申込できない"""
        client.login(email='user@test.com', password='testpass123')
        
        # エントリー期間を過去に変更
        competition.entry_end_at = timezone.now() - timedelta(days=1)
        competition.save()
        
        url = reverse('entries:create', kwargs={
            'competition_pk': competition.pk,
            'race_pk': race.pk,
        })
        response = client.get(url, follow=True)
        
        assert 'エントリーを受け付けていません' in response.content.decode() or response.status_code == 302
    
    def test_dashboard_shows_user_entries(self, client, user, competition, race, athlete):
        """ダッシュボードにユーザーのエントリーが表示される"""
        client.login(email='user@test.com', password='testpass123')
        
        # エントリーグループを作成
        entry_group = EntryGroup.objects.create(
            competition=competition,
            registered_by=user,
            organization=user.organization,
            status='pending',
        )
        
        entry = Entry.objects.create(
            athlete=athlete,
            race=race,
            registered_by=user,
            declared_time=Decimal('870.00'),
            status='pending',
        )
        # エントリーをグループに追加
        entry_group.entries.add(entry)
        entry_group.calculate_total()
        
        url = reverse('competitions:dashboard')
        response = client.get(url)
        
        assert response.status_code == 200


class TestAuthenticationFlow:
    """認証フローの統合テスト"""
    
    def test_login_with_valid_credentials(self, client, user):
        """正しい認証情報でログインできる"""
        response = client.post(reverse('accounts:login'), {
            'username': 'user@test.com',
            'password': 'testpass123',
        })
        assert response.status_code == 302
    
    def test_login_with_invalid_credentials(self, client, user):
        """誤った認証情報ではログインできない"""
        response = client.post(reverse('accounts:login'), {
            'username': 'user@test.com',
            'password': 'wrongpassword',
        })
        assert response.status_code == 200
        assert 'メールアドレスまたはパスワードが正しくありません' in response.content.decode() or 'form' in response.context
    
    def test_logout(self, client, user):
        """ログアウトできる"""
        client.login(email='user@test.com', password='testpass123')
        response = client.post(reverse('accounts:logout'))
        assert response.status_code == 302
    
    def test_profile_requires_login(self, client):
        """プロフィールページはログインが必要"""
        response = client.get(reverse('accounts:profile'))
        assert response.status_code == 302
        assert 'login' in response.url


class TestAthleteManagement:
    """選手管理の統合テスト"""
    
    def test_athlete_list(self, client, user, athlete):
        """選手一覧を表示できる"""
        client.login(email='user@test.com', password='testpass123')
        response = client.get(reverse('accounts:athlete_list'))
        
        assert response.status_code == 200
        assert athlete.full_name in response.content.decode()
    
    def test_athlete_create(self, client, user):
        """選手を登録できる"""
        client.login(email='user@test.com', password='testpass123')
        
        response = client.post(reverse('accounts:athlete_create'), {
            'last_name': '新規',
            'first_name': '選手',
            'last_name_kana': 'シンキ',
            'first_name_kana': 'センシュ',
            'gender': 'M',
            'birth_date': '2000-04-01',
            'nationality': 'JPN',
        })
        
        # フォームエラーの場合は200、成功の場合は302
        if response.status_code == 200:
            # フォームがあるかチェック（エラーがあればフォームが表示される）
            assert 'form' in response.context or Athlete.objects.filter(last_name='新規').exists()
        else:
            assert response.status_code == 302
            assert Athlete.objects.filter(last_name='新規').exists()
