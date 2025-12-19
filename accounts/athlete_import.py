"""
選手一括登録機能
Excelファイルから選手を一括登録
"""
import io
import re
from datetime import date

import pandas as pd
from django.db import transaction

from .models import Athlete, User


class AthleteImportError(Exception):
    """選手インポートエラー"""
    def __init__(self, message, row=None, details=None):
        self.message = message
        self.row = row
        self.details = details or []
        super().__init__(self.message)


class AthleteExcelImporter:
    """
    Excel一括選手インポーター
    
    Excelフォーマット:
    | 姓 | 名 | 姓カナ | 名カナ | 性別 | 生年月日 | 学年 | 登録陸協 | JAAF ID | 国籍 |
    
    性別: M または F
    生年月日: YYYY-MM-DD または YYYY/MM/DD
    学年: 1, 2, 3, 4, M1, M2, D1, D2, D3（空欄可）
    登録陸協: 都道府県名（例: 東京、神奈川）
    JAAF ID: 陸連登録番号
    国籍: JPN, USA, KEN, ETH など（省略時は JPN）
    """
    
    REQUIRED_COLUMNS = ['姓', '名', '姓カナ', '名カナ', '性別', '生年月日', '登録陸協', 'JAAF ID']
    OPTIONAL_COLUMNS = ['学年', '国籍', '姓ローマ字', '名ローマ字']
    
    GENDER_MAP = {
        'M': 'M', '男': 'M', '男子': 'M',
        'F': 'F', '女': 'F', '女子': 'F',
    }
    
    GRADE_MAP = {
        '1': '1', '1年': '1',
        '2': '2', '2年': '2',
        '3': '3', '3年': '3',
        '4': '4', '4年': '4',
        'M1': 'M1', '修士1年': 'M1', '修士1': 'M1',
        'M2': 'M2', '修士2年': 'M2', '修士2': 'M2',
        'D1': 'D1', '博士1年': 'D1', '博士1': 'D1',
        'D2': 'D2', '博士2年': 'D2', '博士2': 'D2',
        'D3': 'D3', '博士3年': 'D3', '博士3': 'D3',
    }
    
    PREF_LIST = [
        '北海道', '青森', '岩手', '宮城', '秋田', '山形', '福島',
        '茨城', '栃木', '群馬', '埼玉', '千葉', '東京', '神奈川',
        '新潟', '富山', '石川', '福井', '山梨', '長野',
        '岐阜', '静岡', '愛知', '三重',
        '滋賀', '京都', '大阪', '兵庫', '奈良', '和歌山',
        '鳥取', '島根', '岡山', '広島', '山口',
        '徳島', '香川', '愛媛', '高知',
        '福岡', '佐賀', '長崎', '熊本', '大分', '宮崎', '鹿児島', '沖縄',
    ]
    
    NATIONALITY_MAP = {
        'JPN': 'JPN', '日本': 'JPN',
        'USA': 'USA', 'アメリカ': 'USA',
        'KEN': 'KEN', 'ケニア': 'KEN',
        'ETH': 'ETH', 'エチオピア': 'ETH',
        'GBR': 'GBR', 'イギリス': 'GBR',
        'CHN': 'CHN', '中国': 'CHN',
        'KOR': 'KOR', '韓国': 'KOR',
        'UGA': 'UGA', 'ウガンダ': 'UGA',
        'TAN': 'TAN', 'タンザニア': 'TAN',
        'MAR': 'MAR', 'モロッコ': 'MAR',
    }
    
    def __init__(self, user: User):
        """
        Args:
            user: 申込者（ログインユーザー）
        """
        self.user = user
        self.organization = user.organization
        self.errors: list[dict] = []
        self.warnings: list[dict] = []
        self.parsed_athletes: list[dict] = []
    
    def validate_kana(self, text: str, field_name: str) -> str:
        """カタカナ検証"""
        if not text:
            raise ValueError(f'{field_name}が空です')
        
        text = text.strip()
        # 全角カタカナとー（長音）のみ許可
        if not re.match(r'^[ァ-ヶー]+$', text):
            raise ValueError(f'{field_name}は全角カタカナで入力してください: {text}')
        
        return text
    
    def parse_gender(self, gender_str: str) -> str:
        """性別解析"""
        if pd.isna(gender_str) or str(gender_str).strip() == '':
            raise ValueError('性別が空です')
        
        gender_str = str(gender_str).strip()
        gender = self.GENDER_MAP.get(gender_str)
        
        if not gender:
            raise ValueError(f'性別が不正です: {gender_str}（M/F または 男/女 で入力）')
        
        return gender
    
    def parse_birth_date(self, date_str) -> date:
        """生年月日解析"""
        if pd.isna(date_str):
            raise ValueError('生年月日が空です')
        
        # pandas Timestamp の場合
        if isinstance(date_str, pd.Timestamp):
            return date_str.date()
        
        # datetime.date の場合
        if isinstance(date_str, date):
            return date_str
        
        date_str = str(date_str).strip()
        
        # YYYY-MM-DD または YYYY/MM/DD 形式をパース
        patterns = [
            r'^(\d{4})-(\d{1,2})-(\d{1,2})$',
            r'^(\d{4})/(\d{1,2})/(\d{1,2})$',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, date_str)
            if match:
                year, month, day = map(int, match.groups())
                try:
                    return date(year, month, day)
                except ValueError as e:
                    raise ValueError(f'無効な日付です: {date_str}') from e
        
        raise ValueError(f'生年月日の形式が不正です: {date_str}（YYYY-MM-DD形式で入力）')
    
    def parse_grade(self, grade_str) -> str:
        """学年解析"""
        if pd.isna(grade_str) or str(grade_str).strip() == '':
            return ''
        
        grade_str = str(grade_str).strip()
        grade = self.GRADE_MAP.get(grade_str)
        
        if grade is None:
            raise ValueError(f'学年が不正です: {grade_str}')
        
        return grade
    
    def parse_pref(self, pref_str: str) -> str:
        """登録陸協（都道府県）解析"""
        if pd.isna(pref_str) or str(pref_str).strip() == '':
            raise ValueError('登録陸協が空です')
        
        pref_str = str(pref_str).strip()
        
        # 「県」「府」「都」を除去して比較
        pref_clean = pref_str.replace('県', '').replace('府', '').replace('都', '')
        
        for pref in self.PREF_LIST:
            if pref == pref_str or pref == pref_clean:
                return pref
        
        raise ValueError(f'登録陸協が不正です: {pref_str}（都道府県名で入力）')
    
    def parse_nationality(self, nationality_str) -> str:
        """国籍解析"""
        if pd.isna(nationality_str) or str(nationality_str).strip() == '':
            return 'JPN'  # デフォルトは日本
        
        nationality_str = str(nationality_str).strip().upper()
        nationality = self.NATIONALITY_MAP.get(nationality_str)
        
        if not nationality:
            # マップにない場合は、3文字コードならそのまま使用
            if len(nationality_str) == 3 and nationality_str.isalpha():
                return nationality_str
            raise ValueError(f'国籍が不正です: {nationality_str}')
        
        return nationality
    
    def parse_row(self, row_data: dict, row_num: int) -> dict:
        """
        1行のデータを解析
        
        Args:
            row_data: 行データ（辞書）
            row_num: 行番号（エラー表示用、2始まり）
        
        Returns:
            解析済みの選手データ辞書
        
        Raises:
            AthleteImportError: 解析エラー
        """
        errors = []
        athlete_data = {'row_num': row_num}
        
        # 姓・名
        try:
            athlete_data['last_name'] = str(row_data.get('姓', '')).strip()
            if not athlete_data['last_name']:
                raise ValueError('姓が空です')
        except ValueError as e:
            errors.append(str(e))
        
        try:
            athlete_data['first_name'] = str(row_data.get('名', '')).strip()
            if not athlete_data['first_name']:
                raise ValueError('名が空です')
        except ValueError as e:
            errors.append(str(e))
        
        # カナ
        try:
            athlete_data['last_name_kana'] = self.validate_kana(
                str(row_data.get('姓カナ', '')), '姓カナ'
            )
        except ValueError as e:
            errors.append(str(e))
        
        try:
            athlete_data['first_name_kana'] = self.validate_kana(
                str(row_data.get('名カナ', '')), '名カナ'
            )
        except ValueError as e:
            errors.append(str(e))
        
        # 性別
        try:
            athlete_data['gender'] = self.parse_gender(row_data.get('性別'))
        except ValueError as e:
            errors.append(str(e))
        
        # 生年月日
        try:
            athlete_data['birth_date'] = self.parse_birth_date(row_data.get('生年月日'))
        except ValueError as e:
            errors.append(str(e))
        
        # 学年（オプション）
        try:
            athlete_data['grade'] = self.parse_grade(row_data.get('学年'))
        except ValueError as e:
            errors.append(str(e))
        
        # 登録陸協
        try:
            athlete_data['registered_pref'] = self.parse_pref(row_data.get('登録陸協'))
        except ValueError as e:
            errors.append(str(e))
        
        # JAAF ID
        jaaf_id = row_data.get('JAAF ID')
        if pd.isna(jaaf_id) or str(jaaf_id).strip() == '':
            errors.append('JAAF IDが空です')
        else:
            athlete_data['jaaf_id'] = str(jaaf_id).strip()
        
        # 国籍（オプション）
        try:
            athlete_data['nationality'] = self.parse_nationality(row_data.get('国籍'))
        except ValueError as e:
            errors.append(str(e))
        
        # ローマ字（オプション）
        athlete_data['last_name_en'] = str(row_data.get('姓ローマ字', '')).strip() if not pd.isna(row_data.get('姓ローマ字')) else ''
        athlete_data['first_name_en'] = str(row_data.get('名ローマ字', '')).strip() if not pd.isna(row_data.get('名ローマ字')) else ''
        
        if errors:
            athlete_data['errors'] = errors
            athlete_data['valid'] = False
        else:
            athlete_data['errors'] = []
            athlete_data['valid'] = True
        
        return athlete_data
    
    def check_duplicates(self, parsed_athletes: list[dict]) -> list[dict]:
        """
        重複チェック
        - JAAF IDの重複（ファイル内、既存DB）
        - 同姓同名＋生年月日の重複
        """
        for athlete in parsed_athletes:
            if not athlete.get('valid'):
                continue
            
            jaaf_id = athlete.get('jaaf_id')
            
            # ファイル内でのJAAF ID重複
            same_jaaf_in_file = [
                a for a in parsed_athletes 
                if a.get('jaaf_id') == jaaf_id 
                and a['row_num'] != athlete['row_num']
                and a.get('valid')
            ]
            if same_jaaf_in_file:
                if 'warnings' not in athlete:
                    athlete['warnings'] = []
                athlete['warnings'].append(f'JAAF ID {jaaf_id} が行{same_jaaf_in_file[0]["row_num"]}と重複しています')
            
            # DB内でのJAAF ID重複
            existing_by_jaaf = Athlete.objects.filter(jaaf_id=jaaf_id, is_active=True)
            if self.organization:
                existing_same_org = existing_by_jaaf.filter(organization=self.organization).first()
                if existing_same_org:
                    if 'warnings' not in athlete:
                        athlete['warnings'] = []
                    athlete['warnings'].append(f'JAAF ID {jaaf_id} は既に登録済みです（{existing_same_org.full_name}）')
                    athlete['existing_id'] = existing_same_org.pk
            else:
                existing_same_user = existing_by_jaaf.filter(user=self.user).first()
                if existing_same_user:
                    if 'warnings' not in athlete:
                        athlete['warnings'] = []
                    athlete['warnings'].append(f'JAAF ID {jaaf_id} は既に登録済みです（{existing_same_user.full_name}）')
                    athlete['existing_id'] = existing_same_user.pk
        
        return parsed_athletes
    
    def parse_excel(self, file_content: bytes) -> tuple[list[dict], list[str]]:
        """
        Excelファイルを解析
        
        Args:
            file_content: Excelファイルのバイトデータ
        
        Returns:
            (解析済み選手リスト, グローバルエラーリスト)
        """
        global_errors = []
        
        try:
            df = pd.read_excel(io.BytesIO(file_content))
        except Exception as e:
            global_errors.append(f'Excelファイルの読み込みに失敗しました: {str(e)}')
            return [], global_errors
        
        if len(df) == 0:
            global_errors.append('データがありません')
            return [], global_errors
        
        # 必須列のチェック
        missing_columns = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            global_errors.append(f'必須列がありません: {", ".join(missing_columns)}')
            return [], global_errors
        
        # 各行を解析
        parsed_athletes = []
        for idx, row in df.iterrows():
            row_num = idx + 2  # Excelは1始まり、ヘッダーで+1
            row_data = row.to_dict()
            athlete_data = self.parse_row(row_data, row_num)
            parsed_athletes.append(athlete_data)
        
        # 重複チェック
        parsed_athletes = self.check_duplicates(parsed_athletes)
        
        self.parsed_athletes = parsed_athletes
        return parsed_athletes, global_errors
    
    @transaction.atomic
    def import_athletes(self, parsed_athletes: list[dict], skip_existing: bool = True) -> tuple[list[Athlete], list[dict]]:
        """
        選手を一括登録
        
        Args:
            parsed_athletes: 解析済み選手リスト
            skip_existing: 既存の選手をスキップするか（Trueならスキップ、Falseなら更新）
        
        Returns:
            (登録した選手リスト, スキップした選手リスト)
        """
        imported = []
        skipped = []
        
        for athlete_data in parsed_athletes:
            if not athlete_data.get('valid'):
                skipped.append(athlete_data)
                continue
            
            # 既存チェック
            if athlete_data.get('existing_id') and skip_existing:
                skipped.append(athlete_data)
                continue
            
            # 選手オブジェクト作成
            athlete = Athlete(
                last_name=athlete_data['last_name'],
                first_name=athlete_data['first_name'],
                last_name_kana=athlete_data['last_name_kana'],
                first_name_kana=athlete_data['first_name_kana'],
                last_name_en=athlete_data.get('last_name_en', ''),
                first_name_en=athlete_data.get('first_name_en', ''),
                gender=athlete_data['gender'],
                birth_date=athlete_data['birth_date'],
                grade=athlete_data.get('grade', ''),
                registered_pref=athlete_data['registered_pref'],
                jaaf_id=athlete_data['jaaf_id'],
                nationality=athlete_data.get('nationality', 'JPN'),
            )
            
            if self.organization:
                athlete.organization = self.organization
            else:
                athlete.user = self.user
            
            athlete.save()
            imported.append(athlete)
        
        return imported, skipped


