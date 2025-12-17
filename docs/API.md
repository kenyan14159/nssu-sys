# Nit-Sys API ドキュメント

## 概要

Nit-Sys（日本体育大学長距離競技会 エントリー・運営管理システム）のREST API仕様書です。

## 認証

すべてのAPIエンドポイントは認証が必要です。セッション認証を使用しています。

```
Cookie: sessionid=<session_id>
```

## 共通レスポンス

### 成功時
```json
{
    "data": [...],
    "status": "success"
}
```

### エラー時
```json
{
    "error": "エラーメッセージ",
    "status": "error"
}
```

## HTTPステータスコード

| コード | 説明 |
|--------|------|
| 200 | 成功 |
| 201 | 作成成功 |
| 400 | リクエストエラー |
| 401 | 認証エラー |
| 403 | 権限エラー |
| 404 | リソースが見つからない |
| 429 | レート制限超過 |
| 500 | サーバーエラー |

---

## エンドポイント一覧

### 選手 (Athletes)

#### 選手一覧取得

```
GET /api/athletes/
```

**パラメータ:**
| 名前 | 型 | 必須 | 説明 |
|------|-----|------|------|
| gender | string | No | 性別フィルタ ('M' または 'F') |

**レスポンス:**
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

---

### エントリー (Entries)

#### エントリー一覧取得

```
GET /api/entries/
```

**パラメータ:**
| 名前 | 型 | 必須 | 説明 |
|------|-----|------|------|
| competition | integer | No | 大会IDでフィルタ |
| status | string | No | ステータスでフィルタ |

**ステータス値:**
- `pending` - 申込中（入金待ち）
- `payment_uploaded` - 入金確認待ち
- `confirmed` - 確定
- `cancelled` - キャンセル
- `dns` - 欠場

**レスポンス:**
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

---

### 組編成 (Heats)

#### 選手の組移動

```
POST /heats/api/move/
```

**リクエストボディ:**
```json
{
    "assignment_id": 1,
    "target_heat_id": 2,
    "new_bib_number": 5
}
```

**レスポンス:**
```json
{
    "success": true
}
```

**エラーレスポンス:**
```json
{
    "success": false,
    "error": "エラーメッセージ"
}
```

---

## レート制限

ログインAPIには以下のレート制限が適用されます：

- **ログイン**: 5回/分（IPアドレスあたり）

制限超過時は `429 Too Many Requests` が返されます。

---

## 使用例

### cURLでの例

```bash
# ログイン
curl -X POST https://example.com/accounts/login/ \
  -d "username=user@example.com&password=password" \
  -c cookies.txt

# 選手一覧取得
curl -X GET https://example.com/api/athletes/ \
  -b cookies.txt

# エントリー一覧取得（大会IDでフィルタ）
curl -X GET "https://example.com/api/entries/?competition=1" \
  -b cookies.txt
```

### JavaScriptでの例

```javascript
// 選手一覧取得
async function getAthletes() {
    const response = await fetch('/api/athletes/', {
        method: 'GET',
        credentials: 'include'
    });
    return response.json();
}

// エントリー一覧取得
async function getEntries(competitionId) {
    const url = new URL('/api/entries/', window.location.origin);
    if (competitionId) {
        url.searchParams.set('competition', competitionId);
    }
    const response = await fetch(url, {
        method: 'GET',
        credentials: 'include'
    });
    return response.json();
}
```

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|------------|------|----------|
| 1.0.0 | 2025-11-27 | 初版作成 |
