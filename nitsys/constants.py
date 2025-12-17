"""
大会設定値 (Constants)
第325回大会固有の定数および参加標準記録
"""

# 参加標準記録（秒単位）
# 申告タイムがこれより遅い場合はエントリーをブロック
STANDARD_LIMITS = {
    'M_5000': 930.00,    # 15:30.00
    'M_10000': 1860.00,  # 31:00.00
    'F_3000': 660.00,    # 11:00.00
    'F_5000': 1110.00,   # 18:30.00
}

# NCG定員
NCG_CAPACITY = 35

# 振込先口座情報（表示用）
BANK_ACCOUNT = {
    'bank': 'ゆうちょ銀行',
    'branch_name': '〇二八店 (028)',
    'type': '普通',
    'number': '8327055',
    'holder': '日本体育大学長距離ブロック',
    'holder_kana': 'ニホンタイイクダイガクチョウキョリブロック',
}

# 参加費（円）
ENTRY_FEE = 2000

# 1組あたりのデフォルト定員
DEFAULT_HEAT_CAPACITY = 40


def get_standard_limit_key(gender: str, distance: int) -> str:
    """
    性別と距離から標準記録キーを生成
    
    Args:
        gender: 'M' or 'F'
        distance: 距離（メートル）
    
    Returns:
        標準記録キー（例: 'M_5000'）
    """
    return f"{gender}_{distance}"


def get_standard_limit(gender: str, distance: int) -> float | None:
    """
    種目に対応する参加標準記録を取得
    
    Args:
        gender: 'M' or 'F'
        distance: 距離（メートル）
    
    Returns:
        標準記録（秒）。設定がない場合はNone
    """
    key = get_standard_limit_key(gender, distance)
    return STANDARD_LIMITS.get(key)


def format_time(seconds: float) -> str:
    """
    秒数を MM:SS.cc 形式に変換
    
    Args:
        seconds: 秒数（例: 930.00）
    
    Returns:
        フォーマット済み文字列（例: '15:30.00'）
    """
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}:{secs:05.2f}"


def parse_time(time_str: str) -> float:
    """
    MM:SS.cc 形式を秒数に変換
    
    Args:
        time_str: タイム文字列（例: '15:30.00'）
    
    Returns:
        秒数（例: 930.00）
    """
    parts = time_str.split(':')
    if len(parts) == 2:
        minutes = int(parts[0])
        seconds = float(parts[1])
        return minutes * 60 + seconds
    raise ValueError(f"Invalid time format: {time_str}")