def generate_athlete_template() -> bytes:
    """
    選手登録用Excelテンプレートを生成
    
    Returns:
        Excelファイルのバイトデータ
    """
    columns = [
        '姓', '名', '姓カナ', '名カナ', '性別', '生年月日', 
        '学年', '登録陸協', 'JAAF ID', '国籍', '姓ローマ字', '名ローマ字'
    ]
    
    # サンプルデータ
    sample_data = [
        {
            '姓': '山田',
            '名': '太郎',
            '姓カナ': 'ヤマダ',
            '名カナ': 'タロウ',
            '性別': 'M',
            '生年月日': '2000-04-01',
            '学年': '3',
            '登録陸協': '東京',
            'JAAF ID': '12345678',
            '国籍': 'JPN',
            '姓ローマ字': 'YAMADA',
            '名ローマ字': 'Taro',
        },
        {
            '姓': '鈴木',
            '名': '花子',
            '姓カナ': 'スズキ',
            '名カナ': 'ハナコ',
            '性別': 'F',
            '生年月日': '2001-08-15',
            '学年': '2',
            '登録陸協': '神奈川',
            'JAAF ID': '87654321',
            '国籍': 'JPN',
            '姓ローマ字': 'SUZUKI',
            '名ローマ字': 'Hanako',
        },
    ]
    
    df = pd.DataFrame(sample_data, columns=columns)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='選手一覧')
        
        # 列幅調整
        worksheet = writer.sheets['選手一覧']
        column_widths = {
            'A': 10,  # 姓
            'B': 10,  # 名
            'C': 12,  # 姓カナ
            'D': 12,  # 名カナ
            'E': 8,   # 性別
            'F': 14,  # 生年月日
            'G': 8,   # 学年
            'H': 12,  # 登録陸協
            'I': 12,  # JAAF ID
            'J': 8,   # 国籍
            'K': 12,  # 姓ローマ字
            'L': 12,  # 名ローマ字
        }
        for col, width in column_widths.items():
            worksheet.column_dimensions[col].width = width
    
    return output.getvalue()


