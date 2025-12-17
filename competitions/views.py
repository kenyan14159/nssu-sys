"""
competitions ビュー
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from entries.models import Entry, EntryGroup
from news.models import News

from .models import Competition


@login_required
def dashboard(request):
    """ダッシュボード"""
    user = request.user
    now = timezone.now()
    
    # 開催予定の大会（公開中のもの）- N+1解消
    upcoming_competitions = Competition.objects.filter(
        is_published=True,
        event_date__gte=now.date()
    ).prefetch_related('races').order_by('event_date')[:5]
    
    # ユーザーのエントリー情報
    if user.organization:
        # 団体の場合 - N+1解消
        entry_groups = EntryGroup.objects.filter(
            organization=user.organization
        ).select_related(
            'competition', 'organization'
        ).prefetch_related('entries').order_by('-created_at')[:5]
        
        entries = Entry.objects.filter(
            athlete__organization=user.organization
        ).select_related(
            'athlete',
            'athlete__organization',
            'race',
            'race__competition'
        ).order_by('-created_at')[:10]
    else:
        # 個人の場合 - N+1解消
        entry_groups = EntryGroup.objects.filter(
            registered_by=user
        ).select_related(
            'competition'
        ).prefetch_related('entries').order_by('-created_at')[:5]
        
        entries = Entry.objects.filter(
            athlete__user=user
        ).select_related(
            'athlete',
            'race',
            'race__competition'
        ).order_by('-created_at')[:10]
    
    # お知らせ（最新5件）
    news_items = News.get_active_news(limit=5)
    
    context = {
        'upcoming_competitions': upcoming_competitions,
        'entry_groups': entry_groups,
        'recent_entries': entries,
        'news_items': news_items,
    }
    
    return render(request, 'competitions/dashboard.html', context)


@login_required
def competition_list(request):
    """大会一覧"""
    now = timezone.now()
    
    # 公開中の大会のみ表示（管理者は全て表示）
    if request.user.is_admin:
        competitions = Competition.objects.all()
    else:
        competitions = Competition.objects.filter(is_published=True)
    
    # 開催予定・開催済みで分類
    upcoming = competitions.filter(event_date__gte=now.date()).order_by('event_date')
    past = competitions.filter(event_date__lt=now.date()).order_by('-event_date')[:10]
    
    return render(request, 'competitions/competition_list.html', {
        'upcoming_competitions': upcoming,
        'past_competitions': past,
    })


@login_required
def competition_detail(request, pk):
    """大会詳細"""
    competition = get_object_or_404(Competition, pk=pk)
    
    # 非公開の大会は管理者のみ
    if not competition.is_published and not request.user.is_admin:
        messages.error(request, 'この大会は公開されていません。')
        return redirect('competitions:list')
    
    # 種目一覧（エントリー数付き）
    races = competition.races.filter(is_active=True).annotate(
        confirmed_count=Count('entries', filter=Q(entries__status='confirmed'))
    ).order_by('display_order')
    
    return render(request, 'competitions/competition_detail.html', {
        'competition': competition,
        'races': races,
    })


@login_required
def entry_history(request):
    """エントリー履歴"""
    user = request.user
    
    if user.organization:
        entries = Entry.objects.filter(
            athlete__organization=user.organization
        ).select_related(
            'athlete', 'race', 'race__competition'
        ).order_by('-race__competition__event_date', '-created_at')
    else:
        entries = Entry.objects.filter(
            athlete__user=user
        ).select_related(
            'athlete', 'race', 'race__competition'
        ).order_by('-race__competition__event_date', '-created_at')
    
    return render(request, 'competitions/entry_history.html', {
        'entries': entries,
    })


def admin_required(view_func):
    """管理者権限チェックデコレータ"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_admin:
            messages.error(request, '管理者権限が必要です。')
            return redirect('competitions:dashboard')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


@admin_required
def admin_competition_select(request):
    """管理者用：大会選択（番組編成用）"""
    competitions = Competition.objects.filter(
        is_published=True
    ).order_by('-event_date')
    
    return render(request, 'competitions/admin_competition_select.html', {
        'competitions': competitions,
        'action_type': 'heats',
        'page_title': '番組編成',
        'page_icon': 'bi-diagram-3',
    })


@admin_required
def admin_report_select(request):
    """管理者用：大会選択（帳票出力用）"""
    competitions = Competition.objects.filter(
        is_published=True
    ).order_by('-event_date')
    
    return render(request, 'competitions/admin_competition_select.html', {
        'competitions': competitions,
        'action_type': 'reports',
        'page_title': '帳票出力',
        'page_icon': 'bi-file-earmark-text',
    })


@admin_required
def admin_checkin_select(request):
    """管理者用：大会選択（当日点呼用）"""
    competitions = Competition.objects.filter(
        is_published=True
    ).order_by('-event_date')
    
    return render(request, 'competitions/admin_competition_select.html', {
        'competitions': competitions,
        'action_type': 'checkin',
        'page_title': '当日点呼',
        'page_icon': 'bi-person-check',
    })
