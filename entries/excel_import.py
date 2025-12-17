"""
Excel一括エントリー機能
Pandasを使用してExcelファイルから選手エントリーを一括登録
"""
import io
from decimal import Decimal

import pandas as pd
from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import Athlete
from competitions.models import Race
from entries.models import Entry


class ExcelImportError(Exception):
    """Excelインポートエラー"""
    def __init__(self, message, row=None, details=None):
        self.message = message
        self.row = row
        self.details = details or []
        super().__init__(self.message)


class ExcelEntryImporter:
    """
    Excel一括エントリーインポーター
    
    Excelフォーマット:
    | 選手ID (JAAF ID) | 姓 | 名 | 種目コード | 申告タイム |
    
    種目コード例: M5000（男子5000m）, F3000（女子3000m）
    申告タイム形式: MM:SS.ss (例: 14:30.00)
    """
    
    REQUIRED_COLUMNS = ['選手ID', '姓', '名', '種目コード', '申告タイム']
    OPTIONAL_COLUMNS = ['備考']
    
    def __init__(self, competition, user):
        """
        Args:
            competition: 大会オブジェクト
            user: 申込者（ログインユーザー）
        """
        self.competition = competition
        self.user = user
        self.organization = user.organization
        self.errors = []
        self.warnings = []
        self.imported_entries = []
    
    def parse_time(self, time_str):
        """
        タイム文字列を秒に変換
        
        Args:
            time_str: "MM:SS.ss" または "M:SS.ss" 形式
        
        Returns:
            Decimal: 秒単位のタイム
        """
        if pd.isna(time_str) or time_str == '':
            raise ValueError('申告タイムが空です')
        
        time_str = str(time_str).strip()
        
        try:
            parts = time_str.split(':')
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = float(parts[1])
                return Decimal(str(minutes * 60 + seconds))
            raise ValueError('タイム形式が不正です')
        except (ValueError, IndexError) as e:
            raise ValueError(f'タイム形式が正しくありません: {time_str}（例: 14:30.00）') from e
    
    def parse_race_code(self, race_code):
        """
        種目コードから種目オブジェクトを取得
        
        Args:
            race_code: 種目コード（例: M5000, F3000, NCG_M5000）
        
        Returns:
            Race: 種目オブジェクト
        """
        if pd.isna(race_code) or race_code == '':
            raise ValueError('種目コードが空です')
        
        race_code = str(race_code).strip().upper()
        
        # NCGフラグ解析
        is_ncg = race_code.startswith('NCG_')
        if is_ncg:
            race_code = race_code[4:]  # NCG_を除去
        
        # 性別と距離を解析
        if len(race_code) < 2:
            raise ValueError(f'種目コード形式が不正です: {race_code}')
        
        gender = race_code[0]
        if gender not in ('M', 'F', 'X'):
            raise ValueError(f'性別コードが不正です: {gender}（M/F/Xのいずれか）')
        
        try:
            distance = int(race_code[1:])
        except ValueError as e:
            raise ValueError(f'距離が不正です: {race_code[1:]}') from e
        
        # 種目を検索
        races = Race.objects.filter(
            competition=self.competition,
            gender=gender,
            distance=distance,
            is_ncg=is_ncg,
            is_active=True
        )
        
        if not races.exists():
            ncg_label = 'NCG ' if is_ncg else ''
            raise ValueError(f'{ncg_label}{gender}{distance}の種目が見つかりません')
        
        return races.first()
    
    def find_or_create_athlete(self, row_data, row_num):
        """
        選手を検索または作成
        
        Args:
            row_data: 行データ（辞書）
            row_num: 行番号（エラー表示用）
        
        Returns:
            Athlete: 選手オブジェクト
        """
        jaaf_id = str(row_data.get('選手ID', '')).strip()
        last_name = str(row_data.get('姓', '')).strip()
        first_name = str(row_data.get('名', '')).strip()
        
        if not last_name or not first_name:
            raise ValidationError(f'行{row_num}: 姓または名が空です')
        
        # JAAF IDで検索
        if jaaf_id:
            athlete = Athlete.objects.filter(jaaf_id=jaaf_id).first()
            if athlete:
                # 所属確認
                if self.organization and athlete.organization != self.organization:
                    self.warnings.append(
                        f'行{row_num}: 選手「{athlete.full_name}」は別団体所属です'
                    )
                return athlete
        
        # 名前と所属で検索
        athletes = Athlete.objects.filter(
            last_name=last_name,
            first_name=first_name
        )
        
        if self.organization:
            athletes = athletes.filter(organization=self.organization)
        
        if athletes.exists():
            return athletes.first()
        
        # 見つからない場合はエラー（選手マスタに事前登録が必要）
        raise ValidationError(
            f'行{row_num}: 選手「{last_name} {first_name}」が見つかりません。'
            f'先に選手マスタに登録してください。'
        )
    
    def validate_entry(self, athlete, race, declared_time, row_num):
        """
        エントリーのバリデーション
        
        Args:
            athlete: 選手オブジェクト
            race: 種目オブジェクト
            declared_time: 申告タイム（秒）
            row_num: 行番号
        
        Returns:
            bool: バリデーション結果
        """
        errors = []
        
        # 性別チェック
        if race.gender != 'X' and athlete.gender != race.gender:
            errors.append(f'選手の性別（{athlete.get_gender_display()}）と種目の性別区分が一致しません')
        
        # 参加標準記録チェック
        if race.standard_time and declared_time:
            if declared_time > race.standard_time:
                from nitsys.constants import format_time
                standard_formatted = format_time(float(race.standard_time))
                declared_formatted = format_time(float(declared_time))
                errors.append(
                    f'申告タイム({declared_formatted})が参加標準記録({standard_formatted})を超えています'
                )
        
        # 重複エントリーチェック
        existing = Entry.objects.filter(
            athlete=athlete,
            race=race
        ).exclude(status='cancelled')
        
        if existing.exists():
            errors.append('既にこの種目にエントリー済みです')
        
        # 定員チェック
        if race.is_full:
            errors.append(f'種目「{race.name}」は定員に達しています')
        
        if errors:
            raise ValidationError(f'行{row_num}: ' + '、'.join(errors))
        
        return True
    
    def import_from_file(self, file_obj):
        """
        Excelファイルからエントリーをインポート
        
        Args:
            file_obj: アップロードされたファイルオブジェクト
        
        Returns:
            dict: インポート結果
        """
        self.errors = []
        self.warnings = []
        self.imported_entries = []
        
        try:
            # Excelファイルを読み込み
            df = pd.read_excel(file_obj, engine='openpyxl')
        except Exception as e:
            raise ExcelImportError(f'Excelファイルの読み込みに失敗しました: {e!s}') from e
        
        # 必須カラムチェック
        missing_columns = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            raise ExcelImportError(
                f'必須カラムが見つかりません: {", ".join(missing_columns)}'
            )
        
        # 空行を除去
        df = df.dropna(how='all')
        
        if df.empty:
            raise ExcelImportError('インポートするデータがありません')
        
        # 各行を処理
        success_count = 0
        
        with transaction.atomic():
            for idx, row in df.iterrows():
                row_num = idx + 2  # Excelの行番号（ヘッダー行を考慮）
                
                try:
                    # 種目を取得
                    race = self.parse_race_code(row.get('種目コード'))
                    
                    # タイムを変換
                    declared_time = self.parse_time(row.get('申告タイム'))
                    
                    # 選手を取得
                    athlete = self.find_or_create_athlete(row.to_dict(), row_num)
                    
                    # バリデーション
                    self.validate_entry(athlete, race, declared_time, row_num)
                    
                    # エントリー作成
                    entry = Entry.objects.create(
                        athlete=athlete,
                        race=race,
                        registered_by=self.user,
                        declared_time=declared_time,
                        note=str(row.get('備考', '')) if not pd.isna(row.get('備考')) else '',
                        status='pending'
                    )
                    
                    self.imported_entries.append(entry)
                    success_count += 1
                    
                except ValidationError as e:
                    self.errors.append(str(e))
                except ValueError as e:
                    self.errors.append(f'行{row_num}: {str(e)}')
                except Exception as e:
                    self.errors.append(f'行{row_num}: 予期しないエラー - {str(e)}')
        
        return {
            'success': success_count > 0,
            'success_count': success_count,
            'total_count': len(df),
            'errors': self.errors,
            'warnings': self.warnings,
            'entries': self.imported_entries,
        }
    
    def preview_from_file(self, file_obj):
        """
        Excelファイルの内容をプレビュー（実際には保存しない）
        
        Args:
            file_obj: アップロードされたファイルオブジェクト
        
        Returns:
            dict: プレビュー結果
        """
        self.errors = []
        self.warnings = []
        preview_data = []
        
        try:
            df = pd.read_excel(file_obj, engine='openpyxl')
        except Exception as e:
            raise ExcelImportError(f'Excelファイルの読み込みに失敗しました: {e!s}') from e
        
        missing_columns = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            raise ExcelImportError(
                f'必須カラムが見つかりません: {", ".join(missing_columns)}'
            )
        
        df = df.dropna(how='all')
        
        for idx, row in df.iterrows():
            row_num = idx + 2
            preview_row = {
                'row_num': row_num,
                'jaaf_id': row.get('選手ID', ''),
                'last_name': row.get('姓', ''),
                'first_name': row.get('名', ''),
                'race_code': row.get('種目コード', ''),
                'declared_time': row.get('申告タイム', ''),
                'note': row.get('備考', ''),
                'valid': True,
                'errors': [],
            }
            
            try:
                race = self.parse_race_code(row.get('種目コード'))
                preview_row['race_name'] = race.name
                
                declared_time = self.parse_time(row.get('申告タイム'))
                preview_row['declared_time_seconds'] = float(declared_time)
                
                athlete = self.find_or_create_athlete(row.to_dict(), row_num)
                preview_row['athlete_name'] = athlete.full_name
                
                self.validate_entry(athlete, race, declared_time, row_num)
                
            except (ValidationError, ValueError) as e:
                preview_row['valid'] = False
                preview_row['errors'].append(str(e))
                self.errors.append(str(e))
            except Exception as e:
                preview_row['valid'] = False
                preview_row['errors'].append(f'エラー: {str(e)}')
                self.errors.append(f'行{row_num}: {str(e)}')
            
            preview_data.append(preview_row)
        
        valid_count = sum(1 for row in preview_data if row['valid'])
        
        return {
            'total_count': len(preview_data),
            'valid_count': valid_count,
            'invalid_count': len(preview_data) - valid_count,
            'rows': preview_data,
            'errors': self.errors,
            'warnings': self.warnings,
        }


