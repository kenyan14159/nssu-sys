"""
帳票生成ユーティリティ
"""
import csv
import io
import random
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from heats.models import HeatAssignment


class CSVGenerator:
    """CSV出力生成"""
    
    @classmethod
    def generate_startlist_csv(cls, race):
        """
        計測システム連携用スタートリストCSV
        FinishLynx/NISHI等に取り込み可能な形式
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # ヘッダー
        writer.writerow([
            'Heat', 'Lane', 'Bib', 'LastName', 'FirstName',
            'Team', 'SeedTime', 'JAAF_ID'
        ])
        
        # データ
        assignments = HeatAssignment.objects.filter(
            heat__race=race,
            status='assigned'
        ).select_related(
            'heat', 'entry', 'entry__athlete', 'entry__athlete__organization'
        ).order_by('heat__heat_number', 'bib_number')
        
        for assignment in assignments:
            athlete = assignment.entry.athlete
            org_name = athlete.organization.short_name if athlete.organization else ''
            
            writer.writerow([
                assignment.heat.heat_number,
                assignment.bib_number,
                assignment.bib_number,
                athlete.last_name,
                athlete.first_name,
                org_name,
                assignment.entry.declared_time_display,
                athlete.jaaf_id or ''
            ])
        
        output.seek(0)
        return output.getvalue()
    
    @classmethod
    def generate_all_data_csv(cls, competition):
        """大会全データCSV出力"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # ヘッダー
        writer.writerow([
            'Race', 'Heat', 'Lane', 'LastName', 'FirstName',
            'LastNameKana', 'FirstNameKana', 'Gender', 'BirthDate',
            'Team', 'TeamKana', 'SeedTime', 'JAAF_ID', 'Status'
        ])
        
        # 全種目のデータ
        for race in competition.races.filter(is_active=True).order_by('display_order'):
            assignments = HeatAssignment.objects.filter(
                heat__race=race
            ).select_related(
                'heat', 'entry', 'entry__athlete', 'entry__athlete__organization'
            ).order_by('heat__heat_number', 'bib_number')
            
            for assignment in assignments:
                athlete = assignment.entry.athlete
                org = athlete.organization
                
                writer.writerow([
                    race.name,
                    assignment.heat.heat_number,
                    assignment.bib_number,
                    athlete.last_name,
                    athlete.first_name,
                    athlete.last_name_kana,
                    athlete.first_name_kana,
                    athlete.get_gender_display(),
                    athlete.birth_date.strftime('%Y-%m-%d'),
                    org.name if org else '',
                    org.name_kana if org else '',
                    assignment.entry.declared_time_display,
                    athlete.jaaf_id or '',
                    assignment.get_status_display()
                ])
        
        output.seek(0)
        return output.getvalue()


