# 日本体育大学長距離競技会 エントリー・運営管理システム (Nit-Sys)

陸上競技会のエントリー受付から番組編成、帳票出力まで一元管理するWebアプリケーション。

## 機能概要

### ユーザー向け機能
- **団体・選手管理**: 団体登録、選手マスタ管理、Excel一括インポート
- **エントリー管理**: 複数種目・複数選手の一括エントリー、申告タイム入力
- **決済管理**: 銀行振込確認（振込明細画像アップロード）、領収書発行
- **駐車場申請**: 大型バス・中型バス・乗用車の駐車場希望申請

### 管理者向け機能
- **入金確認**: 振込明細画像の確認・承認、エントリー確定
- **自動番組編成**: 申告タイムに基づく組分け・腰ナンバー割り当て、NCG（NITTAI CHALLENGE GAMES）対応
- **ゼッケン番号採番**: 性別・NCG種目別の自動採番
- **帳票出力**: スタートリストCSV、点呼表PDF、プログラム原稿PDF、結果記録用紙PDF、駐車許可証PDF
- **当日点呼**: 組ごとの選手点呼管理

## 技術スタック

| カテゴリ | 技術 |
|---------|------|
| **Backend** | Django 4.2+ (Python 3.10+) |
| **Database** | PostgreSQL（本番）/ SQLite（開発） |
| **Frontend** | Bootstrap 5 |
| **管理画面** | Jazzmin (AdminLTEベース) |
| **API** | Django REST Framework |
| **PDF Generation** | ReportLab |
| **Data Processing** | Pandas, OpenPyXL |
| **Audit Log** | django-auditlog |
| **Rate Limiting** | django-ratelimit |
| **Static Files** | WhiteNoise |
| **Deployment** | Render / Railway |

## ローカル開発環境のセットアップ

### 前提条件

- Python 3.10+
- PostgreSQL 15+（またはSQLiteで代用可）
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
# SQLiteを使用する場合は USE_SQLITE=True を設定
```

5. マイグレーションを実行
```bash
python manage.py migrate
```

6. 管理者ユーザーを作成
```bash
python manage.py createsuperuser
```

7. 開発サーバーを起動
```bash
python manage.py runserver
```

ブラウザで http://localhost:8000 にアクセス

### テストの実行

```bash
# 全テスト実行
pytest

# カバレッジ付きで実行
pytest --cov

# 特定のアプリのテスト
pytest accounts/tests.py
```

### コード品質チェック

```bash
# Ruff（リンター・フォーマッター）
ruff check .
ruff format .

# セキュリティチェック
bandit -r .

