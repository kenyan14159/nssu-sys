#!/bin/bash
#
# データベース復元スクリプト
# 使用方法: ./scripts/restore_db.sh <バックアップファイル>
#

set -e

BACKUP_FILE="$1"
PROJECT_DIR=$(dirname $(dirname $(realpath $0)))

if [ -z "$BACKUP_FILE" ]; then
    echo "使用方法: $0 <バックアップファイル>"
    echo ""
    echo "利用可能なバックアップ:"
    ls -lh ./backups/ 2>/dev/null || echo "バックアップが見つかりません"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "エラー: ファイルが見つかりません: $BACKUP_FILE"
    exit 1
fi

echo "=== Nit-Sys データベース復元 ==="
echo "復元元: $BACKUP_FILE"
echo ""

read -p "本当に復元しますか？現在のデータは上書きされます。(y/N): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "キャンセルしました"
    exit 0
fi

# ファイル形式に応じた復元
case "$BACKUP_FILE" in
    *.backup)
        echo "[SQLite] 復元中..."
        cp "$BACKUP_FILE" "$PROJECT_DIR/db.sqlite3"
        echo "[SQLite] 復元完了"
        ;;
    *.sql.gz)
        echo "[PostgreSQL] 復元中..."
        if [ -n "$DATABASE_URL" ]; then
            gunzip -c "$BACKUP_FILE" | psql "$DATABASE_URL"
            echo "[PostgreSQL] 復元完了"
        else
            echo "エラー: DATABASE_URL が設定されていません"
            exit 1
        fi
        ;;
    *.json.gz)
        echo "[Django] loaddata 復元中..."
        cd "$PROJECT_DIR"
        source venv/bin/activate 2>/dev/null || true
        
        # まずデータベースをリセット
        python manage.py flush --no-input
        
        # データを復元
        gunzip -c "$BACKUP_FILE" | python manage.py loaddata --format=json -
        echo "[Django] 復元完了"
        ;;
    *)
        echo "エラー: 不明なファイル形式です"
        exit 1
        ;;
esac

echo ""
echo "=== 復元完了 ==="
