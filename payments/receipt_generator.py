"""
領収書PDF生成モジュール
ReportLabを使用して、公印付きの正式な領収書を生成
"""
import io
import os
from datetime import datetime

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


# 日本語フォント登録（システムフォントを使用）
def register_japanese_font():
    """日本語フォントを登録"""
    # macOS のヒラギノ角ゴシック
    mac_font_paths = [
        '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
        '/System/Library/Fonts/Hiragino Sans GB.ttc',
        '/Library/Fonts/Arial Unicode.ttf',
    ]
    
    # Linux / Windows の代替フォント
    other_font_paths = [
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        'C:/Windows/Fonts/msgothic.ttc',
    ]
    
    font_paths = mac_font_paths + other_font_paths
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('JapaneseFont', font_path))
                return 'JapaneseFont'
            except Exception:
                continue
    
    # フォールバック: Helveticaを使用（日本語表示に問題あり）
    return 'Helvetica'


def generate_receipt_pdf(payment):
    """
    領収書PDFを生成
    
    Args:
        payment: Paymentモデルのインスタンス
    
    Returns:
        bytes: PDF のバイナリデータ
    """
    buffer = io.BytesIO()
    
    # A4サイズでキャンバス作成
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # フォント登録
    font_name = register_japanese_font()
    
    # ===== ヘッダー =====
    # タイトル「領収書」
    c.setFont(font_name, 36)
    c.drawCentredString(width / 2, height - 60 * mm, '領 収 書')
    
    # 管理番号
    c.setFont(font_name, 10)
    receipt_number = f"No. R-{payment.entry_group.competition.id:03d}-{payment.entry_group.id:05d}"
    c.drawRightString(width - 20 * mm, height - 25 * mm, receipt_number)
    
    # 発行日
    issue_date = payment.reviewed_at.strftime('%Y年%m月%d日') if payment.reviewed_at else datetime.now().strftime('%Y年%m月%d日')
    c.drawRightString(width - 20 * mm, height - 32 * mm, f"発行日: {issue_date}")
    
    # ===== 宛名 =====
    c.setFont(font_name, 14)
    organization_name = payment.entry_group.organization.name if payment.entry_group.organization else '個人'
    c.drawString(25 * mm, height - 85 * mm, f"{organization_name}　様")
    
    # 下線
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(25 * mm, height - 88 * mm, 130 * mm, height - 88 * mm)
    
    # ===== 金額 =====
    c.setFont(font_name, 10)
    c.drawString(25 * mm, height - 105 * mm, '金額')
    
    # 金額枠
    c.setLineWidth(2)
    c.rect(40 * mm, height - 118 * mm, 120 * mm, 15 * mm, stroke=1, fill=0)
    
    # 金額表示
    c.setFont(font_name, 24)
    amount = payment.entry_group.total_amount
    amount_str = f"¥ {amount:,}-"
    c.drawCentredString(100 * mm, height - 113 * mm, amount_str)
    
    # ===== 但し書き =====
    c.setFont(font_name, 12)
    competition_name = payment.entry_group.competition.name
    c.drawString(25 * mm, height - 135 * mm, '但し書き：')
    c.drawString(50 * mm, height - 135 * mm, f"{competition_name} 参加料として")
    
    # ===== 内訳 =====
    c.setFont(font_name, 10)
    c.drawString(25 * mm, height - 155 * mm, '【内訳】')
    
    entry_count = payment.entry_group.entries.count()
    entry_fee = payment.entry_group.competition.entry_fee
    c.drawString(35 * mm, height - 165 * mm, f"・エントリー数: {entry_count}名")
    c.drawString(35 * mm, height - 173 * mm, f"・参加料単価: ¥{entry_fee:,}")
    c.drawString(35 * mm, height - 181 * mm, f"・合計金額: ¥{amount:,}")
    
    # ===== 注意書き =====
    c.setFont(font_name, 8)
    c.setFillColor(colors.gray)
    c.drawString(25 * mm, height - 200 * mm, '※ 電子領収書です。印紙税はかかりません。')
    c.drawString(25 * mm, height - 207 * mm, '※ 宛名の変更はできません。変更が必要な場合は事務局にお問い合わせください。')
    c.setFillColor(colors.black)
    
    # ===== 発行元 =====
    c.setFont(font_name, 12)
    c.drawRightString(width - 30 * mm, height - 230 * mm, '日本体育大学陸上競技部')
    c.setFont(font_name, 9)
    c.drawRightString(width - 30 * mm, height - 240 * mm, '〒227-0033')
    c.drawRightString(width - 30 * mm, height - 248 * mm, '神奈川県横浜市青葉区鴨志田町1221-1')
    c.drawRightString(width - 30 * mm, height - 256 * mm, '日本体育大学 健志台キャンパス')
    
    # ===== 公印画像 =====
    # 公印画像のパス（static/images/seal.pngに配置想定）
    seal_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'seal.png')
    if os.path.exists(seal_path):
        # 公印画像を重ねて表示（透過PNG）
        c.drawImage(
            seal_path,
            width - 65 * mm,  # X座標
            height - 270 * mm,  # Y座標
            width=35 * mm,
            height=35 * mm,
            mask='auto'  # 透過処理
        )
    else:
        # 公印画像がない場合は代替テキスト
        c.setStrokeColor(colors.red)
        c.setFillColor(colors.red)
        c.circle(width - 47 * mm, height - 252 * mm, 15 * mm, stroke=1, fill=0)
        c.setFont(font_name, 10)
        c.drawCentredString(width - 47 * mm, height - 250 * mm, '日体大')
        c.drawCentredString(width - 47 * mm, height - 257 * mm, '陸上部')
        c.setFillColor(colors.black)
    
    # ===== フッター =====
    c.setFont(font_name, 8)
    c.setFillColor(colors.gray)
    c.drawCentredString(width / 2, 20 * mm, 'この領収書は日本体育大学陸上競技部が発行する正式な電子領収書です。')
    c.drawCentredString(width / 2, 15 * mm, f'管理番号: {receipt_number} | 発行システム: Nit-Sys')
    
    # PDF保存
    c.save()
    
    buffer.seek(0)
    return buffer.getvalue()
