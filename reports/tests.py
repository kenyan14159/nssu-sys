"""
reports アプリのテスト
"""
from reports.generators import CSVGenerator, PDFGenerator
from reports.models import ReportLog


class TestReportLogModel:
    """帳票ログモデルのテスト"""
    
    def test_create_report_log(self, db, competition, admin_user):
        """帳票ログ作成"""
        log = ReportLog.objects.create(
            report_type='csv_startlist',
            competition=competition,
            generated_by=admin_user,
        )
        assert log.report_type == 'csv_startlist'
        assert 'CSV' in log.get_report_type_display()
    
    def test_report_types(self, db, competition, admin_user):
        """帳票種別"""
        types = ['csv_startlist', 'pdf_rollcall', 'pdf_program', 'pdf_all']
        for rtype in types:
            log = ReportLog.objects.create(
                report_type=rtype,
                competition=competition,
                generated_by=admin_user,
            )
            assert log.report_type == rtype


class TestCSVGenerator:
    """CSV生成のテスト"""
    
    def test_generate_startlist_csv_empty(self, db, race):
        """エントリーなしの場合のCSV"""
        csv_content = CSVGenerator.generate_startlist_csv(race)
        assert 'Heat,Lane,Bib' in csv_content  # ヘッダーは存在
    
    def test_generate_all_data_csv_empty(self, db, competition):
        """大会データなしの場合のCSV"""
        csv_content = CSVGenerator.generate_all_data_csv(competition)
        assert 'Race,Heat,Lane' in csv_content  # ヘッダーは存在


class TestPDFGenerator:
    """PDF生成のテスト"""
    
    def test_setup_fonts(self):
        """フォント設定"""
        font_name = PDFGenerator._setup_fonts()
        # フォントが見つかればJapanese、なければHelvetica
        assert font_name in ['Japanese', 'Helvetica']
