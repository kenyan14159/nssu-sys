"""
payments ビュー
"""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models, transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.utils import admin_required, log_permission_denied
from entries.models import EntryGroup

from .forms import PaymentReviewForm, PaymentUploadForm
from .models import BankAccount, ParkingRequest, Payment
from .notifications import send_payment_approved_email, send_payment_rejected_email

security_logger = logging.getLogger('security')


@login_required
def payment_upload(request, entry_group_pk):
    """振込明細アップロード"""
    entry_group = get_object_or_404(EntryGroup, pk=entry_group_pk)
    
    # 権限チェック
    if entry_group.registered_by != request.user:
        log_permission_denied(request, "payment upload - wrong user")
        messages.error(request, '権限がありません。')
        return redirect('competitions:dashboard')
    
    # 既にPaymentが存在するかチェック
    try:
        payment = entry_group.payment
        # 既に承認済みの場合
        if payment.status == 'approved':
            messages.info(request, 'この申込は既に確定しています。')
            return redirect('payments:status', entry_group_pk=entry_group_pk)
    except Payment.DoesNotExist:
        payment = None
    
    # 振込先口座情報
    bank_account = BankAccount.objects.filter(is_active=True).first()
    
    if request.method == 'POST':
        form = PaymentUploadForm(request.POST, request.FILES, instance=payment)
        if form.is_valid():
            with transaction.atomic():
                payment = form.save(commit=False)
                payment.entry_group = entry_group
                payment.save()
                
                # エントリーグループのステータスを更新
                entry_group.status = 'payment_uploaded'
                entry_group.save()
                
                # 各エントリーのステータスも更新
                entry_group.entries.update(status='payment_uploaded')
            
            messages.success(request, '振込明細をアップロードしました。確認をお待ちください。')
            return redirect('payments:status', entry_group_pk=entry_group_pk)
    else:
        form = PaymentUploadForm(instance=payment)

    # 合計金額を最新化して表示
    try:
        entry_group.calculate_total()
    except Exception:
        # 計算は副作用なしで失敗しても表示継続
        pass

    return render(request, 'payments/payment_upload.html', {
        'form': form,
        'entry_group': entry_group,
        'bank_account': bank_account,
    })


@login_required
def payment_status(request, entry_group_pk):
    """支払い状態確認"""
    entry_group = get_object_or_404(EntryGroup, pk=entry_group_pk)
    
    # 権限チェック
    if not request.user.is_admin and entry_group.registered_by != request.user:
        messages.error(request, '権限がありません。')
        return redirect('competitions:dashboard')
    
    try:
        payment = entry_group.payment
    except Payment.DoesNotExist:
        payment = None

    # 合計金額を最新化して表示
    try:
        entry_group.calculate_total()
    except Exception:
        pass

    return render(request, 'payments/payment_status.html', {
        'entry_group': entry_group,
        'payment': payment,
    })


@admin_required
def payment_list(request):
    """入金確認一覧（管理者用）"""
    from django.utils import timezone
    
    status_filter = request.GET.get('status', 'pending')
    
    payments = Payment.objects.select_related(
        'entry_group', 'entry_group__organization', 'entry_group__competition'
    ).order_by('-uploaded_at')
    
    # 統計情報を計算
    pending_count = Payment.objects.filter(status='pending').count()
    
    # 本日承認数・金額
    today = timezone.localdate()
    today_approved = Payment.objects.filter(
        status='approved',
        reviewed_at__date=today
    )
    approved_count = today_approved.count()
    total_amount = sum(p.entry_group.total_amount or 0 for p in today_approved.select_related('entry_group'))
    
    if status_filter != 'all':
        payments = payments.filter(status=status_filter)
    
    paginator = Paginator(payments, 20)
    page = request.GET.get('page')
    payments = paginator.get_page(page)
    
    return render(request, 'payments/admin/payment_list.html', {
        'payments': payments,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'total_amount': total_amount,
    })


@admin_required
def payment_review(request, pk):
    """入金確認（管理者用）"""
    payment = get_object_or_404(Payment, pk=pk)
    
    if request.method == 'POST':
        form = PaymentReviewForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            note = form.cleaned_data.get('note', '')
            
            with transaction.atomic():
                if action == 'approve':
                    payment.approve(request.user)
                    # メール送信（失敗してもトランザクションは継続）
                    email_sent = send_payment_approved_email(payment)
                    if email_sent:
                        messages.success(request, '入金を承認し、確認メールを送信しました。')
                    else:
                        messages.success(request, '入金を承認しました。（メール送信に失敗しました）')
                else:
                    payment.reject(request.user, note)
                    # メール送信（失敗してもトランザクションは継続）
                    email_sent = send_payment_rejected_email(payment, note)
                    if email_sent:
                        messages.warning(request, '入金を却下し、通知メールを送信しました。')
                    else:
                        messages.warning(request, '入金を却下しました。（メール送信に失敗しました）')
            
            return redirect('payments:admin_list')
    else:
        form = PaymentReviewForm()
    
    return render(request, 'payments/admin/payment_review.html', {
        'payment': payment,
        'form': form,
    })


