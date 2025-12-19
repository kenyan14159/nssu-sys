"""
重要フローの統合テスト

本番運用に必要な重要なビジネスフローをテストします。
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import Athlete, Organization, User
from competitions.models import Competition, Race
from entries.models import Entry, EntryGroup
from heats.models import Heat, HeatAssignment
from payments.models import Payment


class TestEntryToPaymentFlow:
    """エントリー → 確定 → 入金の完全フロー"""
    
    @pytest.fixture
    def setup_data(self, db):
        """テストデータのセットアップ"""
        # 団体作成
        org = Organization.objects.create(
            name='テスト大学',
            name_kana='テストダイガク',
            short_name='テスト大',
            representative_name='代表太郎',
            representative_email='rep@test.com',
            representative_phone='03-1234-5678',
        )
        
        # ユーザー作成
        user = User.objects.create_user(
            email='testuser@test.com',
            password='testpass123',
            full_name='テスト太郎',
            full_name_kana='テストタロウ',
            phone='090-1234-5678',
            organization=org,
        )
        
        # 選手作成
        athlete = Athlete.objects.create(
            organization=org,
            last_name='鈴木',
            first_name='一郎',
            last_name_kana='スズキ',
            first_name_kana='イチロウ',
            gender='M',
            birth_date=date(2000, 4, 1),
        )
        
        # 大会作成
        now = timezone.now()
        competition = Competition.objects.create(
            name='テスト記録会',
            event_date=now.date() + timedelta(days=30),
            entry_start_at=now - timedelta(days=1),
            entry_end_at=now + timedelta(days=14),
            entry_fee=2000,
            is_published=True,
            is_entry_open=True,
        )
        
        # 種目作成
        race = Race.objects.create(
            competition=competition,
            distance=5000,
            gender='M',
            name='男子5000m',
            heat_capacity=40,
            max_entries=200,
        )
        
        return {
            'org': org,
            'user': user,
            'athlete': athlete,
            'competition': competition,
            'race': race,
        }
    
    def test_complete_entry_flow(self, setup_data):
        """エントリー作成から確定までの完全フロー"""
        data = setup_data
        client = Client()
        
        # 1. ログイン
        login_success = client.login(email='testuser@test.com', password='testpass123')
        assert login_success
        
        # 2. エントリー作成
        entry = Entry.objects.create(
            athlete=data['athlete'],
            race=data['race'],
            registered_by=data['user'],
            declared_time=Decimal('870.00'),  # 14:30
            status='pending',
        )
        assert entry.status == 'pending'
        
        # 3. エントリーグループ作成
        entry_group = EntryGroup.objects.create(
            organization=data['org'],
            competition=data['competition'],
            registered_by=data['user'],
            status='pending',
        )
        entry_group.entries.add(entry)
        entry_group.calculate_total()
        
        assert entry_group.total_amount == data['competition'].entry_fee
        
        # 4. カート確認
        cart_url = reverse('entries:cart', kwargs={'competition_pk': data['competition'].pk})
        response = client.get(cart_url)
        assert response.status_code == 200
        
        # 5. エントリー確定（ステータス変更）
        entry_group.status = 'payment_pending'
        entry_group.submitted_at = timezone.now()
        entry_group.save()
        entry.status = 'payment_pending'
        entry.save()
        
        assert entry_group.status == 'payment_pending'
    
    def test_payment_approval_flow(self, setup_data):
        """入金確認から承認までのフロー"""
        data = setup_data
        
        # エントリーグループ作成（入金待ち状態）
        entry_group = EntryGroup.objects.create(
            organization=data['org'],
            competition=data['competition'],
            registered_by=data['user'],
            total_amount=2000,
            status='payment_pending',
        )

        
        # 入金証明アップロード
        image = SimpleUploadedFile(
            name='receipt.png',
            content=b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82',
            content_type='image/png'
        )
        
        payment = Payment.objects.create(
            entry_group=entry_group,
            receipt_image=image,
            status='pending',
        )
        
        assert payment.status == 'pending'
        
        # 管理者による承認
        payment.status = 'approved'
        payment.reviewed_at = timezone.now()
        payment.save()
        
        entry_group.status = 'confirmed'
        entry_group.save()
        
        assert payment.status == 'approved'
        assert entry_group.status == 'confirmed'


class TestHeatAssignmentFlow:
    """番組編成 → チェックインフロー"""
    
    @pytest.fixture
    def setup_heat_data(self, db):
        """番組編成用テストデータ"""
        org = Organization.objects.create(
            name='テスト大学',
            name_kana='テストダイガク',
            short_name='テスト大',
            representative_name='代表太郎',
            representative_email='rep@test.com',
            representative_phone='03-1234-5678',
        )
        
        user = User.objects.create_user(
            email='testuser@test.com',
            password='testpass123',
            full_name='テスト太郎',
            full_name_kana='テストタロウ',
            phone='090-1234-5678',
            organization=org,
        )
        
        admin_user = User.objects.create_superuser(
            email='admin@test.com',
            password='adminpass123',
            full_name='管理太郎',
            full_name_kana='カンリタロウ',
        )
        
        now = timezone.now()
        competition = Competition.objects.create(
            name='テスト記録会',
            event_date=now.date() + timedelta(days=30),
            entry_start_at=now - timedelta(days=14),
            entry_end_at=now - timedelta(days=1),  # エントリー締切済み
            entry_fee=2000,
            is_published=True,
            is_entry_open=False,
        )
        
        race = Race.objects.create(
            competition=competition,
            distance=5000,
            gender='M',
            name='男子5000m',
            heat_capacity=40,
        )
        
        # 複数選手・エントリー作成
        athletes = []
        entries = []
        for i in range(5):
            athlete = Athlete.objects.create(
                organization=org,
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
                registered_by=user,
                declared_time=Decimal(str(850 + i * 10)),
                status='confirmed',
            )
            entries.append(entry)
        
        return {
            'org': org,
            'user': user,
            'admin_user': admin_user,
            'competition': competition,
            'race': race,
            'athletes': athletes,
            'entries': entries,
        }
    
    def test_heat_creation_and_assignment(self, setup_heat_data):
        """組作成と選手割り当て"""
        data = setup_heat_data
        
        # 組作成
        heat = Heat.objects.create(
            race=data['race'],
            heat_number=1,
        )
        
        # 選手を組に割り当て
        for i, entry in enumerate(data['entries']):
            assignment = HeatAssignment.objects.create(
                heat=heat,
                entry=entry,
                bib_number=i + 1,
            )
            assert assignment.status == 'assigned'
        
        assert heat.assignments.count() == 5
    
    def test_checkin_flow(self, setup_heat_data):
        """チェックインフロー"""
        data = setup_heat_data
        
        # 組作成
        heat = Heat.objects.create(
            race=data['race'],
            heat_number=1,
        )
        
        # 選手割り当て
        assignment = HeatAssignment.objects.create(
            heat=heat,
            entry=data['entries'][0],
            bib_number=1,
        )
        
        # チェックイン前の状態確認
        assert not assignment.checked_in
        
        # チェックイン実行
        assignment.checked_in = True
        assignment.checked_in_at = timezone.now()
        assignment.save()
        
        # チェックイン後の状態確認
        assignment.refresh_from_db()
        assert assignment.checked_in
        assert assignment.checked_in_at is not None
    
    def test_dns_marking(self, setup_heat_data):
        """DNS（欠場）マーキング"""
        data = setup_heat_data
        
        heat = Heat.objects.create(
            race=data['race'],
            heat_number=1,
        )
        
        assignment = HeatAssignment.objects.create(
            heat=heat,
            entry=data['entries'][0],
            bib_number=1,
        )
        
        # DNSに変更
        assignment.status = 'dns'
        assignment.save()
        
        assignment.refresh_from_db()
        assert assignment.status == 'dns'


class TestAdminPermissions:
    """管理者権限フロー"""
    
    @pytest.fixture
    def users(self, db):
        """ユーザー作成"""
        org = Organization.objects.create(
            name='テスト大学',
            name_kana='テストダイガク',
            short_name='テスト大',
            representative_name='代表太郎',
            representative_email='rep@test.com',
            representative_phone='03-1234-5678',
        )
        
        normal_user = User.objects.create_user(
            email='normal@test.com',
            password='normalpass123',
            full_name='一般太郎',
            full_name_kana='イッパンタロウ',
            phone='090-1234-5678',
            organization=org,
        )
        
        staff_user = User.objects.create_user(
            email='staff@test.com',
            password='staffpass123',
            full_name='スタッフ太郎',
            full_name_kana='スタッフタロウ',
            phone='090-2345-6789',
            is_staff=True,
        )
        
        admin_user = User.objects.create_superuser(
            email='admin@test.com',
            password='adminpass123',
            full_name='管理太郎',
            full_name_kana='カンリタロウ',
        )
        
        return {
            'normal': normal_user,
            'staff': staff_user,
            'admin': admin_user,
        }
    
    def test_normal_user_cannot_access_admin(self, users):
        """一般ユーザーは管理画面にアクセスできない"""
        client = Client()
        client.login(email='normal@test.com', password='normalpass123')
        
        response = client.get('/admin/')
        # ログインページにリダイレクト
        assert response.status_code == 302
    
    def test_staff_can_access_admin(self, users):
        """スタッフは管理画面にアクセスできる"""
        client = Client()
        client.login(email='staff@test.com', password='staffpass123')
        
        response = client.get('/admin/')
        assert response.status_code == 200
    
    def test_admin_has_full_access(self, users):
        """管理者は全機能にアクセスできる"""
        client = Client()
        client.login(email='admin@test.com', password='adminpass123')
        
        # 管理画面トップ
        response = client.get('/admin/')
        assert response.status_code == 200
        
        # ユーザー管理
        response = client.get('/admin/accounts/user/')
        assert response.status_code == 200
        
        # 大会管理
        response = client.get('/admin/competitions/competition/')
        assert response.status_code == 200