class PDFGenerator:
    """PDF出力生成"""
    
    _font_registered = False
    _font_name = 'Helvetica'
    
    @classmethod
    def _setup_fonts(cls):
        """日本語フォント設定（システムフォント使用）"""
        if cls._font_registered:
            return cls._font_name
        
        font_paths = [
            # macOS
            '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
            '/System/Library/Fonts/Hiragino Sans GB.ttc',
            '/Library/Fonts/Arial Unicode.ttf',
            # Linux (Ubuntu/Debian)
            '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/truetype/takao-gothic/TakaoPGothic.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            # IPAフォント（手動インストール時）
            '/usr/share/fonts/ipa-gothic/ipag.ttf',
            '/usr/share/fonts/truetype/ipafont/ipag.ttf',
        ]
        
        for font_path in font_paths:
            try:
                pdfmetrics.registerFont(TTFont('Japanese', font_path))
                cls._font_registered = True
                cls._font_name = 'Japanese'
                print(f"[PDF] 日本語フォント登録成功: {font_path}")
                return cls._font_name
            except Exception:
                continue
        
        # フォールバック（日本語は表示できない可能性あり）
        print("[PDF] 警告: 日本語フォントが見つかりません。代替フォントを使用します。")
        cls._font_registered = True
        return cls._font_name
    
    @classmethod
    def generate_rollcall_pdf(cls, heat):
        """
        点呼用リストPDF
        受付で手動チェックするためのリスト
        """
        buffer = io.BytesIO()
        font_name = cls._setup_fonts()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=15*mm
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # タイトル
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=16,
            spaceAfter=10*mm
        )
        elements.append(Paragraph(
            f"{heat.race.name} {heat.heat_number}組 点呼リスト",
            title_style
        ))
        
        # 日時
        elements.append(Paragraph(
            f"出力日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}",
            styles['Normal']
        ))
        elements.append(Spacer(1, 5*mm))
        
        # テーブルデータ
        data = [['No.', '腰番号', '氏名', 'フリガナ', '所属', '点呼']]
        
        assignments = heat.assignments.select_related(
            'entry', 'entry__athlete', 'entry__athlete__organization'
        ).order_by('bib_number')
        
        for i, assignment in enumerate(assignments, 1):
            athlete = assignment.entry.athlete
            org_name = athlete.organization.short_name if athlete.organization else ''
            
            data.append([
                str(i),
                str(assignment.bib_number),
                athlete.full_name,
                athlete.full_name_kana,
                org_name,
                '□'  # チェックボックス
            ])
        
        # テーブル作成
        table = Table(data, colWidths=[15*mm, 20*mm, 50*mm, 50*mm, 35*mm, 15*mm])
        table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), font_name, 10),
            ('FONT', (0, 0), (-1, 0), font_name, 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (3, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWHEIGHTS', (0, 0), (-1, -1), 8*mm),
        ]))
        
        elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
    
    @classmethod
    def generate_program_pdf(cls, race):
        """
        プログラム原稿PDF
        組ごとの選手一覧
        """
        buffer = io.BytesIO()
        font_name = cls._setup_fonts()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=15*mm
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=18,
            spaceAfter=5*mm
        )
        
        heat_title_style = ParagraphStyle(
            'HeatTitle',
            parent=styles['Heading2'],
            fontName=font_name,
            fontSize=14,
            spaceBefore=10*mm,
            spaceAfter=5*mm
        )
        
        # タイトル
        elements.append(Paragraph(f"{race.name} プログラム", title_style))
        elements.append(Paragraph(
            f"{race.competition.name} ({race.competition.event_date.strftime('%Y年%m月%d日')})",
            styles['Normal']
        ))
        
        # 各組
        for heat in race.heats.order_by('heat_number'):
            elements.append(Paragraph(f"{heat.heat_number}組", heat_title_style))
            
            data = [['腰', '氏名', '所属', '申告タイム']]
            
            for assignment in heat.assignments.select_related(
                'entry', 'entry__athlete', 'entry__athlete__organization'
            ).order_by('bib_number'):
                athlete = assignment.entry.athlete
                org_name = athlete.organization.short_name if athlete.organization else ''
                
                data.append([
                    str(assignment.bib_number),
                    athlete.full_name,
                    org_name,
                    assignment.entry.declared_time_display
                ])
            
            table = Table(data, colWidths=[15*mm, 60*mm, 50*mm, 30*mm])
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), font_name, 10),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWHEIGHTS', (0, 0), (-1, -1), 7*mm),
            ]))
            
            elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
    
    @classmethod
    def generate_all_data_pdf(cls, competition):
        """
        緊急時対応用：全データPDF
        ネットワーク障害時に備えた全データ出力
        """
        buffer = io.BytesIO()
        font_name = cls._setup_fonts()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=10*mm,
            leftMargin=10*mm,
            topMargin=15*mm,
            bottomMargin=15*mm
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=20,
            spaceAfter=10*mm
        )
        
        race_title_style = ParagraphStyle(
            'RaceTitle',
            parent=styles['Heading2'],
            fontName=font_name,
            fontSize=16,
            spaceBefore=15*mm,
            spaceAfter=5*mm
        )
        
        # タイトル
        elements.append(Paragraph(
            f"{competition.name}",
            title_style
        ))
        elements.append(Paragraph(
            f"開催日: {competition.event_date.strftime('%Y年%m月%d日')}",
            styles['Normal']
        ))
        elements.append(Paragraph(
            f"出力日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
            styles['Normal']
        ))
        elements.append(Paragraph(
            "※緊急時バックアップ用データ",
            styles['Normal']
        ))
        
        # 各種目
        for race in competition.races.filter(is_active=True).order_by('display_order'):
            elements.append(Paragraph(race.name, race_title_style))
            
            for heat in race.heats.order_by('heat_number'):
                elements.append(Paragraph(
                    f"{heat.heat_number}組",
                    styles['Heading3']
                ))
                
                data = [['腰', '氏名', '所属', '申告', '状態']]
                
                for assignment in heat.assignments.select_related(
                    'entry', 'entry__athlete', 'entry__athlete__organization'
                ).order_by('bib_number'):
                    athlete = assignment.entry.athlete
                    org_name = athlete.organization.short_name if athlete.organization else ''
                    
                    data.append([
                        str(assignment.bib_number),
                        athlete.full_name,
                        org_name,
                        assignment.entry.declared_time_display,
                        assignment.get_status_display()
                    ])
                
                if len(data) > 1:
                    table = Table(data, colWidths=[12*mm, 55*mm, 45*mm, 25*mm, 25*mm])
                    table.setStyle(TableStyle([
                        ('FONT', (0, 0), (-1, -1), font_name, 9),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('ROWHEIGHTS', (0, 0), (-1, -1), 6*mm),
                    ]))
                    elements.append(table)
                    elements.append(Spacer(1, 3*mm))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer


class ParkingPermitPDFGenerator:
    """駐車許可証PDF生成"""
    
    @classmethod
    def generate_permit_pdf(cls, parking_request):
        """
        駐車許可証PDF生成
        ダッシュボードに掲示するための許可証
        """
        buffer = io.BytesIO()
        font_name = PDFGenerator._setup_fonts()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # カスタムスタイル
        title_style = ParagraphStyle(
            'PermitTitle',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=28,
            alignment=1,  # CENTER
            spaceAfter=15*mm,
            textColor=colors.darkblue
        )
        
        subtitle_style = ParagraphStyle(
            'PermitSubtitle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=14,
            alignment=1,
            spaceAfter=10*mm
        )
        
        org_style = ParagraphStyle(
            'OrgName',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=32,
            alignment=1,
            spaceAfter=15*mm,
            textColor=colors.black
        )
        
        # info_style は現在未使用だが、将来の拡張用に残す
        _ = ParagraphStyle(
            'InfoStyle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=14,
            spaceAfter=5*mm
        )
        
        large_info_style = ParagraphStyle(
            'LargeInfoStyle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=20,
            alignment=1,
            spaceAfter=10*mm
        )
        
        # ヘッダー枠
        elements.append(Spacer(1, 10*mm))
        
        # タイトル
        competition = parking_request.competition
        elements.append(Paragraph(
            f"第{competition.name.split('第')[-1].split('回')[0]}回" if '第' in competition.name else '',
            subtitle_style
        ))
        elements.append(Paragraph("駐 車 許 可 証", title_style))
        
        # 大会名
        elements.append(Paragraph(competition.name, subtitle_style))
        elements.append(Spacer(1, 10*mm))
        
        # 団体名（大きく表示）
        elements.append(Paragraph(
            parking_request.organization.name,
            org_style
        ))
        
        elements.append(Spacer(1, 15*mm))
        
        # 駐車場情報テーブル
        permit_info = parking_request.get_permit_info()
        
        # 駐車場名を大きく表示
        elements.append(Paragraph(
            f"駐車場: {permit_info['parking_lot']}",
            large_info_style
        ))
        
        elements.append(Spacer(1, 10*mm))
        
        # 時間・台数情報テーブル
        table_data = [
            ['項目', '内容'],
        ]
        
        # 入庫時間
        entry_time = permit_info['entry_time']
        if entry_time:
            table_data.append(['入庫時間', entry_time.strftime('%H:%M') + ' 以降'])
        
        # 出庫時間
        exit_time = permit_info['exit_time']
        if exit_time:
            table_data.append(['出庫時間', exit_time.strftime('%H:%M') + ' まで'])
        
        # 台数
        vehicles = []
        if permit_info['large_bus'] > 0:
            vehicles.append(f"大型バス {permit_info['large_bus']}台")
        if permit_info['medium_bus'] > 0:
            vehicles.append(f"中型バス {permit_info['medium_bus']}台")
        if permit_info['car'] > 0:
            vehicles.append(f"乗用車 {permit_info['car']}台")
        
        if vehicles:
            table_data.append(['許可台数', ', '.join(vehicles)])
        
        # 開催日
        event_date = permit_info['event_date']
        if event_date:
            table_data.append(['開催日', event_date.strftime('%Y年%m月%d日')])
        
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[50*mm, 100*mm])
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), font_name, 14),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWHEIGHTS', (0, 0), (-1, -1), 12*mm),
            ]))
            elements.append(table)
        
        elements.append(Spacer(1, 20*mm))
        
        # 注意事項
        note_style = ParagraphStyle(
            'NoteStyle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=10,
            spaceAfter=3*mm
        )
        
        elements.append(Paragraph("【注意事項】", note_style))
        notes = [
            "・本許可証はダッシュボードの見える位置に掲示してください。",
            "・指定された駐車場以外への駐車はご遠慮ください。",
            "・出庫時間を過ぎる場合は、事前に運営本部までご連絡ください。",
            "・場内は徐行運転をお願いいたします。",
        ]
        for note in notes:
            elements.append(Paragraph(note, note_style))
        
        elements.append(Spacer(1, 15*mm))
        
        # 発行情報
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=9,
            alignment=2,  # RIGHT
        )
        elements.append(Paragraph(
            f"発行日: {datetime.now().strftime('%Y年%m月%d日')}",
            footer_style
        ))
        elements.append(Paragraph(
            "日本体育大学陸上競技部",
            footer_style
        ))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
    
    @classmethod
    def generate_all_permits_pdf(cls, competition):
        """
        全団体の駐車許可証を一括生成（1PDFに複数ページ）
        """
        from payments.models import ParkingRequest
        
        buffer = io.BytesIO()
        font_name = PDFGenerator._setup_fonts()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        parking_requests = ParkingRequest.objects.filter(
            competition=competition,
            status='assigned'
        ).select_related('organization').order_by('organization__name_kana')
        
        for i, parking_request in enumerate(parking_requests):
            if i > 0:
                from reportlab.platypus import PageBreak
                elements.append(PageBreak())
            
            # 各団体の許可証を追加
            cls._add_permit_page(elements, parking_request, font_name, styles)
        
        if elements:
            doc.build(elements)
        
        buffer.seek(0)
        return buffer
    
    @classmethod
    def _add_permit_page(cls, elements, parking_request, font_name, styles):
        """1団体分の許可証ページを追加"""
        # スタイル定義
        title_style = ParagraphStyle(
            'PermitTitle',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=24,
            alignment=1,
            spaceAfter=10*mm
        )
        
        org_style = ParagraphStyle(
            'OrgName',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=28,
            alignment=1,
            spaceAfter=10*mm
        )
        
        info_style = ParagraphStyle(
            'InfoStyle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=16,
            alignment=1,
            spaceAfter=5*mm
        )
        
        # コンテンツ
        elements.append(Paragraph("駐 車 許 可 証", title_style))
        elements.append(Paragraph(parking_request.competition.name, info_style))
        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph(parking_request.organization.name, org_style))
        elements.append(Spacer(1, 10*mm))
        
        permit_info = parking_request.get_permit_info()
        elements.append(Paragraph(f"駐車場: {permit_info['parking_lot']}", info_style))
        
        if permit_info['entry_time']:
            elements.append(Paragraph(
                f"入庫: {permit_info['entry_time'].strftime('%H:%M')}～",
                info_style
            ))
        if permit_info['exit_time']:
            elements.append(Paragraph(
                f"出庫: ～{permit_info['exit_time'].strftime('%H:%M')}",
                info_style
            ))


