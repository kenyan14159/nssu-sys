"""
reports ビュー
"""
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from accounts.utils import admin_required
from competitions.models import Competition, Race
from heats.models import Heat

from .generators import CSVGenerator, PDFGenerator, ResultSheetPDFGenerator
from .models import ReportLog


@login_required
@admin_required
def report_index(request, competition_pk):
    """帳票出力メニュー"""
    competition = get_object_or_404(Competition, pk=competition_pk)
    races = competition.races.filter(is_active=True).order_by('display_order')
    
    return render(request, 'reports/report_index.html', {
        'competition': competition,
        'races': races,
    })


@login_required
@admin_required
def download_startlist_csv(request, race_pk):
    """スタートリストCSVダウンロード"""
    race = get_object_or_404(Race, pk=race_pk)
    
    csv_content = CSVGenerator.generate_startlist_csv(race)
    
    # ログ記録
    ReportLog.objects.create(
        report_type='csv_startlist',
        competition=race.competition,
        race=race,
        generated_by=request.user
    )
    
    response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8-sig')
    filename = f"startlist_{race.competition.event_date}_{race.name}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@login_required
@admin_required
def download_all_data_csv(request, competition_pk):
    """全データCSVダウンロード"""
    competition = get_object_or_404(Competition, pk=competition_pk)
    
    csv_content = CSVGenerator.generate_all_data_csv(competition)
    
    # ログ記録
    ReportLog.objects.create(
        report_type='csv_startlist',
        competition=competition,
        generated_by=request.user
    )
    
    response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8-sig')
    filename = f"all_data_{competition.event_date}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@login_required
@admin_required
def download_rollcall_pdf(request, heat_pk):
    """点呼用PDFダウンロード"""
    heat = get_object_or_404(Heat, pk=heat_pk)
    
    pdf_buffer = PDFGenerator.generate_rollcall_pdf(heat)
    
    # ログ記録
    ReportLog.objects.create(
        report_type='pdf_rollcall',
        competition=heat.race.competition,
        race=heat.race,
        generated_by=request.user
    )
    
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    filename = f"rollcall_{heat.race.name}_{heat.heat_number}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@login_required
@admin_required
def download_program_pdf(request, race_pk):
    """プログラム原稿PDFダウンロード"""
    race = get_object_or_404(Race, pk=race_pk)
    
    pdf_buffer = PDFGenerator.generate_program_pdf(race)
    
    # ログ記録
    ReportLog.objects.create(
        report_type='pdf_program',
        competition=race.competition,
        race=race,
        generated_by=request.user
    )
    
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    filename = f"program_{race.competition.event_date}_{race.name}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@login_required
@admin_required
def download_all_data_pdf(request, competition_pk):
    """緊急用全データPDFダウンロード"""
    competition = get_object_or_404(Competition, pk=competition_pk)
    
    pdf_buffer = PDFGenerator.generate_all_data_pdf(competition)
    
    # ログ記録
    ReportLog.objects.create(
        report_type='pdf_all',
        competition=competition,
        generated_by=request.user
    )
    
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    filename = f"emergency_backup_{competition.event_date}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@login_required
@admin_required
def download_result_sheet_pdf(request, heat_pk):
    """結果記録用紙PDFダウンロード（1組分）"""
    heat = get_object_or_404(Heat, pk=heat_pk)
    
    pdf_buffer = ResultSheetPDFGenerator.generate_result_sheet_pdf(heat)
    
    # ログ記録
    ReportLog.objects.create(
        report_type='pdf_result_sheet',
        competition=heat.race.competition,
        race=heat.race,
        generated_by=request.user
    )
    
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    filename = f"result_sheet_{heat.race.name}_{heat.heat_number}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@login_required
@admin_required
def download_all_result_sheets_pdf(request, race_pk):
    """結果記録用紙PDF一括ダウンロード（全組）"""
    race = get_object_or_404(Race, pk=race_pk)
    
    pdf_buffer = ResultSheetPDFGenerator.generate_all_result_sheets_pdf(race)
    
    # ログ記録
    ReportLog.objects.create(
        report_type='pdf_result_sheet',
        competition=race.competition,
        race=race,
        generated_by=request.user
    )
    
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    filename = f"result_sheets_{race.competition.event_date}_{race.name}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response
