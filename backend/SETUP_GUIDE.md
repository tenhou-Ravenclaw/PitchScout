# Supabase + FastAPI 認証システム セットアップガイド

## 🎯 概要

このプロジェクトは**Supabase Auth**を使用した認証システムを実装しています。

### 主な機能
- ✅ メールアドレス/パスワード認証
- ✅ ユーザープロファイル管理
- ✅ 声域分析の履歴保存
- ✅ お気に入り楽曲管理
- 🔜 Google OAuth（将来実装予定）
- 🔜 DAM連携（将来実装予定）

## 📋 事前準備

### 1. Supabaseプロジェクトの作成

1. [Supabase](https://supabase.com)にアクセスしてアカウント作成
2. 新しいプロジェクトを作成
3. プロジェクト設定から以下の情報を取得:
   - **Project URL** (例: `https://xxxxx.supabase.co`)
   - **Anon Key** (公開用APIキー)

### 2. データベースのセットアップ

1. Supabaseダッシュボードで **「SQL Editor」** を開く
2. `backend/supabase_migration.sql` の内容を全てコピー
3. SQL Editorに貼り付けて **「Run」** を実行

これで以下のテーブルが作成されます：
- `user_profiles` - ユーザープロファイル
- `analysis_history` - 声域分析履歴
- `favorite_songs` - お気に入り楽曲
- `artists` - アーティスト情報
- `songs` - 楽曲情報

### 3. 環境変数の設定

```bash
cd backend
cp .env.example .env
```

`.env`ファイルを編集して、Supabaseの情報を入力：

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key-here
JWT_SECRET=your-jwt-secret-here-change-in-production
```

### 4. 依存関係のインストール

```bash
# 仮想環境を有効化した状態で実行
python -m pip install --upgrade pip wheel

# pyworld は環境依存で失敗する場合があるため先に導入
python -m pip install "setuptools<81"
pip install pyworld --no-build-isolation

# その後に通常の依存を導入
pip install -r requirements.txt
```

補足:
- `numpy` は `requirements.txt` で `2.2.0` に固定しています。
- `pyworld` 導入時に `pkg_resources` エラーが出る場合、`setuptools` 再インストール後に再実行してください。

### 4.1 声区分類モデルの再学習（必要時）

音声解析パイプライン更新後は、学習済みモデルの再生成が必要です。

```bash
cd backend
source venv/bin/activate
python ml/train.py \
  --dataset-root ml/vocalset_data/FULL \
  --manifest ml/training_data/vocalset_manifest.csv
```

出力:
- `ml/models/register_model.joblib`
- `ml/training_data/world_dataset.npz`

### 5. サーバーの起動

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 📚 API エンドポイント

### 認証

| メソッド | エンドポイント | 説明 | 認証 |
|---------|---------------|------|-----|
| POST | `/auth/signup` | ユーザー登録 | 不要 |
| POST | `/auth/signin` | ログイン | 不要 |
| POST | `/auth/signout` | ログアウト | 必要 |
| POST | `/auth/refresh` | トークン更新 | 不要 |
| POST | `/auth/reset-password` | パスワードリセット | 不要 |
| POST | `/auth/update-password` | パスワード更新 | 必要 |

### ユーザープロファイル

| メソッド | エンドポイント | 説明 | 認証 |
|---------|---------------|------|-----|
| GET | `/profile/me` | 自分のプロファイル取得 | 必要 |
| PUT | `/profile/me` | プロファイル更新 | 必要 |
| PUT | `/profile/vocal-range` | 声域情報更新 | 必要 |

### 分析履歴

| メソッド | エンドポイント | 説明 | 認証 |
|---------|---------------|------|-----|
| POST | `/analysis` | 分析履歴を保存 | 必要 |
| GET | `/analysis/history` | 履歴一覧取得 | 必要 |

### お気に入り

| メソッド | エンドポイント | 説明 | 認証 |
|---------|---------------|------|-----|
| GET | `/favorites` | お気に入り一覧 | 必要 |
| POST | `/favorites` | お気に入り追加 | 必要 |
| DELETE | `/favorites/{song_id}` | お気に入り削除 | 必要 |
| GET | `/favorites/check/{song_id}` | お気に入り確認 | 必要 |

### 楽曲検索（認証不要）

| メソッド | エンドポイント | 説明 | 認証 |
|---------|---------------|------|-----|
| GET | `/songs` | 楽曲一覧・検索 | 不要 |

### 音声分析（認証オプショナル）

| メソッド | エンドポイント | 説明 | 認証 |
|---------|---------------|------|-----|
| POST | `/analyze` | マイク録音分析 | オプショナル |
| POST | `/analyze-karaoke` | カラオケ音源分析 | オプショナル |

※ログイン済みの場合、分析結果が自動的に履歴に保存されます

## 🔐 認証フロー例

### 1. ユーザー登録

```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "display_name": "山田太郎"
  }'
```

レスポンス例：
```json
{
  "user": {
    "id": "uuid-here",
    "email": "user@example.com"
  },
  "session": {
    "access_token": "jwt-token-here",
    "refresh_token": "refresh-token-here"
  }
}
```

### 2. ログイン

```bash
curl -X POST http://localhost:8000/auth/signin \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

### 3. 認証が必要なエンドポイントへのアクセス

```bash
curl -X GET http://localhost:8000/profile/me \
  -H "Authorization: Bearer <access_token>"
```

## 🛠️ トラブルシューティング

### エラー: "SUPABASE_URLとSUPABASE_KEYを.envファイに設定してください"

→ `.env`ファイルが正しく設定されているか確認してください

### エラー: "認証エラー: Invalid JWT"

→ トークンの有効期限が切れています。`/auth/refresh`でトークンを更新してください

### テーブルが見つからない

→ `supabase_migration.sql`を実行したか確認してください

## 📊 データベース構造

```
user_profiles (ユーザープロファイル)
├─ id (UUID, PK)
├─ email
├─ display_name
├─ avatar_url
├─ dam_account_id
├─ current_vocal_range_min
├─ current_vocal_range_max
└─ current_falsetto_max

analysis_history (分析履歴)
├─ id (UUID, PK)
├─ user_id (FK → user_profiles)
├─ vocal_range_min
├─ vocal_range_max
├─ falsetto_max
├─ source_type
├─ file_name
└─ created_at

favorite_songs (お気に入り)
├─ id (UUID, PK)
├─ user_id (FK → user_profiles)
├─ song_id (FK → songs)
└─ created_at
```

## 🚀 次のステップ

### Google認証を追加する場合

1. Supabaseダッシュボードの **「Authentication」** → **「Providers」**
2. Googleを有効化してClient IDとSecretを設定
3. フロントエンドから`supabase.auth.signInWithOAuth({ provider: 'google' })`を呼び出す

### DAM連携を追加する場合

1. `user_profiles.dam_account_id`にDAMのIDを保存
2. DAM APIとの連携処理を実装
3. `/profile/me`でDAM連携状態を確認

## 📝 ライセンス

MIT License