@admin_required
def force_approve_search(request, competition_pk=None):
    """
    強制承認用の選手検索（トラブルデスク用）
    """
    from competitions.models import Competition
    from entries.models import Entry
    
    if competition_pk:
        competition = get_object_or_404(Competition, pk=competition_pk)
    else:
        # 直近の大会を取得
        competition = Competition.objects.filter(is_published=True).order_by('-event_date').first()
    
    query = request.GET.get('q', '')
    results = []
    
    if query:
        # 未確定のエントリーを検索
        results = Entry.objects.filter(
            race__competition=competition,
            status__in=['pending', 'payment_uploaded']
        ).filter(
            models.Q(athlete__last_name__icontains=query) |
            models.Q(athlete__first_name__icontains=query) |
            models.Q(athlete__organization__name__icontains=query)
        ).select_related(
            'athlete', 'athlete__organization', 'race'
        )[:50]
    
    return render(request, 'payments/admin/force_approve_search.html', {
        'competition': competition,
        'query': query,
        'results': results,
    })


@admin_required
@transaction.atomic
def force_approve(request, entry_group_pk):
    """
    強制承認（トラブルデスク用）
    振込明細画像なしでも支払いを承認する
    """
    entry_group = get_object_or_404(EntryGroup, pk=entry_group_pk)
    
    if request.method == 'POST':
        note = request.POST.get('note', '当日現場確認')
        
        # Paymentが存在しない場合は作成
        try:
            payment = entry_group.payment
        except Payment.DoesNotExist:
            payment = Payment.objects.create(
                entry_group=entry_group,
                status='pending',
            )
        
        # 強制承認実行
        payment.force_approve(request.user, note)
        
        # メール送信（強制承認の場合も確認メールを送信）
        email_sent = send_payment_approved_email(payment)
        
        # セキュリティログ
        security_logger.warning(
            f"強制承認実行: entry_group={entry_group_pk}, "
            f"organization={entry_group.organization}, "
            f"user={request.user.email}, note={note}"
        )
        
        org_name = entry_group.organization.name if entry_group.organization else "個人"
        if email_sent:
            messages.success(
                request,
                f'{org_name}の支払いを強制承認し、確認メールを送信しました。'
            )
        else:
            messages.success(
                request,
                f'{org_name}の支払いを強制承認しました。'
            )
        
        referer = request.META.get('HTTP_REFERER')
        if referer and 'force_approve_search' in referer:
            return redirect(referer)
        return redirect('payments:admin_list')
    
    return render(request, 'payments/admin/force_approve_confirm.html', {
        'entry_group': entry_group,
    })


@login_required
def parking_permit_download(request, parking_request_pk):
    """駐車許可証PDFダウンロード"""
    parking_request = get_object_or_404(ParkingRequest, pk=parking_request_pk)
    
    # 権限チェック
    if not request.user.is_admin:
        if request.user.organization != parking_request.organization:
            log_permission_denied(request, "parking permit download - wrong organization")
            messages.error(request, '権限がありません。')
            return redirect('competitions:dashboard')
    
    # 割当済みかチェック
    if not parking_request.is_assigned:
        messages.error(request, '駐車場が割り当てられていません。')
        return redirect('competitions:dashboard')
    
    # PDF生成
    from reports.generators import ParkingPermitPDFGenerator
    
    pdf_buffer = ParkingPermitPDFGenerator.generate_permit_pdf(parking_request)
    
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    filename = f"parking_permit_{parking_request.organization.pk}_{parking_request.competition.pk}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@login_required
def parking_request_view(request, competition_pk):
    """駐車場申請・確認"""
    from competitions.models import Competition

    from .forms import ParkingRequestForm
    
    competition = get_object_or_404(Competition, pk=competition_pk)
    user = request.user
    
    if not user.organization:
        messages.error(request, '団体に所属していない場合は駐車場申請はできません。')
        return redirect('competitions:detail', pk=competition_pk)
    
    # 既存の申請を取得または新規作成
    try:
        parking_request = ParkingRequest.objects.get(
            organization=user.organization,
            competition=competition
        )
        is_new = False
    except ParkingRequest.DoesNotExist:
        parking_request = None
        is_new = True
    
    if request.method == 'POST':
        form = ParkingRequestForm(request.POST)
        if form.is_valid():
            if parking_request is None:
                parking_request = ParkingRequest(
                    organization=user.organization,
                    competition=competition,
                    requested_by=user
                )
            
            # 既に割当済みの場合は変更不可
            if parking_request.status == 'assigned':
                messages.warning(request, '既に駐車場が割り当てられているため、申請内容を変更できません。')
                return redirect('payments:parking_request', competition_pk=competition_pk)
            
            parking_request.requested_large_bus = form.cleaned_data['requested_large_bus']
            parking_request.requested_medium_bus = form.cleaned_data['requested_medium_bus']
            parking_request.requested_car = form.cleaned_data['requested_car']
            parking_request.request_note = form.cleaned_data.get('notes', '')
            parking_request.save()
            
            if is_new:
                messages.success(request, '駐車場申請を送信しました。')
            else:
                messages.success(request, '駐車場申請を更新しました。')
            
            return redirect('payments:parking_request', competition_pk=competition_pk)
    else:
        if parking_request:
            form = ParkingRequestForm(initial={
                'requested_large_bus': parking_request.requested_large_bus,
                'requested_medium_bus': parking_request.requested_medium_bus,
                'requested_car': parking_request.requested_car,
                'notes': parking_request.request_note if hasattr(parking_request, 'request_note') else '',
            })
        else:
            form = ParkingRequestForm()
    
    return render(request, 'payments/parking_request.html', {
        'competition': competition,
        'parking_request': parking_request,
        'form': form,
        'is_new': is_new,
    })


