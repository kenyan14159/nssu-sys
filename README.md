# 日本体育大学長距離競技会 エントリー・運営管理システム (Nit-Sys)

陸上競技会のエントリー受付から番組編成まで一元管理するWebアプリケーション。

## 機能概要

- **ユーザー管理**: 団体登録、選手マスタ管理
- **エントリー管理**: 複数種目・複数選手の一括エントリー
- **決済管理**: 銀行振込確認（振込明細画像アップロード）
- **自動番組編成**: 申告タイムに基づく組分け・レーン割り当て
- **帳票出力**: スタートリストCSV、点呼表PDF、緊急用バックアップPDF

## 技術スタック

- **Backend**: Django 4.2+
- **Database**: PostgreSQL
- **Frontend**: Bootstrap 5
- **PDF Generation**: ReportLab
- **CSV Export**: Pandas
- **Deployment**: Render / Railway

## ローカル開発環境のセットアップ

### 前提条件

- Python 3.11+
- PostgreSQL 15+
- Git

### 手順

1. リポジトリをクローン
```bash
git clone https://github.com/yourusername/nit-sys.git
cd nit-sys
```

2. 仮想環境を作成
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 依存パッケージをインストール
```bash
pip install -r requirements.txt
```

4. 環境変数を設定
```bash
cp .env.example .env
# .envファイルを編集して適切な値を設定
```

5. PostgreSQLデータベースを作成
```bash
createdb nitsys
```

6. マイグレーションを実行
```bash
python manage.py migrate
```

7. 管理者ユーザーを作成
```bash
python manage.py createsuperuser
```

8. 開発サーバーを起動
```bash
python manage.py runserver
```

ブラウザで http://localhost:8000 にアクセス

## 本番環境へのデプロイ (Render)

1. GitHubリポジトリを作成してpush

2. Renderで「New Web Service」を作成
   - GitHubリポジトリを連携
   - `render.yaml`のBlueprintを使用

3. 環境変数を設定
   - `SECRET_KEY`: 自動生成
   - `DATABASE_URL`: PostgreSQLアドオンから自動設定
   - `ALLOWED_HOSTS`: `.onrender.com`

4. デプロイ完了後、初回のみ管理者作成
```bash
render exec python manage.py createsuperuser
```

## プロジェクト構成

```
nit-sys/
├── nitsys/              # Djangoプロジェクト設定
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/            # ユーザー・団体・選手管理
├── competitions/        # 競技会・種目管理
├── entries/             # エントリー管理
├── payments/            # 決済管理
├── heats/               # 番組編成・受付
├── reports/             # 帳票出力
├── templates/           # HTMLテンプレート
├── static/              # CSS/JS
├── manage.py
├── requirements.txt
├── Procfile             # Heroku/Render用
└── render.yaml          # Render Blueprint
```

## 主要モデル

### accounts アプリ
- `User` - カスタムユーザー（メールアドレス認証）
- `Organization` - 団体（大学・クラブ）
- `Athlete` - 選手マスタ

### competitions アプリ
- `Competition` - 競技会
- `Race` - 種目（距離・開始時刻など）

### entries アプリ
- `EntryGroup` - エントリーグループ（決済単位）
- `Entry` - 個別エントリー

### payments アプリ
- `Payment` - 決済記録
- `PaymentProof` - 振込証明画像

### heats アプリ
- `Heat` - 組
- `HeatAssignment` - 組割り当て（レーン割り当て含む）
- `HeatGenerator` - 番組自動生成履歴

### reports アプリ
- `ReportLog` - 帳票出力履歴

## API

REST APIはDjango REST Frameworkで実装。

### エンドポイント

- `GET /api/athletes/` - 選手一覧
- `GET /api/athletes/<id>/` - 選手詳細
- `POST /api/entries/` - エントリー作成
- `GET /api/entries/` - エントリー一覧

## ライセンス

MIT License

## 作者

日本体育大学陸上競技部
