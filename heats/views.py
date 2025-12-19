"""
heats ビュー
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.utils import admin_required
from competitions.models import Competition, Race

from .models import Heat, HeatAssignment, HeatGenerator


@login_required
@admin_required
def heat_management(request, competition_pk):
    """番組編成管理"""
    competition = get_object_or_404(Competition, pk=competition_pk)
    races = competition.races.filter(is_active=True).order_by('display_order')
    
    return render(request, 'heats/heat_management.html', {
        'competition': competition,
        'races': races,
    })


@login_required
@admin_required
def heat_list(request, race_pk):
    """種目の組一覧"""
    race = get_object_or_404(
        Race.objects.select_related('competition'),
        pk=race_pk
    )
    heats = race.heats.prefetch_related(
        'assignments',
        'assignments__entry',
        'assignments__entry__athlete',
        'assignments__entry__athlete__organization'
    ).order_by('heat_number')
    
    return render(request, 'heats/heat_list.html', {
        'race': race,
        'heats': heats,
    })


@login_required
@admin_required
@require_POST
def generate_heats(request, race_pk):
    """組分け自動生成"""
    race = get_object_or_404(Race, pk=race_pk)
    
    force = request.POST.get('force', 'false') == 'true'
    
    # 既存の確定済み組があるかチェック
    if race.heats.filter(is_finalized=True).exists() and not force:
        messages.error(request, '確定済みの組が存在します。再生成する場合は強制オプションを使用してください。')
        return redirect('heats:list', race_pk=race_pk)
    
    try:
        heats = HeatGenerator.generate_heats(race, force_regenerate=True)
        messages.success(request, f'{len(heats)}組を生成しました。')
    except Exception as e:
        messages.error(request, f'組分け生成に失敗しました: {str(e)}')
    
    return redirect('heats:list', race_pk=race_pk)


@login_required
@admin_required
def heat_detail(request, pk):
    """組詳細"""
    heat = get_object_or_404(Heat, pk=pk)
    assignments = heat.assignments.select_related(
        'entry', 'entry__athlete', 'entry__athlete__organization'
    ).order_by('bib_number')
    
    return render(request, 'heats/heat_detail.html', {
        'heat': heat,
        'assignments': assignments,
    })


@login_required
@admin_required
@require_POST
def move_assignment(request):
    """選手の組移動（Ajax）"""
    assignment_id = request.POST.get('assignment_id')
    target_heat_id = request.POST.get('target_heat_id')
    new_bib = request.POST.get('new_bib_number')
    
    try:
        assignment = HeatAssignment.objects.get(pk=assignment_id)
        target_heat = Heat.objects.get(pk=target_heat_id)
        
        new_bib_number = int(new_bib) if new_bib else None
        
        HeatGenerator.move_entry(assignment, target_heat, new_bib_number)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@admin_required
@require_POST
def finalize_heat(request, pk):
    """組を確定"""
    heat = get_object_or_404(Heat, pk=pk)
    heat.is_finalized = True
    heat.save()
    
    messages.success(request, f'{heat}を確定しました。')
    return redirect('heats:list', race_pk=heat.race.pk)


@login_required
@admin_required
def checkin_search(request, competition_pk):
    """点呼・受付検索"""
    competition = get_object_or_404(Competition, pk=competition_pk)
    
    query = request.GET.get('q', '')
    results = []
    
    if query:
        # 氏名または所属で検索
        results = HeatAssignment.objects.filter(
            heat__race__competition=competition,
            heat__is_finalized=True
        ).filter(
            models.Q(entry__athlete__last_name__icontains=query) |
            models.Q(entry__athlete__first_name__icontains=query) |
            models.Q(entry__athlete__organization__name__icontains=query) |
            models.Q(entry__athlete__organization__short_name__icontains=query)
        ).select_related(
            'heat', 'heat__race', 'entry', 'entry__athlete', 'entry__athlete__organization'
        )[:50]
    
    return render(request, 'heats/checkin_search.html', {
        'competition': competition,
        'query': query,
        'results': results,
    })


@login_required
@admin_required
def checkin_dashboard(request, competition_pk):
    """リアルタイム点呼状況ダッシュボード"""
    competition = get_object_or_404(Competition, pk=competition_pk)
    
    # 各種目の点呼状況を取得
    races = []
    for race in competition.races.filter(is_active=True).order_by('display_order'):
        heats_data = []
        for heat in race.heats.filter(is_finalized=True).order_by('heat_number'):
            total = heat.assignments.count()
            checked_in = heat.assignments.filter(checked_in=True).count()
            dns = heat.assignments.filter(status='dns').count()
            pending = total - checked_in - dns
            
            heats_data.append({
                'heat': heat,
                'total': total,
                'checked_in': checked_in,
                'dns': dns,
                'pending': pending,
                'progress': round(checked_in / total * 100) if total > 0 else 0,
            })
        
        total_race = sum(h['total'] for h in heats_data)
        checked_in_race = sum(h['checked_in'] for h in heats_data)
        
        races.append({
            'race': race,
            'heats': heats_data,
            'total': total_race,
            'checked_in': checked_in_race,
            'progress': round(checked_in_race / total_race * 100) if total_race > 0 else 0,
        })
    
    return render(request, 'heats/checkin_dashboard.html', {
        'competition': competition,
        'races': races,
    })


@login_required
@admin_required
def checkin_status_api(request, competition_pk):
    """点呼状況API（リアルタイム更新用）"""
    competition = get_object_or_404(Competition, pk=competition_pk)
    
    data = []
    for race in competition.races.filter(is_active=True).order_by('display_order'):
        heats = []
        for heat in race.heats.filter(is_finalized=True).order_by('heat_number'):
            total = heat.assignments.count()
            checked_in = heat.assignments.filter(checked_in=True).count()
            dns = heat.assignments.filter(status='dns').count()
            
            # 未点呼選手リスト
            unchecked = heat.assignments.filter(
                checked_in=False
            ).exclude(status='dns').select_related(
                'entry__athlete', 'entry__athlete__organization'
            ).values(
                'pk',
                'bib_number',
                'entry__athlete__last_name',
                'entry__athlete__first_name',
                'entry__athlete__organization__short_name',
            )[:10]
            
            heats.append({
                'id': heat.pk,
                'number': heat.heat_number,
                'total': total,
                'checked_in': checked_in,
                'dns': dns,
                'pending': total - checked_in - dns,
                'progress': round(checked_in / total * 100) if total > 0 else 0,
                'unchecked': list(unchecked),
            })
        
        total_race = sum(h['total'] for h in heats)
        checked_in_race = sum(h['checked_in'] for h in heats)
        
        data.append({
            'race_id': race.pk,
            'race_name': race.name,
            'total': total_race,
            'checked_in': checked_in_race,
            'progress': round(checked_in_race / total_race * 100) if total_race > 0 else 0,
            'heats': heats,
        })
    
    return JsonResponse({'races': data})


@login_required
@admin_required
def checkin_stats_partial(request, competition_pk):
    """点呼状況統計パーシャル（htmx用）"""
    competition = get_object_or_404(Competition, pk=competition_pk)
    
    # 統計を計算
    total = 0
    checked_in = 0
    dns = 0
    
    for race in competition.races.filter(is_active=True):
        for heat in race.heats.filter(is_finalized=True):
            total += heat.assignments.count()
            checked_in += heat.assignments.filter(checked_in=True).count()
            dns += heat.assignments.filter(status='dns').count()
    
    pending = total - checked_in - dns
    progress = round(checked_in / total * 100) if total > 0 else 0
    
    stats = {
        'total': total,
        'checked_in': checked_in,
        'dns': dns,
        'pending': pending,
        'progress': progress,
    }
    
    return render(request, 'heats/partials/checkin_stats.html', {
        'stats': stats,
        'competition': competition,
    })


@login_required
@admin_required
@require_POST
def checkin(request, assignment_pk):
    """点呼チェックイン"""
    assignment = get_object_or_404(HeatAssignment, pk=assignment_pk)
    
    if not assignment.checked_in:
        assignment.checked_in = True
        assignment.checked_in_at = timezone.now()
        assignment.save()
        messages.success(request, f'{assignment.entry.athlete.full_name}の点呼を完了しました。')
    else:
        messages.info(request, f'{assignment.entry.athlete.full_name}は既に点呼済みです。')
    
    # リファラーに戻る
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('heats:checkin_search', competition_pk=assignment.heat.race.competition.pk)


@login_required
@admin_required
@require_POST
def mark_dns(request, assignment_pk):
    """欠場（DNS）マーク"""
    assignment = get_object_or_404(HeatAssignment, pk=assignment_pk)
    assignment.status = 'dns'
    assignment.save()
    
    # エントリーのステータスも更新
    assignment.entry.status = 'dns'
    assignment.entry.save()
    
    messages.warning(request, f'{assignment.entry.athlete.full_name}を欠場（DNS）としました。')
    
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('heats:detail', pk=assignment.heat.pk)


@login_required
@admin_required
@require_POST
def toggle_checkin(request, assignment_pk):
    """点呼トグル（HTMX部分更新対応）"""
    assignment = get_object_or_404(
        HeatAssignment.objects.select_related('entry__athlete'),
        pk=assignment_pk
    )
    
    # 状態をトグル
    if assignment.checked_in:
        assignment.checked_in = False
        assignment.checked_in_at = None
    else:
        assignment.checked_in = True
        assignment.checked_in_at = timezone.now()
    assignment.save()
    
    # HTMX用のパーシャルテンプレートを返す
    return render(request, 'heats/partials/checkin_toggle.html', {
        'assignment': assignment,
    })


@login_required
@admin_required
@require_POST
def generate_all_heats(request, competition_pk):
    """大会全体の組分けを生成（NCG処理を含む）"""
    competition = get_object_or_404(Competition, pk=competition_pk)
    
    force = request.POST.get('force', 'false') == 'true'
    
    try:
        result = HeatGenerator.generate_heats_with_ncg(competition, force_regenerate=force)
        
        # 結果メッセージ
        if result['ncg_processed']:
            for ncg in result['ncg_processed']:
                messages.info(
                    request,
                    f'{ncg["race"]}: NCG {ncg["ncg_count"]}名、一般種目へ移動 {ncg["moved_count"]}名'
                )
        
        if result['heats_generated']:
            total_heats = sum(h['heat_count'] for h in result['heats_generated'])
            messages.success(request, f'全{len(result["heats_generated"])}種目、計{total_heats}組を生成しました。')
        
        for error in result['errors']:
            messages.error(request, f'{error["race"]}: {error["error"]}')
            
    except Exception as e:
        messages.error(request, f'組分け生成に失敗しました: {str(e)}')
    
    return redirect('heats:management', competition_pk=competition_pk)


@login_required
@admin_required
@require_POST
def assign_bib_numbers(request, competition_pk):
    """大会全体のゼッケン番号を採番"""
    from .models import BibNumberGenerator
    
    competition = get_object_or_404(Competition, pk=competition_pk)
    
    try:
        result = BibNumberGenerator.assign_bib_numbers(competition)
        
        if result['assigned']:
            messages.success(
                request,
                f'{len(result["assigned"])}種目のゼッケン番号を採番しました。'
            )
            for assigned in result['assigned']:
                messages.info(
                    request,
                    f'{assigned["race"]}: {assigned["start_bib"]}〜{assigned["end_bib"]}'
                )
        
        for error in result.get('errors', []):
            messages.error(request, str(error))
            
    except Exception as e:
        messages.error(request, f'ゼッケン採番に失敗しました: {str(e)}')
    
    return redirect('heats:management', competition_pk=competition_pk)
