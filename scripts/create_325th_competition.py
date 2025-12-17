"""
第325回日本体育大学長距離競技会のテストデータ作成スクリプト
各組40名でHeatsを作成
"""
import os
import sys

import django

# Django設定
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nitsys.settings')
django.setup()

from datetime import date, datetime, time

from django.utils import timezone

from competitions.models import Competition, Race
from heats.models import Heat

# 大会データ
COMPETITION_DATA = {
    'name': '第325回日本体育大学長距離競技会',
    'event_date': date(2025, 7, 29),
    'venue': '日本体育大学横浜・健志台キャンパス陸上競技場',
    'entry_fee': 1000,
    'default_heat_capacity': 40,
}

# 種目と組データ（開催日7月29日）
# フォーマット: (種目名, 性別, 距離, [(組番号, 開始時刻), ...])
RACE_DATA = [
    # 男子10000m（1日目前半）
    ('男子10000m', 'M', 10000, [
        (1, '07:30'), (2, '08:04'), (3, '08:38'), (4, '09:12'),
        (5, '09:46'), (6, '10:19'), (7, '10:52'), (8, '11:25'),
    ]),
    # 男子10000m（1日目後半）
    ('男子10000m', 'M', 10000, [
        (9, '15:54'), (10, '16:27'), (11, '17:00'), (12, '17:32'),
        (13, '18:04'), (14, '18:36'),
    ]),
    # 女子3000m
    ('女子3000m', 'F', 3000, [
        (1, '12:00'), (2, '12:13'), (3, '12:26'), (4, '12:39'),
        (5, '12:52'), (6, '13:05'), (7, '13:17'),
    ]),
    # 女子5000m
    ('女子5000m', 'F', 5000, [
        (1, '13:29'), (2, '13:49'), (3, '14:09'), (4, '14:28'), (5, '14:47'),
    ]),
    # NCG女子3000m
    ('NCG女子3000m', 'F', 3000, [
        (1, '15:06'),
    ]),
    # NCG女子5000m
    ('NCG女子5000m', 'F', 5000, [
        (1, '15:18'), (2, '15:36'),
    ]),
    # NCG男子10000m
    ('NCG男子10000m', 'M', 10000, [
        (1, '19:08'), (2, '19:40'),
    ]),
    # 男子5000m
    ('男子5000m', 'M', 5000, [
        (1, '09:40'), (2, '09:59'), (3, '10:18'), (4, '10:37'), (5, '10:56'),
        (6, '11:15'), (7, '11:33'), (8, '11:51'), (9, '12:09'), (10, '12:27'),
        (11, '12:45'), (12, '13:03'), (13, '13:21'), (14, '13:39'), (15, '13:57'),
        (16, '14:15'), (17, '14:33'), (18, '14:51'), (19, '15:09'), (20, '15:27'),
        (21, '15:45'), (22, '16:03'), (23, '16:21'), (24, '16:38'), (25, '16:55'),
        (26, '17:12'), (27, '17:29'), (28, '17:46'), (29, '18:03'), (30, '18:20'),
        (31, '18:37'), (32, '18:54'), (33, '19:11'), (34, '19:28'),
    ]),
    # NCG男子5000m
    ('NCG男子5000m', 'M', 5000, [
        (1, '19:45'),
    ]),
]

def parse_time(time_str):
    """時刻文字列をtimeオブジェクトに変換"""
    parts = time_str.split(':')
    return time(int(parts[0]), int(parts[1]))

def create_competition_data():
    """大会・種目・組データを作成"""
    
    # エントリー期間設定（大会1ヶ月前から1週間前まで）
    event_date = COMPETITION_DATA['event_date']
    entry_start = timezone.make_aware(datetime(event_date.year, event_date.month - 1, event_date.day, 0, 0))
    entry_end = timezone.make_aware(datetime(event_date.year, event_date.month, event_date.day - 7, 23, 59))
    
    # 大会作成
    competition, created = Competition.objects.update_or_create(
        name=COMPETITION_DATA['name'],
        defaults={
            'event_date': event_date,
            'venue': COMPETITION_DATA['venue'],
            'entry_start_at': entry_start,
            'entry_end_at': entry_end,
            'entry_fee': COMPETITION_DATA['entry_fee'],
            'default_heat_capacity': COMPETITION_DATA['default_heat_capacity'],
            'is_published': True,
            'is_entry_open': True,
        }
    )
    
    if created:
        print(f"✅ 大会作成: {competition.name}")
    else:
        print(f"🔄 大会更新: {competition.name}")
    
    # 種目作成
    display_order = 0
    race_cache = {}  # 種目名でキャッシュ
    
    for race_name, gender, distance, heats_data in RACE_DATA:
        display_order += 1
        
        # NCGは別種目として扱う
        is_ncg = race_name.startswith('NCG')
        
        # 種目を取得または作成
        if race_name not in race_cache:
            # 同じ種目が既に作成されているか確認
            existing_races = Race.objects.filter(
                competition=competition,
                name=race_name
            )
            
            if existing_races.exists():
                race = existing_races.first()
                print(f"  🔄 種目更新: {race_name}")
            else:
                race = Race.objects.create(
                    competition=competition,
                    distance=distance,
                    gender=gender,
                    name=race_name,
                    heat_capacity=40,
                    max_entries=len(heats_data) * 40,
                    display_order=display_order,
                    is_active=True,
                )
                print(f"  ✅ 種目作成: {race_name}")
            
            race_cache[race_name] = race
        else:
            race = race_cache[race_name]
        
        # 組データ作成
        for heat_number, start_time_str in heats_data:
            start_time = parse_time(start_time_str)
            
            heat, heat_created = Heat.objects.update_or_create(
                race=race,
                heat_number=heat_number,
                defaults={
                    'scheduled_start_time': start_time,
                    'is_finalized': False,
                }
            )
            
            if heat_created:
                print(f"    ✅ 組作成: {race_name} {heat_number}組 ({start_time_str})")
    
    # サマリー出力
    print("\n" + "="*60)
    print("📊 作成データサマリー")
    print("="*60)
    print(f"大会: {competition.name}")
    print(f"開催日: {competition.event_date}")
    print(f"種目数: {Race.objects.filter(competition=competition).count()}")
    print(f"総組数: {Heat.objects.filter(race__competition=competition).count()}")
    
    # 種目ごとの組数
    print("\n種目別組数:")
    for race in Race.objects.filter(competition=competition).order_by('display_order'):
        heat_count = race.heats.count()
        total_capacity = heat_count * race.heat_capacity
        print(f"  - {race.name}: {heat_count}組 (定員計: {total_capacity}名)")
    
    return competition

if __name__ == '__main__':
    print("="*60)
    print("第325回日本体育大学長距離競技会 データ作成")
    print("="*60)
    create_competition_data()
    print("\n✅ データ作成完了!")
