"""
entries API ビュー

OpenAPI/Swagger 対応 API ドキュメント
各エンドポイントは以下の形式で提供されます:
- GET /api/athletes/ - 選手一覧取得
- GET /api/entries/ - エントリー一覧取得
- GET /api/assignments/<pk>/ - 選手詳細取得（組編成情報付き）
"""
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Athlete
from heats.models import HeatAssignment

from .models import Entry


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def athlete_list(request):
    """
    選手一覧を取得するAPI
    
    ## リクエストパラメータ
    - `gender` (optional): 性別フィルタ ('M' または 'F')
    
    ## レスポンス
    ```json
    [
        {
            "id": 1,
            "full_name": "鈴木一郎",
            "full_name_kana": "スズキイチロウ",
            "gender": "M",
            "organization": "テスト大学"
        }
    ]
    ```
    
    ## エラーレスポンス
    - 401: 認証が必要です
    """
    user = request.user
    
    if user.organization:
        athletes = Athlete.objects.filter(
            organization=user.organization,
            is_active=True
        ).select_related('organization')
    else:
        athletes = Athlete.objects.filter(
            user=user,
            is_active=True
        )
    
    # 性別フィルタ
    gender = request.GET.get('gender')
    if gender and gender in ['M', 'F']:
        athletes = athletes.filter(gender=gender)
    
    data = [{
        'id': a.id,
        'full_name': a.full_name,
        'full_name_kana': a.full_name_kana,
        'gender': a.gender,
        'organization': a.organization.name if a.organization else None,
    } for a in athletes]
    
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def entry_list(request):
    """
    エントリー一覧を取得するAPI
    
    ## リクエストパラメータ
    - `competition` (optional): 大会IDでフィルタ
    - `status` (optional): ステータスでフィルタ ('pending', 'confirmed', 'cancelled')
    
    ## レスポンス
    ```json
    [
        {
            "id": 1,
            "athlete": "鈴木一郎",
            "athlete_id": 1,
            "race": "男子5000m",
            "race_id": 1,
            "competition": "第100回日体大記録会",
            "competition_id": 1,
            "declared_time": "14:30.00",
            "declared_time_seconds": 870.0,
            "status": "pending",
            "status_display": "申込中（入金待ち）"
        }
    ]
    ```
    
    ## エラーレスポンス
    - 401: 認証が必要です
    """
    user = request.user
    competition_id = request.GET.get('competition')
    entry_status = request.GET.get('status')
    
    if user.organization:
        entries = Entry.objects.filter(
            athlete__organization=user.organization
        )
    else:
        entries = Entry.objects.filter(
            athlete__user=user
        )
    
    if competition_id:
        entries = entries.filter(race__competition_id=competition_id)
    
    if entry_status:
        entries = entries.filter(status=entry_status)
    
    entries = entries.select_related(
        'athlete',
        'athlete__organization',
        'race',
        'race__competition'
    )
    
    data = [{
        'id': e.id,
        'athlete': e.athlete.full_name,
        'athlete_id': e.athlete.id,
        'race': e.race.name,
        'race_id': e.race.id,
        'competition': e.race.competition.name,
        'competition_id': e.race.competition.id,
        'declared_time': e.declared_time_display,
        'declared_time_seconds': float(e.declared_time),
        'status': e.status,
        'status_display': e.get_status_display(),
    } for e in entries]
    
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def assignment_detail(request, pk):
    """
    選手詳細を取得するAPI（組編成情報付き）
    
    ## パスパラメータ
    - `pk`: HeatAssignment ID
    
    ## レスポンス
    ```json
    {
        "athlete": {
            "full_name": "鈴木一郎",
            "full_name_kana": "スズキ イチロウ",
            "organization": "テスト大学",
            "organization_short": "テスト大",
            "gender": "男子",
            "birth_date": "2000-01-01",
            "nationality": "JPN",
            "registered_pref": "東京",
            "jaaf_id": "12345678"
        },
        "entry": {
            "declared_time": "14:30.00",
            "personal_best": "14:00.00",
            "status": "確定",
            "note": ""
        },
        "heat": {
            "race": "男子5000m",
            "race_id": 1,
            "heat_number": 1,
            "bib_number": 5,
            "race_bib_number": 1005,
            "checked_in": false,
            "checked_in_at": null
        }
    }
    ```
    
    ## エラーレスポンス
    - 401: 認証が必要です
    - 404: 組編成が見つかりません
    """
    assignment = get_object_or_404(
        HeatAssignment.objects.select_related(
            'entry__athlete__organization',
            'entry__race',
            'heat__race__competition'
        ),
        pk=pk
    )
    
    athlete = assignment.entry.athlete
    entry = assignment.entry
    
    # 自己ベストの表示形式変換
    personal_best_display = None
    if entry.personal_best:
        personal_best_display = Entry.seconds_to_time(float(entry.personal_best))
    
    data = {
        'athlete': {
            'full_name': athlete.full_name,
            'full_name_kana': athlete.full_name_kana,
            'organization': athlete.organization.name if athlete.organization else '個人',
            'organization_short': athlete.organization.short_name if athlete.organization else '個人',
            'gender': athlete.get_gender_display(),
            'birth_date': athlete.birth_date.strftime('%Y-%m-%d') if athlete.birth_date else None,
            'nationality': athlete.nationality,
            'registered_pref': athlete.registered_pref,
            'jaaf_id': athlete.jaaf_id,
        },
        'entry': {
            'declared_time': entry.declared_time_display,
            'personal_best': personal_best_display,
            'status': entry.get_status_display(),
            'note': entry.note,
        },
        'heat': {
            'race': assignment.heat.race.name,
            'race_id': assignment.heat.race.id,
            'heat_number': assignment.heat.heat_number,
            'bib_number': assignment.bib_number,
            'race_bib_number': assignment.race_bib_number,
            'checked_in': assignment.checked_in,
            'checked_in_at': assignment.checked_in_at.isoformat() if assignment.checked_in_at else None,
        },
        'recent_entries': [],  # エントリー履歴
    }
    
    # 最近のエントリー履歴（同選手の他エントリー、最新5件）
    recent_entries = Entry.objects.filter(
        athlete=athlete
    ).exclude(
        pk=entry.pk
    ).select_related(
        'race', 'race__competition'
    ).order_by('-race__competition__event_date')[:5]
    
    for e in recent_entries:
        data['recent_entries'].append({
            'competition': e.race.competition.name,
            'race': e.race.name,
            'declared_time': e.declared_time_display,
            'status': e.get_status_display(),
            'event_date': e.race.competition.event_date.strftime('%Y/%m/%d') if e.race.competition.event_date else None,
        })
    
    return Response(data)
