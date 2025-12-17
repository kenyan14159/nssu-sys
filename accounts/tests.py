"""
accounts アプリのテスト
"""
from datetime import date

import pytest
from django.contrib.auth import get_user_model

from accounts.models import Athlete, Organization

User = get_user_model()


# ===== User モデルのテスト =====

class TestUserModel:
    """ユーザーモデルのテスト"""
    
    def test_create_user(self, db):
        """一般ユーザー作成"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            full_name='テスト太郎',
            full_name_kana='テストタロウ',
            phone='090-1234-5678',
        )
        assert user.email == 'test@example.com'
        assert user.full_name == 'テスト太郎'
        assert user.check_password('testpass123')
        assert not user.is_admin
        assert not user.is_superuser
    
    def test_create_superuser(self, db):
        """管理者ユーザー作成"""
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123',
            full_name='管理者',
            full_name_kana='カンリシャ',
        )
        assert user.is_admin
        assert user.is_superuser
        assert user.is_staff
    
    def test_user_email_required(self, db):
        """メールアドレス必須チェック"""
        with pytest.raises(ValueError, match='メールアドレスは必須です'):
            User.objects.create_user(
                email='',
                password='testpass',
                full_name='Test',
                full_name_kana='Test',
            )
    
    def test_user_str(self, normal_user):
        """ユーザー文字列表現"""
        assert str(normal_user) == '田中花子 (user@test.com)'
    
    def test_display_name_with_org(self, normal_user, organization):
        """団体所属時の表示名"""
        assert normal_user.display_name == 'テスト大学 - 田中花子'
    
    def test_display_name_individual(self, individual_user):
        """個人の表示名"""
        assert individual_user.display_name == '佐藤一郎'


# ===== Organization モデルのテスト =====

class TestOrganizationModel:
    """団体モデルのテスト"""
    
    def test_create_organization(self, db):
        """団体作成"""
        org = Organization.objects.create(
            name='新規大学',
            name_kana='シンキダイガク',
            short_name='新大',
            representative_name='代表太郎',
            representative_email='rep@example.com',
            representative_phone='03-9999-9999',
        )
        assert org.name == '新規大学'
        assert org.is_active
    
    def test_organization_str(self, organization):
        """団体文字列表現"""
        assert str(organization) == 'テスト大学'
    
    def test_organization_unique_name(self, db, organization):
        """団体名のユニーク制約"""
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Organization.objects.create(
                name='テスト大学',  # 重複
                name_kana='テストダイガク',
                representative_name='別代表',
                representative_email='other@example.com',
                representative_phone='03-0000-0000',
            )


# ===== Athlete モデルのテスト =====

class TestAthleteModel:
    """選手モデルのテスト"""
    
    def test_create_athlete(self, db, organization):
        """選手作成"""
        athlete = Athlete.objects.create(
            organization=organization,
            last_name='高橋',
            first_name='三郎',
            last_name_kana='タカハシ',
            first_name_kana='サブロウ',
            gender='M',
            birth_date=date(2001, 5, 15),
        )
        assert athlete.full_name == '高橋 三郎'
        assert athlete.full_name_kana == 'タカハシ サブロウ'
        assert athlete.is_active
    
    def test_athlete_str(self, athlete):
        """選手文字列表現"""
        assert str(athlete) == '鈴木 次郎 (テスト大)'
    
    def test_athlete_age(self, athlete):
        """年齢計算"""
        # birth_date=date(2000, 4, 1) なので、2025年11月時点で25歳
        assert athlete.age == 25
    
    def test_athlete_gender_choices(self, db, organization):
        """性別選択肢"""
        male = Athlete.objects.create(
            organization=organization,
            last_name='男',
            first_name='選手',
            last_name_kana='オトコ',
            first_name_kana='センシュ',
            gender='M',
            birth_date=date(2000, 1, 1),
        )
        assert male.gender == 'M'
        
        female = Athlete.objects.create(
            organization=organization,
            last_name='女',
            first_name='選手',
            last_name_kana='オンナ',
            first_name_kana='センシュ',
            gender='F',
            birth_date=date(2000, 1, 1),
        )
        assert female.gender == 'F'


# ===== ビューのテスト =====

class TestAccountViews:
    """アカウント関連ビューのテスト"""
    
    def test_login_page(self, client):
        """ログインページ表示"""
        response = client.get('/accounts/login/')
        assert response.status_code == 200
        assert 'ログイン' in response.content.decode()
    
    def test_login_success(self, client, normal_user):
        """ログイン成功"""
        response = client.post('/accounts/login/', {
            'username': 'user@test.com',
            'password': 'testpass123',
        })
        assert response.status_code == 302  # リダイレクト
    
    def test_login_failure(self, client, normal_user):
        """ログイン失敗"""
        response = client.post('/accounts/login/', {
            'username': 'user@test.com',
            'password': 'wrongpassword',
        })
        assert response.status_code == 200  # ログインページに留まる
    
    def test_register_page(self, client):
        """新規登録ページ表示"""
        response = client.get('/accounts/register/')
        assert response.status_code == 200
    
    def test_profile_requires_login(self, client):
        """プロフィールページはログイン必須"""
        response = client.get('/accounts/profile/')
        assert response.status_code == 302  # ログインページへリダイレクト
    
    def test_profile_logged_in(self, client_logged_in):
        """ログイン済みでプロフィール表示"""
        response = client_logged_in.get('/accounts/profile/')
        assert response.status_code == 200
    
    def test_athlete_list_requires_login(self, client):
        """選手一覧はログイン必須"""
        response = client.get('/accounts/athletes/')
        assert response.status_code == 302
    
    def test_password_reset_page(self, client):
        """パスワードリセットページ表示"""
        response = client.get('/accounts/password_reset/')
        assert response.status_code == 200
        assert 'パスワードリセット' in response.content.decode()
