"""
entries ビュー
"""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.utils import log_permission_denied
from competitions.models import Competition, Race

from .excel_import import ExcelEntryImporter, ExcelImportError, generate_entry_template
from .forms import EntryForm, ExcelUploadForm
from .models import Entry, EntryGroup

security_logger = logging.getLogger('security')


@login_required
def entry_create(request, competition_pk, race_pk):
    """エントリー作成"""
    competition = get_object_or_404(Competition, pk=competition_pk)
    race = get_object_or_404(Race, pk=race_pk, competition=competition)
    
    # エントリー可能かチェック
    if not competition.can_entry:
        messages.error(request, 'この大会は現在エントリーを受け付けていません。')
        return redirect('competitions:detail', pk=competition_pk)
    
    # 種目の定員チェック
    if race.is_full:
        messages.error(request, 'この種目は定員に達しています。')
        return redirect('competitions:detail', pk=competition_pk)
    
    if request.method == 'POST':
        form = EntryForm(request.POST, race=race, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                entry = form.save()
                messages.success(request, f'{entry.athlete.full_name}のエントリーを受け付けました。')
                
                # 続けてエントリーするか確認
                if request.POST.get('continue'):
                    return redirect('entries:create', competition_pk=competition_pk, race_pk=race_pk)
                return redirect('entries:cart', competition_pk=competition_pk)
    else:
        form = EntryForm(race=race, user=request.user)
    
    return render(request, 'entries/entry_form.html', {
        'form': form,
        'competition': competition,
        'race': race,
    })


@login_required
def entry_cart(request, competition_pk):
    """エントリー確認（未確定エントリー一覧）"""
    competition = get_object_or_404(Competition, pk=competition_pk)
    user = request.user
    
    # 未確定のエントリーを取得（N+1クエリ解消）
    if user.organization:
        entries = Entry.objects.filter(
            race__competition=competition,
            athlete__organization=user.organization,
            status='pending'
        ).select_related(
            'athlete',
            'athlete__organization',
            'race',
            'race__competition'
        ).only(
            'id', 'declared_time', 'status', 'created_at',
            'athlete__id', 'athlete__last_name', 'athlete__first_name',
            'athlete__organization__id', 'athlete__organization__short_name',
            'race__id', 'race__name', 'race__distance',
            'race__competition__id', 'race__competition__entry_fee'
        )
    else:
        entries = Entry.objects.filter(
            race__competition=competition,
            athlete__user=user,
            status='pending'
        ).select_related(
            'athlete',
            'race',
            'race__competition'
        ).only(
            'id', 'declared_time', 'status', 'created_at',
            'athlete__id', 'athlete__last_name', 'athlete__first_name',
            'race__id', 'race__name', 'race__distance',
            'race__competition__id', 'race__competition__entry_fee'
        )
    
    # 合計金額（entry_fee が None の場合は 2000 をデフォルト）
    entry_fee = competition.entry_fee if competition.entry_fee else 2000
    total_amount = entries.count() * entry_fee
    
    return render(request, 'entries/entry_cart.html', {
        'competition': competition,
        'entries': entries,
        'total_amount': total_amount,
    })


@login_required
def entry_delete(request, pk):
    """エントリー削除"""
    entry = get_object_or_404(Entry, pk=pk)
    competition = entry.race.competition
    
    # 権限チェック
    if request.user.organization:
        if entry.athlete.organization != request.user.organization:
            log_permission_denied(request, "entry delete - wrong organization")
            messages.error(request, '権限がありません。')
            return redirect('competitions:dashboard')
    else:
        if entry.athlete.user != request.user:
            log_permission_denied(request, "entry delete - wrong user")
            messages.error(request, '権限がありません。')
            return redirect('competitions:dashboard')
    
    # 確定済みは削除不可
    if entry.status == 'confirmed':
        messages.error(request, '確定済みのエントリーは削除できません。')
        return redirect('entries:cart', competition_pk=competition.pk)
    
    if request.method == 'POST':
        athlete_name = entry.athlete.full_name
        entry.delete()
        messages.success(request, f'{athlete_name}のエントリーを削除しました。')
        return redirect('entries:cart', competition_pk=competition.pk)
    
    return render(request, 'entries/entry_confirm_delete.html', {
        'entry': entry,
        'competition': competition,
    })


@login_required
@transaction.atomic
def entry_confirm(request, competition_pk):
    """エントリー確定（決済へ進む）"""
    competition = get_object_or_404(Competition, pk=competition_pk)
    user = request.user
    
    # 未確定のエントリーを取得
    if user.organization:
        entries = Entry.objects.filter(
            race__competition=competition,
            athlete__organization=user.organization,
            status='pending'
        ).select_related('athlete', 'race')
    else:
        entries = Entry.objects.filter(
            race__competition=competition,
            athlete__user=user,
            status='pending'
        ).select_related('athlete', 'race')
    
    if not entries.exists():
        messages.error(request, 'エントリーがありません。')
        return redirect('competitions:detail', pk=competition_pk)
    
    if request.method == 'POST':
        # エントリーグループを作成
        entry_group = EntryGroup.objects.create(
            organization=user.organization,
            competition=competition,
            registered_by=user,
            total_amount=entries.count() * competition.entry_fee
        )
        entry_group.entries.set(entries)
        
        # エントリーのステータスを更新
        entries.update(status='pending')
        
        messages.success(request, 'エントリー内容を確認しました。振込明細をアップロードしてください。')
        return redirect('payments:upload', entry_group_pk=entry_group.pk)
    
    total_amount = entries.count() * competition.entry_fee
    
    return render(request, 'entries/entry_confirm.html', {
        'competition': competition,
        'entries': entries,
        'total_amount': total_amount,
    })


@login_required
def entry_detail(request, pk):
    """エントリー詳細"""
    entry = get_object_or_404(Entry, pk=pk)
    
    # 権限チェック
    if not request.user.is_admin:
        if request.user.organization:
            if entry.athlete.organization != request.user.organization:
                log_permission_denied(request, "entry detail - wrong organization")
                messages.error(request, '権限がありません。')
                return redirect('competitions:dashboard')
        else:
            if entry.athlete.user != request.user:
                log_permission_denied(request, "entry detail - wrong user")
                messages.error(request, '権限がありません。')
                return redirect('competitions:dashboard')
    
    return render(request, 'entries/entry_detail.html', {
        'entry': entry,
    })


@login_required
def excel_template_download(request, competition_pk):
    """Excel一括エントリーテンプレートダウンロード"""
    competition = get_object_or_404(Competition, pk=competition_pk)
    
    template = generate_entry_template()
    
    response = HttpResponse(
        template.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="entry_template_{competition.pk}.xlsx"'
    
    return response


@login_required
def excel_upload(request, competition_pk):
    """Excel一括エントリーアップロード"""
    competition = get_object_or_404(Competition, pk=competition_pk)
    
    # エントリー可能かチェック
    if not competition.can_entry:
        messages.error(request, 'この大会は現在エントリーを受け付けていません。')
        return redirect('competitions:detail', pk=competition_pk)
    
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']
            importer = ExcelEntryImporter(competition, request.user)
            
            # プレビューモードか確定モードか
            if 'preview' in request.POST:
                try:
                    preview_result = importer.preview_from_file(excel_file)
                    return render(request, 'entries/excel_preview.html', {
                        'competition': competition,
                        'preview': preview_result,
                        'form': form,
                    })
                except ExcelImportError as e:
                    messages.error(request, str(e))
            else:
                # 確定モード
                try:
                    result = importer.import_from_file(excel_file)
                    
                    if result['success']:
                        messages.success(
                            request,
                            f'{result["success_count"]}件のエントリーを登録しました。'
                        )
                        if result['errors']:
                            for error in result['errors'][:5]:
                                messages.warning(request, error)
                            if len(result['errors']) > 5:
                                messages.warning(
                                    request,
                                    f'他に{len(result["errors"]) - 5}件のエラーがあります。'
                                )
                        return redirect('entries:cart', competition_pk=competition_pk)
                    else:
                        messages.error(request, 'エントリーに失敗しました。')
                        for error in result['errors'][:10]:
                            messages.error(request, error)
                except ExcelImportError as e:
                    messages.error(request, str(e))
    else:
        form = ExcelUploadForm()
    
    return render(request, 'entries/excel_upload.html', {
        'competition': competition,
        'form': form,
    })