def generate_entry_template():
    """
    エントリー用Excelテンプレートを生成
    
    Returns:
        BytesIO: Excelファイルのバイナリデータ
    """
    # テンプレートデータ
    data = {
        '選手ID': ['12345678', '87654321', ''],
        '姓': ['山田', '鈴木', '田中'],
        '名': ['太郎', '花子', '一郎'],
        '種目コード': ['M5000', 'F3000', 'NCG_M5000'],
        '申告タイム': ['14:30.00', '9:45.50', '13:50.00'],
        '備考': ['', '自己ベスト', ''],
    }
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='エントリーデータ')
        
        # 説明シートを追加
        instructions = {
            '項目': ['選手ID', '姓', '名', '種目コード', '申告タイム', '備考'],
            '説明': [
                'JAAF陸連登録番号（任意）。既存選手の照合に使用',
                '選手の姓（必須）',
                '選手の名（必須）',
                '種目コード（必須）。例: M5000=男子5000m, F3000=女子3000m, NCG_M5000=NCG男子5000m',
                '申告タイム（必須）。形式: MM:SS.ss（例: 14:30.00）',
                '備考（任意）',
            ],
            '必須': ['○', '○', '○', '○', '○', ''],
        }
        pd.DataFrame(instructions).to_excel(
            writer, index=False, sheet_name='入力説明'
        )
    
    output.seek(0)
    return output