@admin_required
def parking_csv_import(request, competition_pk):
    """駐車場割当CSVインポート（管理者用）"""
    from competitions.models import Competition

    from .parking_import import import_parking_csv
    
    competition = get_object_or_404(Competition, pk=competition_pk)
    
    if request.method == 'POST':
        if 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']
            
            try:
                result = import_parking_csv(csv_file, competition, request.user)
                
                if result.success_count > 0:
                    messages.success(
                        request, 
                        f'{result.success_count}件の駐車場割当をインポートしました。'
                    )
                
                for warning in result.warnings:
                    messages.warning(
                        request, 
                        f'行{warning["row"]}: {warning["message"]}'
                    )
                
                for error in result.errors:
                    messages.error(
                        request, 
                        f'行{error["row"]}: {error["message"]}'
                    )
                
            except Exception as e:
                messages.error(request, f'インポートに失敗しました: {str(e)}')
        
        return redirect('payments:parking_csv_import', competition_pk=competition_pk)
    
    # 現在の駐車場申請一覧
    parking_requests = ParkingRequest.objects.filter(
        competition=competition
    ).select_related('organization').order_by('organization__name_kana')
    
    return render(request, 'payments/admin/parking_csv_import.html', {
        'competition': competition,
        'parking_requests': parking_requests,
    })


@admin_required
def parking_csv_template(request):
    """駐車場CSVテンプレートダウンロード"""
    from .parking_import import generate_sample_csv
    
    csv_content = generate_sample_csv()
    
    response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="parking_template.csv"'
    
    return response


@admin_required
def all_permits_download(request, competition_pk):
    """全駐車許可証一括ダウンロード（管理者用）"""
    from competitions.models import Competition
    from reports.generators import ParkingPermitPDFGenerator
    
    competition = get_object_or_404(Competition, pk=competition_pk)
    
    pdf_buffer = ParkingPermitPDFGenerator.generate_all_permits_pdf(competition)
    
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    filename = f"all_parking_permits_{competition.pk}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@login_required
def receipt_download(request, entry_group_pk):
    """
    領収書PDFダウンロード
    
    入金が承認済み（PAID）の場合のみダウンロード可能。
    宛名は所属団体名が自動印字され、変更不可。
    """
    from .receipt_generator import generate_receipt_pdf
    
    entry_group = get_object_or_404(EntryGroup, pk=entry_group_pk)
    
    # 権限チェック: 本人または管理者のみ
    if not request.user.is_admin and entry_group.registered_by != request.user:
        security_logger.warning(
            f'Unauthorized receipt download attempt: user={request.user.pk}, entry_group={entry_group_pk}'
        )
        messages.error(request, '権限がありません。')
        return redirect('competitions:dashboard')
    
    # Paymentの存在チェック
    try:
        payment = entry_group.payment
    except Payment.DoesNotExist:
        messages.error(request, '入金情報が見つかりません。')
        return redirect('payments:status', entry_group_pk=entry_group_pk)
    
    # 承認済みチェック
    if payment.status != 'approved':
        messages.error(request, '入金が承認されていないため、領収書を発行できません。')
        return redirect('payments:status', entry_group_pk=entry_group_pk)
    
    # PDF生成
    try:
        pdf_data = generate_receipt_pdf(payment)
    except Exception as e:
        security_logger.error(f'Receipt PDF generation failed: {str(e)}')
        messages.error(request, '領収書の生成に失敗しました。管理者にお問い合わせください。')
        return redirect('payments:status', entry_group_pk=entry_group_pk)
    
    # ファイル名生成
    competition_name = entry_group.competition.name.replace(' ', '_').replace('/', '_')
    organization_name = entry_group.organization.name if entry_group.organization else 'individual'
    filename = f"receipt_{competition_name}_{organization_name}.pdf"
    
    # レスポンス返却
    response = HttpResponse(pdf_data, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response