# 依存パッケージの脆弱性チェック
pip-audit
```

## 本番環境へのデプロイ (Render)

1. GitHubリポジトリを作成してpush

2. Renderで「New Web Service」を作成
   - GitHubリポジトリを連携
   - `render.yaml`のBlueprintを使用

3. 環境変数を設定
   - `SECRET_KEY`: 自動生成
   - `DATABASE_URL`: PostgreSQLアドオンから自動設定
   - `ALLOWED_HOSTS`: `.onrender.com`
   - `DEBUG`: `False`

4. デプロイ完了後、初回のみ管理者作成
```bash
render exec python manage.py createsuperuser
```

## プロジェクト構成

```
nit-sys/
├── nitsys/              # Djangoプロジェクト設定
│   ├── settings.py      # 設定ファイル（Jazzmin、セキュリティ設定含む）
│   ├── urls.py          # URLルーティング
│   ├── views.py         # トップページ、管理者ガイド
│   ├── constants.py     # 共通定数・ユーティリティ関数
│   └── error_handlers.py # カスタムエラーハンドラー
├── accounts/            # ユーザー・団体・選手管理
│   ├── models.py        # User, Organization, Athlete
│   ├── views.py         # 登録、ログイン、選手管理
│   ├── forms.py         # フォーム定義
│   └── athlete_import.py # Excel一括インポート
├── competitions/        # 競技会・種目管理
│   ├── models.py        # Competition, Race
│   ├── views.py         # ダッシュボード、大会詳細
│   └── admin.py         # 管理画面カスタマイズ
├── entries/             # エントリー管理
│   ├── models.py        # Entry, EntryGroup
│   ├── views.py         # エントリー申込、確認
│   ├── forms.py         # エントリーフォーム
│   ├── api_views.py     # REST API
│   └── excel_import.py  # Excelエントリーインポート
├── payments/            # 決済・入金管理
│   ├── models.py        # Payment, BankAccount, ParkingRequest
│   ├── views.py         # 振込アップロード、管理者確認
│   ├── receipt_generator.py # 領収書PDF生成
│   └── parking_import.py # 駐車場割当CSVインポート
├── heats/               # 番組編成
│   ├── models.py        # Heat, HeatAssignment, HeatGenerator, BibNumberGenerator
│   ├── views.py         # 組編成画面、点呼
│   └── admin.py         # 管理画面カスタマイズ
├── reports/             # 帳票出力
│   ├── models.py        # ReportLog
│   ├── views.py         # 帳票ダウンロード
│   └── generators.py    # CSV/PDF生成ロジック
├── news/                # お知らせ
│   ├── models.py        # News
│   └── views.py         # お知らせ一覧・詳細
├── templates/           # HTMLテンプレート
│   ├── base.html        # 共通レイアウト
│   ├── index.html       # トップページ
│   ├── accounts/        # ユーザー関連テンプレート
│   ├── competitions/    # 大会関連テンプレート
│   ├── entries/         # エントリー関連テンプレート
│   ├── payments/        # 決済関連テンプレート
│   ├── heats/           # 番組編成関連テンプレート
│   └── admin/           # 管理画面カスタムテンプレート
├── static/              # 静的ファイル
│   ├── css/             # カスタムCSS
│   ├── js/              # カスタムJavaScript
│   └── images/          # ロゴ、ファビコン
├── docs/                # ドキュメント
├── tests/               # 追加テスト
├── scripts/             # 管理スクリプト
├── manage.py
├── requirements.txt     # 依存パッケージ
├── pyproject.toml       # Ruff、pytest設定
├── pytest.ini           # pytest設定
├── Procfile             # Render/Heroku用
└── render.yaml          # Render Blueprint
```

## 主要モデル

### accounts アプリ
| モデル | 説明 |
|--------|------|
| `User` | カスタムユーザー（メールアドレス認証、団体分類、管理者フラグ） |
| `Organization` | 団体（大学・クラブ・実業団、代表者情報、陸連登録コード） |
| `Athlete` | 選手マスタ（氏名、カナ、ローマ字、生年月日、陸連ID、国籍） |

### competitions アプリ
| モデル | 説明 |
|--------|------|
| `Competition` | 競技会（開催日、エントリー期間、参加費、公開設定） |
| `Race` | 種目（距離、性別区分、NCGフラグ、参加標準記録、開始予定時刻） |

### entries アプリ
| モデル | 説明 |
|--------|------|
| `Entry` | 個別エントリー（選手×種目、申告タイム、ステータス、NCG移動履歴） |
| `EntryGroup` | エントリーグループ（団体一括申込単位、決済管理） |

### payments アプリ
| モデル | 説明 |
|--------|------|
| `Payment` | 入金記録（振込明細画像、承認ステータス、確認者） |
| `BankAccount` | 振込先口座情報 |
| `ParkingRequest` | 駐車場申請（希望台数、割当結果、入出庫時間） |

### heats アプリ
| モデル | 説明 |
|--------|------|
| `Heat` | 組（組番号、開始予定時刻、確定フラグ） |
| `HeatAssignment` | 組編成（エントリー×組、腰ナンバー、ゼッケン番号、点呼状態） |
| `HeatGenerator` | 自動番組編成ロジック（クラスメソッド） |
| `BibNumberGenerator` | ゼッケン番号自動採番ロジック（クラスメソッド） |

### reports アプリ
| モデル | 説明 |
|--------|------|
| `ReportLog` | 帳票出力履歴 |

## 帳票出力機能

| 帳票種別 | 形式 | 用途 |
|----------|------|------|
| スタートリストCSV | CSV | FinishLynx/NISHI計測システム連携 |
| 点呼用リストPDF | PDF | 当日受付での手動チェック |
| プログラム原稿PDF | PDF | 大会プログラム作成用 |
| 結果記録用紙PDF | PDF | 陸連公式フォーマット準拠 |
| 駐車許可証PDF | PDF | 車両ダッシュボード掲示用 |
| 全データPDF | PDF | ネットワーク障害時の緊急バックアップ |

## NCG（NITTAI CHALLENGE GAMES）機能

NCG種目は上位選手のみを対象とした特別組です。

1. NCG種目にエントリー
2. エントリー締切後、申告タイム上位N名をNCG組に確定
3. N+1位以下の選手は自動的に一般種目に移動
4. 移動履歴は `Entry.moved_from_ncg` と `Entry.original_ncg_race` で追跡

## ゼッケン番号採番ルール

| 区分 | 番号範囲 |
|------|----------|
| NCG男子 | 1〜499 |
| NCG女子 | 500〜999 |
| 一般男子 | 1000〜1999 |
| 一般女子 | 2000〜2999 |
| 混合 | 3000〜 |

## API

REST APIはDjango REST Frameworkで実装。

### エンドポイント

| メソッド | パス | 説明 |
|----------|------|------|
| `GET` | `/api/athletes/` | 選手一覧 |
| `GET` | `/api/athletes/<id>/` | 選手詳細 |
| `POST` | `/api/entries/` | エントリー作成 |
| `GET` | `/api/entries/` | エントリー一覧 |

## UI/UX機能

- **レスポンシブデザイン**: モバイル対応サイドバー（オフキャンバス）
- **キーボードショートカット**: `G+D`（ダッシュボード）、`G+A`（選手管理）など
- **アクセシビリティ**: スキップリンク、ARIA属性、フォーカス表示改善
- **トースト通知**: 成功/エラー/情報の動的通知
- **テーブルソート**: クライアントサイドでの列ソート
- **二重送信防止**: ボタンローディング状態管理

## セキュリティ機能

- セッションアイドルタイムアウト（30分）
- セキュリティログ記録
- CSRF保護
- XSS対策
- django-ratelimitによるレート制限
- django-auditlogによる操作履歴記録

## ライセンス

MIT License

## 作者

日本体育大学陸上競技部
