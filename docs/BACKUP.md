# データベースバックアップ戦略

## 概要

日体大長距離競技会エントリーシステム（Nit-Sys）のデータ保護のためのバックアップ戦略を定義します。

## 1. Renderの自動バックアップ

### Point-in-Time Recovery (PITR)

Renderが提供するPostgreSQLデータベースには、自動的にPITRが有効になっています。

- **保持期間**: 7日間（Standard Plan以上）
- **復旧粒度**: 1秒単位
- **設定場所**: Render Dashboard → Database → Backups

### 手動バックアップの取得

```bash
# Renderダッシュボードから接続情報を取得
PGPASSWORD=your_password pg_dump \
  -h your-host.render.com \
  -U your_user \
  -d your_database \
  -F c \
  -f backup_$(date +%Y%m%d_%H%M%S).dump
```

## 2. 推奨するバックアップスケジュール

| タイミング | バックアップ種別 | 保持期間 |
|-----------|-----------------|---------|
| 毎日 | 自動（PITR） | 7日 |
| 大会前日 | 手動フルバックアップ | 1ヶ月 |
| 大会終了後 | アーカイブバックアップ | 永続 |

## 3. 障害復旧手順

### 3.1 特定時点への復旧（PITR）

1. Render Dashboard → Database → Backups
2. 「Restore to point in time」を選択
3. 復旧したい日時を指定
4. 新しいデータベースインスタンスとして復旧
5. アプリケーションの環境変数を更新

### 3.2 手動バックアップからの復旧

```bash
# バックアップファイルから復旧
pg_restore \
  -h your-host.render.com \
  -U your_user \
  -d your_database \
  -c \
  backup_file.dump
```

## 4. 重要な注意事項

> [!CAUTION]
> 大会当日のデータは特に重要です。大会開始前に必ず手動バックアップを取得してください。

> [!TIP]
> 本番デプロイ前にステージング環境でバックアップ・リストア手順をテストすることを推奨します。

## 5. 連絡先

データ障害発生時の緊急連絡先:
- Render Support: support@render.com
- システム管理者: [要設定]