class ResultSheetPDFGenerator:
    """結果記録用紙PDF生成（陸協フォーマット）"""
    
    @classmethod
    def generate_result_sheet_pdf(cls, heat):
        """
        結果記録用紙PDF（1組分）
        陸連公式フォーマット準拠
        """
        buffer = io.BytesIO()
        font_name = PDFGenerator._setup_fonts()
        
        # 横向きA4
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=10*mm,
            leftMargin=10*mm,
            topMargin=10*mm,
            bottomMargin=10*mm
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # タイトルスタイル
        title_style = ParagraphStyle(
            'ResultTitle',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=14,
            alignment=1,
            spaceAfter=5*mm
        )
        
        # ヘッダー情報
        race = heat.race
        competition = race.competition
        
        elements.append(Paragraph(
            f"{competition.name}　{race.name}　{heat.heat_number}組",
            title_style
        ))
        
        # 日付
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=10,
            alignment=2,  # RIGHT
        )
        elements.append(Paragraph(
            f"{competition.event_date.strftime('%Y年%m月%d日')}",
            date_style
        ))
        elements.append(Spacer(1, 3*mm))
        
        # ヘッダー行（2行構成）
        header_row1 = ['ﾚｰﾝ', 'No', '競技者名', '所属', '所属地', '記録', '順位', 'ｺﾒﾝﾄ', '通過', '備考']
        
        # データ行
        assignments = heat.assignments.select_related(
            'entry', 'entry__athlete', 'entry__athlete__organization'
        ).order_by('bib_number')
        
        data_rows = []
        
        for assignment in assignments:
            athlete = assignment.entry.athlete
            org = athlete.organization
            org_name = org.short_name if org else ''
            
            # 所属地（都道府県）- organizationのprefectureまたはathleteの情報から取得
            prefecture = ''
            if org and hasattr(org, 'prefecture') and org.prefecture:
                prefecture = org.prefecture
            elif hasattr(athlete, 'prefecture') and athlete.prefecture:
                prefecture = athlete.prefecture
            
            # カナ名（半角カナ）
            kana_name = cls._to_half_width_kana(athlete.full_name_kana) if athlete.full_name_kana else ''
            
            # 漢字名＋年齢コード
            birth_year = athlete.birth_date.year if athlete.birth_date else None
            age_code = ''
            if birth_year:
                age_code = f"（{str(birth_year)[2:]}）"
            kanji_name = f"{athlete.full_name}{age_code}"
            
            # ランダム4桁No生成
            random_no = random.randint(1000, 9999)
            
            # 2行を1セルにまとめる形式
            # 1行目: レーン, No, カナ名, 所属
            # 2行目: 空, 空, 漢字名, 所属地, 記録, 順位, コメント, 通過, 備考
            data_rows.append([
                str(assignment.bib_number or ''),  # レーン（腰番号）
                str(random_no),  # No（ランダム4桁）
                kana_name,  # カナ名
                org_name,  # 所属
                prefecture,  # 所属地
                '',  # 記録（空欄）
                '',  # 順位（空欄）
                '',  # コメント（空欄）
                '',  # 通過（空欄）
                '',  # 備考（空欄）
            ])
            data_rows.append([
                '',  # レーン（空）
                '',  # No（空）
                kanji_name,  # 漢字名
                '',  # 所属（空）
                '',  # 所属地（空）
                '',  # 記録（空欄）
                '',  # 順位（空欄）
                '',  # コメント（空欄）
                '',  # 通過（空欄）
                '',  # 備考（空欄）
            ])
        
        # テーブル全体を構築
        all_data = [header_row1] + data_rows
        
        # 列幅設定
        col_widths = [15*mm, 15*mm, 55*mm, 45*mm, 25*mm, 30*mm, 15*mm, 25*mm, 25*mm, 25*mm]
        
        table = Table(all_data, colWidths=col_widths)
        
        # スタイル設定
        style_commands = [
            ('FONT', (0, 0), (-1, -1), font_name, 9),
            ('FONT', (0, 0), (-1, 0), font_name, 8),  # ヘッダーは小さめ
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.9)),  # ヘッダー背景
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),  # 競技者名は左寄せ
            ('ALIGN', (3, 1), (3, -1), 'LEFT'),  # 所属は左寄せ
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, 0), 1, colors.black),  # ヘッダー罫線
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),  # ヘッダー下線
            ('ROWHEIGHTS', (0, 0), (0, 0), 7*mm),  # ヘッダー行高さ
        ]
        
        # データ行の罫線と行高さ
        for i in range(1, len(all_data)):
            style_commands.append(('ROWHEIGHTS', (0, i), (-1, i), 6*mm))
            # 2行ごとに下線（選手ごとの区切り）
            if i % 2 == 0:
                style_commands.append(('LINEBELOW', (0, i), (-1, i), 1, colors.black))
            else:
                style_commands.append(('LINEBELOW', (0, i), (-1, i), 0.5, colors.grey))
        
        # 縦線
        style_commands.append(('LINEBEFORE', (0, 0), (0, -1), 1, colors.black))
        for col in range(1, len(col_widths) + 1):
            style_commands.append(('LINEBEFORE', (col, 0), (col, -1), 0.5, colors.grey))
        style_commands.append(('LINEAFTER', (-1, 0), (-1, -1), 1, colors.black))
        
        table.setStyle(TableStyle(style_commands))
        elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
    
    @classmethod
    def generate_all_result_sheets_pdf(cls, race):
        """
        全組の結果記録用紙を一括生成（1PDFに複数ページ）
        """
        from reportlab.platypus import PageBreak
        
        buffer = io.BytesIO()
        font_name = PDFGenerator._setup_fonts()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=10*mm,
            leftMargin=10*mm,
            topMargin=10*mm,
            bottomMargin=10*mm
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        heats = race.heats.order_by('heat_number')
        
        for i, heat in enumerate(heats):
            if i > 0:
                elements.append(PageBreak())
            
            cls._add_result_sheet_page(elements, heat, font_name, styles)
        
        if elements:
            doc.build(elements)
        
        buffer.seek(0)
        return buffer
    
    @classmethod
    def _add_result_sheet_page(cls, elements, heat, font_name, styles):
        """1組分の結果記録用紙ページを追加"""
        # タイトルスタイル
        title_style = ParagraphStyle(
            'ResultTitle',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=14,
            alignment=1,
            spaceAfter=5*mm
        )
        
        race = heat.race
        competition = race.competition
        
        elements.append(Paragraph(
            f"{competition.name}　{race.name}　{heat.heat_number}組",
            title_style
        ))
        
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=10,
            alignment=2,
        )
        elements.append(Paragraph(
            f"{competition.event_date.strftime('%Y年%m月%d日')}",
            date_style
        ))
        elements.append(Spacer(1, 3*mm))
        
        # ヘッダー
        header_row = ['ﾚｰﾝ', 'No', '競技者名', '所属', '所属地', '記録', '順位', 'ｺﾒﾝﾄ', '通過', '備考']
        
        assignments = heat.assignments.select_related(
            'entry', 'entry__athlete', 'entry__athlete__organization'
        ).order_by('bib_number')
        
        data_rows = []
        
        for assignment in assignments:
            athlete = assignment.entry.athlete
            org = athlete.organization
            org_name = org.short_name if org else ''
            
            prefecture = ''
            if org and hasattr(org, 'prefecture') and org.prefecture:
                prefecture = org.prefecture
            elif hasattr(athlete, 'prefecture') and athlete.prefecture:
                prefecture = athlete.prefecture
            
            kana_name = cls._to_half_width_kana(athlete.full_name_kana) if athlete.full_name_kana else ''
            
            birth_year = athlete.birth_date.year if athlete.birth_date else None
            age_code = ''
            if birth_year:
                age_code = f"（{str(birth_year)[2:]}）"
            kanji_name = f"{athlete.full_name}{age_code}"
            
            random_no = random.randint(1000, 9999)
            
            # 1行目（カナ名）
            data_rows.append([
                str(assignment.bib_number or ''),
                str(random_no),
                kana_name,
                org_name,
                prefecture,
                '',
                '',
                '',
                '',
                '',
            ])
            # 2行目（漢字名）
            data_rows.append([
                '',
                '',
                kanji_name,
                '',
                '',
                '',
                '',
                '',
                '',
                '',
            ])
        
        all_data = [header_row] + data_rows
        col_widths = [15*mm, 15*mm, 55*mm, 45*mm, 25*mm, 30*mm, 15*mm, 25*mm, 25*mm, 25*mm]
        
        table = Table(all_data, colWidths=col_widths)
        
        style_commands = [
            ('FONT', (0, 0), (-1, -1), font_name, 9),
            ('FONT', (0, 0), (-1, 0), font_name, 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.9)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            ('ALIGN', (3, 1), (3, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, 0), 1, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('ROWHEIGHTS', (0, 0), (0, 0), 7*mm),
        ]
        
        for i in range(1, len(all_data)):
            style_commands.append(('ROWHEIGHTS', (0, i), (-1, i), 6*mm))
            if i % 2 == 0:
                style_commands.append(('LINEBELOW', (0, i), (-1, i), 1, colors.black))
            else:
                style_commands.append(('LINEBELOW', (0, i), (-1, i), 0.5, colors.grey))
        
        style_commands.append(('LINEBEFORE', (0, 0), (0, -1), 1, colors.black))
        for col in range(1, len(col_widths) + 1):
            style_commands.append(('LINEBEFORE', (col, 0), (col, -1), 0.5, colors.grey))
        style_commands.append(('LINEAFTER', (-1, 0), (-1, -1), 1, colors.black))
        
        table.setStyle(TableStyle(style_commands))
        elements.append(table)
    
    @staticmethod
    def _to_half_width_kana(text):
        """
        全角カナを半角カナに変換
        """
        if not text:
            return ''
        
        # 全角カナ→半角カナ変換テーブル
        kana_map = {
            'ア': 'ｱ', 'イ': 'ｲ', 'ウ': 'ｳ', 'エ': 'ｴ', 'オ': 'ｵ',
            'カ': 'ｶ', 'キ': 'ｷ', 'ク': 'ｸ', 'ケ': 'ｹ', 'コ': 'ｺ',
            'サ': 'ｻ', 'シ': 'ｼ', 'ス': 'ｽ', 'セ': 'ｾ', 'ソ': 'ｿ',
            'タ': 'ﾀ', 'チ': 'ﾁ', 'ツ': 'ﾂ', 'テ': 'ﾃ', 'ト': 'ﾄ',
            'ナ': 'ﾅ', 'ニ': 'ﾆ', 'ヌ': 'ﾇ', 'ネ': 'ﾈ', 'ノ': 'ﾉ',
            'ハ': 'ﾊ', 'ヒ': 'ﾋ', 'フ': 'ﾌ', 'ヘ': 'ﾍ', 'ホ': 'ﾎ',
            'マ': 'ﾏ', 'ミ': 'ﾐ', 'ム': 'ﾑ', 'メ': 'ﾒ', 'モ': 'ﾓ',
            'ヤ': 'ﾔ', 'ユ': 'ﾕ', 'ヨ': 'ﾖ',
            'ラ': 'ﾗ', 'リ': 'ﾘ', 'ル': 'ﾙ', 'レ': 'ﾚ', 'ロ': 'ﾛ',
            'ワ': 'ﾜ', 'ヲ': 'ｦ', 'ン': 'ﾝ',
            'ガ': 'ｶﾞ', 'ギ': 'ｷﾞ', 'グ': 'ｸﾞ', 'ゲ': 'ｹﾞ', 'ゴ': 'ｺﾞ',
            'ザ': 'ｻﾞ', 'ジ': 'ｼﾞ', 'ズ': 'ｽﾞ', 'ゼ': 'ｾﾞ', 'ゾ': 'ｿﾞ',
            'ダ': 'ﾀﾞ', 'ヂ': 'ﾁﾞ', 'ヅ': 'ﾂﾞ', 'デ': 'ﾃﾞ', 'ド': 'ﾄﾞ',
            'バ': 'ﾊﾞ', 'ビ': 'ﾋﾞ', 'ブ': 'ﾌﾞ', 'ベ': 'ﾍﾞ', 'ボ': 'ﾎﾞ',
            'パ': 'ﾊﾟ', 'ピ': 'ﾋﾟ', 'プ': 'ﾌﾟ', 'ペ': 'ﾍﾟ', 'ポ': 'ﾎﾟ',
            'ァ': 'ｧ', 'ィ': 'ｨ', 'ゥ': 'ｩ', 'ェ': 'ｪ', 'ォ': 'ｫ',
            'ャ': 'ｬ', 'ュ': 'ｭ', 'ョ': 'ｮ', 'ッ': 'ｯ',
            'ヴ': 'ｳﾞ', 'ー': 'ｰ', '　': ' ',
        }
        
        result = ''
        for char in text:
            result += kana_map.get(char, char)
        return result

