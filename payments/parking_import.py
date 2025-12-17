"""
駐車場割当CSVインポート機能
Excelで作成した配車表をCSVでインポートし、ParkingRequestテーブルに保存する
"""
import csv
import io
from datetime import datetime
from difflib import SequenceMatcher

from django.db import transaction

from accounts.models import Organization
from payments.models import ParkingRequest


class ParkingImportResult:
    """インポート結果を保持するクラス"""
    
    def __init__(self):
        self.success_count = 0
        self.error_count = 0
        self.warnings = []
        self.errors = []
        self.updated_records = []
    
    def add_success(self, org_name, parking_lot):
        self.success_count += 1
        self.updated_records.append({
            'organization': org_name,
            'parking_lot': parking_lot,
            'status': 'success'
        })
    
    def add_warning(self, row_num, message, org_name=None):
        self.warnings.append({
            'row': row_num,
            'message': message,
            'organization': org_name
        })
    
    def add_error(self, row_num, message, org_name=None):
        self.error_count += 1
        self.errors.append({
            'row': row_num,
            'message': message,
            'organization': org_name
        })


def find_organization_by_name(name, threshold=0.8):
    """
    組織名で団体を検索
    完全一致しない場合は類似度で候補を探す
    
    Args:
        name: 検索する団体名
        threshold: 類似度の閾値 (0.0-1.0)
    
    Returns:
        (Organization or None, list of candidates)
    """
    # 完全一致
    exact_match = Organization.objects.filter(name=name).first()
    if exact_match:
        return exact_match, []
    
    # 短縮名で検索
    short_match = Organization.objects.filter(short_name=name).first()
    if short_match:
        return short_match, []
    
    # 部分一致
    partial_matches = Organization.objects.filter(name__icontains=name)
    if partial_matches.count() == 1:
        return partial_matches.first(), []
    
    # 類似度検索
    all_orgs = Organization.objects.filter(is_active=True)
    candidates = []
    
    for org in all_orgs:
        # 団体名との類似度
        ratio = SequenceMatcher(None, name, org.name).ratio()
        if ratio >= threshold:
            candidates.append((org, ratio))
        
        # 短縮名との類似度
        if org.short_name:
            short_ratio = SequenceMatcher(None, name, org.short_name).ratio()
            if short_ratio >= threshold:
                candidates.append((org, short_ratio))
    
    # 類似度でソート
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    # 類似度が高い1件だけ一致とみなす場合
    if candidates and candidates[0][1] >= 0.9:
        return candidates[0][0], []
    
    return None, [c[0] for c in candidates[:3]]


def parse_time(time_str):
    """
    時刻文字列をTimeオブジェクトに変換
    対応形式: "HH:MM", "H:MM", "HH時MM分"
    """
    if not time_str or time_str.strip() == '':
        return None
    
    time_str = time_str.strip()
    
    # "HH時MM分" 形式
    if '時' in time_str:
        time_str = time_str.replace('時', ':').replace('分', '')
    
    try:
        # "HH:MM" 形式
        if ':' in time_str:
            parts = time_str.split(':')
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
    except (ValueError, IndexError):
        pass
    
    return None


@transaction.atomic
def import_parking_csv(csv_file, competition, created_by_user):
    """
    駐車場割当CSVをインポート
    
    CSVフォーマット:
    団体名,駐車場,入庫時間,出庫時間,大型バス,中型バス,乗用車,備考
    
    Args:
        csv_file: CSVファイル（ファイルオブジェクトまたは文字列）
        competition: Competition インスタンス
        created_by_user: インポート実行ユーザー
    
    Returns:
        ParkingImportResult
    """
    result = ParkingImportResult()
    
    # ファイル読み込み
    if isinstance(csv_file, str):
        content = csv_file
    else:
        # ファイルオブジェクトの場合
        content = csv_file.read()
        if isinstance(content, bytes):
            # BOM付きUTF-8やShift-JISに対応
            for encoding in ['utf-8-sig', 'utf-8', 'shift-jis', 'cp932']:
                try:
                    content = content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
    
    # CSVパース
    reader = csv.DictReader(io.StringIO(content))
    
    # 必須カラムの確認
    required_columns = ['団体名', '駐車場']
    if reader.fieldnames:
        missing = [col for col in required_columns if col not in reader.fieldnames]
        if missing:
            result.add_error(0, f'必須カラムがありません: {", ".join(missing)}')
            return result
    
    for row_num, row in enumerate(reader, start=2):  # ヘッダー行を1として、データは2から
        org_name = row.get('団体名', '').strip()
        
        if not org_name:
            result.add_warning(row_num, '団体名が空のため、スキップしました')
            continue
        
        # 団体の検索
        organization, candidates = find_organization_by_name(org_name)
        
        if not organization:
            if candidates:
                candidate_names = ', '.join([c.name for c in candidates])
                result.add_error(
                    row_num,
                    f'団体が見つかりません。候補: {candidate_names}',
                    org_name
                )
            else:
                result.add_error(row_num, '団体が見つかりません', org_name)
            continue
        
        # ParkingRequestの取得または作成
        parking_request, created = ParkingRequest.objects.get_or_create(
            organization=organization,
            competition=competition,
            defaults={'requested_by': created_by_user}
        )
        
        # 割当情報の更新
        parking_request.status = 'assigned'
        parking_request.assigned_parking_lot = row.get('駐車場', '').strip()
        
        # 入出庫時間
        entry_time = parse_time(row.get('入庫時間', ''))
        exit_time = parse_time(row.get('出庫時間', ''))
        if entry_time:
            parking_request.entry_time = entry_time
        if exit_time:
            parking_request.exit_time = exit_time
        
        # 車両台数
        try:
            parking_request.assigned_large_bus = int(row.get('大型バス', 0) or 0)
        except ValueError:
            parking_request.assigned_large_bus = 0
        
        try:
            parking_request.assigned_medium_bus = int(row.get('中型バス', 0) or 0)
        except ValueError:
            parking_request.assigned_medium_bus = 0
        
        try:
            parking_request.assigned_car = int(row.get('乗用車', 0) or 0)
        except ValueError:
            parking_request.assigned_car = 0
        
        # 備考
        note = row.get('備考', '').strip()
        if note:
            parking_request.assignment_note = note
        
        parking_request.save()
        
        # 団体名が完全一致でなかった場合は警告
        if organization.name != org_name and organization.short_name != org_name:
            result.add_warning(
                row_num,
                f'"{org_name}" を "{organization.name}" にマッチしました',
                org_name
            )
        
        result.add_success(organization.name, parking_request.assigned_parking_lot)
    
    return result


def generate_sample_csv():
    """
    サンプルCSVを生成
    """
    header = ['団体名', '駐車場', '入庫時間', '出庫時間', '大型バス', '中型バス', '乗用車', '備考']
    sample_data = [
        ['日本体育大学', 'A駐車場', '7:00', '18:00', '1', '0', '3', ''],
        ['東洋大学', 'B駐車場', '7:30', '17:30', '0', '1', '2', ''],
        ['駒澤大学', 'A駐車場', '8:00', '18:00', '1', '0', '2', '大型バス優先'],
    ]
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(header)
    writer.writerows(sample_data)
    
    return output.getvalue()
