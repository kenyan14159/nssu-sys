"""
payments/notifications.py
入金確認メール通知機能
"""
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def send_payment_approved_email(payment):
    """
    入金承認時のメール通知
    """
    entry_group = payment.entry_group
    user = entry_group.registered_by
    competition = entry_group.competition
    
    # エントリー一覧を取得
    entries = entry_group.entries.select_related('athlete', 'race').all()
    
    context = {
        'user': user,
        'payment': payment,
        'entry_group': entry_group,
        'competition': competition,
        'entries': entries,
    }
    
    # テンプレートからメール本文を生成
    subject = f'[Nit-Sys] 入金確認完了のお知らせ - {competition.name}'
    message = render_to_string('payments/email/payment_approved.txt', context)
    html_message = render_to_string('payments/email/payment_approved.html', context)
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"[Email] 送信エラー: {e}")
        return False


def send_payment_rejected_email(payment, reason=''):
    """
    入金却下時のメール通知
    """
    entry_group = payment.entry_group
    user = entry_group.registered_by
    competition = entry_group.competition
    
    context = {
        'user': user,
        'payment': payment,
        'entry_group': entry_group,
        'competition': competition,
        'reason': reason or payment.review_note,
    }
    
    subject = f'[Nit-Sys] 入金確認について - {competition.name}'
    message = render_to_string('payments/email/payment_rejected.txt', context)
    html_message = render_to_string('payments/email/payment_rejected.html', context)
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"[Email] 送信エラー: {e}")
        return False