def generate_jaaf_csv_template() -> bytes:
    """
    JAAF形式（NANS21V互換）のCSVテンプレートを生成
    
    カラム構成はNANS21V Web登録サービスのフォーマットに準拠:
    年度, JAAF ID, 氏名（姓）, 氏名（名）, 登録番号（ナンバー）, フリガナ（姓）, フリガナ（名）,
    英字（姓）, 英字（名）, 国籍, 性別, 登録都道府県番号, 生年月日, 学年, 団体区分
    
    Returns:
        CSVファイルのバイトデータ
    """
    import csv
    from datetime import datetime
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # ヘッダー（NANS21V形式）
    headers = [
        '年度',
        'JAAF ID',
        '氏名（姓）',
        '氏名（名）',
        '登録番号（ナンバー）',
        'ﾌﾘｶﾞﾅ（姓）',
        'ﾌﾘｶﾞﾅ（名）',
        '英字（姓）',
        '英字（名）',
        '国籍',
        '性別',
        '登録都道府県番号',
        '登録都道府県名',  # 未使用だが互換性のため
        '団体UID',  # 未使用
        '団体ID',  # 未使用
        '団体名',  # 未使用
        '団体名略称1',  # 未使用
        '団体名略称2',  # 未使用
        '生年月日',
        '旧団体コード',  # 未使用
        '備考',  # 未使用
        '学年',
        '団体区分',
    ]
    writer.writerow(headers)
    
    # サンプルデータ（2行）
    current_year = datetime.now().year
    sample_data = [
        [
            current_year,  # 年度
            '12345678',    # JAAF ID
            '山田',        # 氏名（姓）
            '太郎',        # 氏名（名）
            'A12345',      # 登録番号
            'ヤマダ',      # フリガナ（姓）
            'タロウ',      # フリガナ（名）
            'YAMADA',      # 英字（姓）
            'Taro',        # 英字（名）
            'JPN',         # 国籍
            '男子',        # 性別
            '13',          # 登録都道府県番号（東京）
            '',            # 登録都道府県名
            '',            # 団体UID
            '',            # 団体ID
            '',            # 団体名
            '',            # 団体名略称1
            '',            # 団体名略称2
            '2000/04/01',  # 生年月日
            '',            # 旧団体コード
            '',            # 備考
            '3',           # 学年
            '大学',        # 団体区分
        ],
        [
            current_year,
            '87654321',
            '鈴木',
            '花子',
            'B67890',
            'スズキ',
            'ハナコ',
            'SUZUKI',
            'Hanako',
            'JPN',
            '女子',
            '14',  # 神奈川
            '',
            '',
            '',
            '',
            '',
            '',
            '2001/08/15',
            '',
            '',
            '2',
            '大学',
        ],
    ]
    
    for row in sample_data:
        writer.writerow(row)
    
    # Shift_JISでエンコード（Excel互換）
    csv_content = output.getvalue()
    return csv_content.encode('utf-8-sig')  # BOM付きUTF-8でExcel互換
