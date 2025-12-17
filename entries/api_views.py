"""
entries API ビュー

OpenAPI/Swagger 対応 API ドキュメント
各エンドポイントは以下の形式で提供されます:
- GET /api/athletes/ - 選手一覧取得
- GET /api/entries/ - エントリー一覧取得
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Athlete

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
