#!/bin/bash
#
# データベースバックアップスクリプト
# 使用方法: ./scripts/backup_db.sh
#

set -e

# 設定
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
PROJECT_DIR=$(dirname $(dirname $(realpath $0)))

# バックアップディレクトリ作成
mkdir -p "$BACKUP_DIR"

# 環境変数読み込み
if [ -f "$PROJECT_DIR/.env" ]; then
    source "$PROJECT_DIR/.env"
fi

echo "=== Nit-Sys データベースバックアップ ==="
echo "日時: $(date)"
echo ""

# SQLite バックアップ（開発環境）
if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
    SQLITE_BACKUP="$BACKUP_DIR/db_sqlite3_$TIMESTAMP.backup"
    echo "[SQLite] バックアップ開始..."
    cp "$PROJECT_DIR/db.sqlite3" "$SQLITE_BACKUP"
    echo "[SQLite] バックアップ完了: $SQLITE_BACKUP"
    
    # 古いバックアップを削除（30日以上前）
    find "$BACKUP_DIR" -name "db_sqlite3_*.backup" -mtime +30 -delete 2>/dev/null || true
    echo "[SQLite] 古いバックアップを削除しました"
fi

# PostgreSQL バックアップ（本番環境）
if [ -n "$DATABASE_URL" ]; then
    PG_BACKUP="$BACKUP_DIR/db_postgres_$TIMESTAMP.sql.gz"
    echo "[PostgreSQL] バックアップ開始..."
    
    # DATABASE_URL からパース
    # 形式: postgres://user:password@host:port/database
    if command -v pg_dump &> /dev/null; then
        pg_dump "$DATABASE_URL" | gzip > "$PG_BACKUP"
        echo "[PostgreSQL] バックアップ完了: $PG_BACKUP"
        
        # 古いバックアップを削除（30日以上前）
        find "$BACKUP_DIR" -name "db_postgres_*.sql.gz" -mtime +30 -delete 2>/dev/null || true
    else
        echo "[PostgreSQL] 警告: pg_dump がインストールされていません"
    fi
fi

# Django dumpdata バックアップ（JSON形式）
if [ -f "$PROJECT_DIR/manage.py" ]; then
    JSON_BACKUP="$BACKUP_DIR/data_$TIMESTAMP.json.gz"
    echo "[Django] dumpdata バックアップ開始..."
    
    cd "$PROJECT_DIR"
    source venv/bin/activate 2>/dev/null || true
    
    python manage.py dumpdata \
        --exclude auth.permission \
        --exclude contenttypes \
        --exclude sessions \
        --indent 2 | gzip > "$JSON_BACKUP"
    
    echo "[Django] dumpdata 完了: $JSON_BACKUP"
fi

echo ""
echo "=== バックアップ完了 ==="
echo "バックアップ先: $BACKUP_DIR"
ls -lh "$BACKUP_DIR" | tail -5
