"""
payments アプリのテスト
"""
from datetime import time

import pytest

from entries.models import EntryGroup
from payments.models import BankAccount, ParkingRequest, Payment


class TestPaymentModel:
    """決済モデルのテスト"""
    
    def test_create_bank_account(self, db):
        """振込先口座作成"""
        account = BankAccount.objects.create(
            bank_name='テスト銀行',
            branch_name='本店',
            account_type='ordinary',
            account_number='1234567',
            account_holder='ニツタイダイガクリクジヨウブ',
        )
        assert account.is_active
        assert str(account) == 'テスト銀行 本店 1234567'
    
    def test_bank_account_types(self, db):
        """口座種別"""
        ordinary = BankAccount.objects.create(
            bank_name='銀行A',
            branch_name='支店A',
            account_type='ordinary',
            account_number='1111111',
            account_holder='テスト',
        )
        assert ordinary.account_type == 'ordinary'
        
        current = BankAccount.objects.create(
            bank_name='銀行B',
            branch_name='支店B',
            account_type='current',
            account_number='2222222',
            account_holder='テスト',
        )
        assert current.account_type == 'current'


class TestParkingRequestModel:
    """駐車場申請モデルのテスト"""
    
    def test_create_parking_request(self, db, organization, competition, normal_user):
        """駐車場申請作成"""
        request = ParkingRequest.objects.create(
            organization=organization,
            competition=competition,
            requested_by=normal_user,
            requested_large_bus=1,
            requested_medium_bus=0,
            requested_car=3,
        )
        assert request.status == 'requested'
        assert request.total_requested == 4
        assert not request.is_assigned
    
    def test_parking_request_assignment(self, db, organization, competition, normal_user):
        """駐車場割当"""
        request = ParkingRequest.objects.create(
            organization=organization,
            competition=competition,
            requested_by=normal_user,
            requested_large_bus=1,
            requested_car=2,
        )
        
        # 管理者による割当
        request.status = 'assigned'
        request.assigned_parking_lot = 'A駐車場'
        request.assigned_large_bus = 1
        request.assigned_car = 2
        request.entry_time = time(7, 0)
        request.exit_time = time(18, 0)
        request.save()
        
        assert request.is_assigned
        assert request.total_assigned == 3
    
    def test_parking_request_permit_info(self, db, organization, competition, normal_user):
        """駐車許可証情報取得"""
        request = ParkingRequest.objects.create(
            organization=organization,
            competition=competition,
            requested_by=normal_user,
            status='assigned',
            assigned_parking_lot='B駐車場',
            assigned_large_bus=0,
            assigned_medium_bus=1,
            assigned_car=2,
            entry_time=time(8, 0),
            exit_time=time(17, 30),
        )
        
        info = request.get_permit_info()
        assert info['organization_name'] == organization.name
        assert info['parking_lot'] == 'B駐車場'
        assert info['entry_time'] == time(8, 0)
        assert info['medium_bus'] == 1
        assert info['car'] == 2
    
    def test_parking_duplicate_not_allowed(self, db, organization, competition, normal_user):
        """同一大会・団体の重複不可"""
        from django.db import IntegrityError
        
        ParkingRequest.objects.create(
            organization=organization,
            competition=competition,
            requested_by=normal_user,
        )
        
        with pytest.raises(IntegrityError):
            ParkingRequest.objects.create(
                organization=organization,
                competition=competition,
                requested_by=normal_user,
            )


class TestParkingImport:
    """駐車場CSVインポートのテスト"""
    
    def test_import_csv_basic(self, db, organization, competition, admin_user):
        """基本的なCSVインポート"""
        from payments.parking_import import import_parking_csv
        
        csv_content = f'''団体名,駐車場,入庫時間,出庫時間,大型バス,中型バス,乗用車,備考
{organization.name},A駐車場,7:00,18:00,1,0,2,'''
        
        result = import_parking_csv(csv_content, competition, admin_user)
        
        assert result.success_count == 1
        assert result.error_count == 0
        
        # 作成されたレコードを確認
        parking = ParkingRequest.objects.get(organization=organization, competition=competition)
        assert parking.assigned_parking_lot == 'A駐車場'
        assert parking.assigned_large_bus == 1
        assert parking.assigned_car == 2
        assert parking.entry_time == time(7, 0)
    
    def test_import_csv_organization_not_found(self, db, competition, admin_user):
        """存在しない団体名"""
        from payments.parking_import import import_parking_csv
        
        csv_content = '''団体名,駐車場,入庫時間,出庫時間,大型バス,中型バス,乗用車,備考
存在しない大学,C駐車場,9:00,17:00,0,0,1,'''
        
        result = import_parking_csv(csv_content, competition, admin_user)
        
        assert result.success_count == 0
        assert result.error_count == 1
        assert '団体が見つかりません' in result.errors[0]['message']


class TestPaymentViews:
    """決済関連ビューのテスト"""
    
    def test_admin_payment_list_requires_admin(self, client_logged_in):
        """入金一覧は管理者のみ"""
        response = client_logged_in.get('/payments/admin/')
        # 管理者でないのでリダイレクト
        assert response.status_code == 302
    
    def test_admin_payment_list_admin(self, client_admin):
        """管理者は入金一覧表示可能"""
        response = client_admin.get('/payments/admin/')
        assert response.status_code == 200
    
    def test_force_approve_search_requires_admin(self, client_logged_in):
        """強制承認検索は管理者のみ"""
        response = client_logged_in.get('/payments/admin/force-approve/')
        assert response.status_code == 302
    
    def test_force_approve_search_admin(self, client_admin):
        """管理者は強制承認検索可能"""
        response = client_admin.get('/payments/admin/force-approve/')
        assert response.status_code == 200
        assert response.status_code == 200


class TestReceiptGenerator:
    """領収書生成機能のテスト"""
    
    def test_receipt_download_requires_login(self, client):
        """ログインしていないと領収書ダウンロード不可"""
        response = client.get('/payments/receipt/1/download/')
        assert response.status_code == 302
        assert 'login' in response.url
    
    def test_receipt_download_not_approved(self, client_logged_in, db, normal_user, competition, organization):
        """承認されていないエントリーでは領収書ダウンロード不可"""
        
        # エントリーグループ作成
        entry_group = EntryGroup.objects.create(
            organization=organization,
            competition=competition,
            registered_by=normal_user,
            total_amount=3000,
            status='pending'
        )
        
        response = client_logged_in.get(f'/payments/receipt/{entry_group.pk}/download/')
        # Paymentがないためエラー
        assert response.status_code == 302
    
    def test_receipt_pdf_generation(self, db, normal_user, competition, organization):
        """領収書PDF生成テスト"""

        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.utils import timezone

        from payments.receipt_generator import generate_receipt_pdf
        
        # エントリーグループ作成
        entry_group = EntryGroup.objects.create(
            organization=organization,
            competition=competition,
            registered_by=normal_user,
            total_amount=3000,
            status='confirmed'
        )
        
        # 画像ファイル作成
        image = SimpleUploadedFile(
            name='test_image.jpg',
            content=b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82',
            content_type='image/png'
        )
        
        # Payment作成（承認済み）
        payment = Payment.objects.create(
            entry_group=entry_group,
            receipt_image=image,
            status='approved',
            reviewed_at=timezone.now()
        )
        
        # PDF生成
        pdf_data = generate_receipt_pdf(payment)
        
        # PDFデータが返されることを確認
        assert pdf_data is not None
        assert len(pdf_data) > 0
        # PDF形式であることを確認（PDFヘッダ）
        assert pdf_data[:4] == b'%PDF'
