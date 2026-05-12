# PitchScout アーキテクチャ（最新版）

最終更新: 2026-04-20  
対象リポジトリ: PitchScout

本ドキュメントは、現在の実装コードを基準に構成を整理したものです。

---

## 1. 全体構成

PitchScout は、フロントエンド（React/TypeScript）とバックエンド（FastAPI/Python）で構成される音域分析アプリです。

- フロントエンド: 録音/アップロード UI、結果表示、履歴・お気に入り管理
- バックエンド: 音声前処理、声区分析、推薦、ユーザーデータ管理
- データストア:
  - SQLite: 楽曲・アーティスト（読み取り中心）
  - Supabase(PostgreSQL): 認証、プロフィール、履歴、お気に入り

### 1.1 構成図（論理）

```text
[Browser / React]
  ├─ routes.tsx + routeWrappers
  ├─ Contexts (Auth / App / Analysis)
  └─ API client (Axios + Supabase token interceptor)
          |
          | HTTPS
          v
[FastAPI]
  ├─ routers/auth.py
  ├─ routers/users.py
  ├─ routers/songs.py
  └─ routers/analysis.py
        ├─ audio/converter.py      (ffmpeg WAV 変換)
        ├─ audio/separator.py      (MelBandRoformers ボーカル分離)
        ├─ audio/noise.py          (DeepFilterNet ノイズ除去)
        └─ analysis/pipeline.py    (WORLD + AP/HNR ゲート + RF 20次元ベクトル)

[SQLite songs.db]   [Supabase]
```

---

## 2. フロントエンド

### 2.1 採用技術

- React 19
- TypeScript
- react-router-dom
- Axios
- Tailwind CSS
- Supabase JS SDK
- Recharts
- CRA（react-scripts）

参照: `frontend/package.json`

### 2.2 ルーティング設計

`frontend/src/routes.tsx` で全ページを `React.lazy()` による遅延ロードに統一しています。
主要パス:

- `/` `/menu` `/record` `/karaoke` `/upload`
- `/result` `/analysis` `/songs`
- `/favorites` `/history`
- `/guide` `/login` `/reset-password` `/change-password`

### 2.3 API 通信と認証連携

`frontend/src/api/client.ts` の `API` インスタンスを全 API 通信で使用します。

- リクエスト時: Supabase セッションから JWT を取得し `Authorization: Bearer ...` を自動付与
- レスポンス時: 401 を受けたら一度だけ `refreshSession()` を試行して再実行

`frontend/src/supabaseClient.ts` は環境変数未設定時に `null` を返す実装で、認証機能を無効化してもアプリが落ちない設計です。

---

## 3. バックエンド

### 3.1 採用技術

- FastAPI / Uvicorn
- numpy / scipy / librosa / soundfile
- torch / torchaudio
- pyworld
- audio-separator[cpu]（MelBandRoformers 実行）
- deepfilternet
- scikit-learn / joblib
- Supabase Python SDK

参照: `backend/requirements.txt`

### 3.2 エントリポイント

`backend/main.py`

- lifespan 初期化:
  - SQLite 初期化: `db.songs.init_db()`
  - ノイズ処理モデル初期化: `init_deepfilter()`, `init_silero_vad()`
- CORS: `ALLOWED_ORIGINS`（環境変数）
- アップロード上限: 50MB（ミドルウェア）
- ルーター登録: auth / users / songs / analysis

### 3.3 ディレクトリ責務

```text
backend/
  main.py               FastAPIアプリ設定
  config.py             閾値・定数の一元管理
  models.py             Pydanticモデル
  note_converter.py     Hz <-> 音階ラベル(A4=442Hz)
  recommender.py        楽曲推薦・類似アーティスト・声質タイプ判定
  auth.py               認証ヘルパー

  routers/
    auth.py             /auth/*
    users.py            /profile/*, /analysis/*, /favorites*, /favorite-artists*
    songs.py            /songs, /artists, /recommend, /recommend/challenge, /similar-artists
    analysis.py         /analyze, /analyze-karaoke

  audio/
    converter.py        WAV変換 (ffmpeg: 16kHz mono / 44.1kHz stereo)
    separator.py        MelBandRoformersでボーカル分離
    noise.py            DeepFilterNet3 ノイズ除去 + Silero VAD

  analysis/
    pipeline.py         メイン解析パイプライン (WORLD → RF → AP/HNRゲート → 結果整形)
    classifier.py       HybridClassifier (AP/HNRゲート + RFフォールバック)
    feature_extractor.py WORLD特徴抽出・20次元セグメント特徴集約
    features.py         倍音特徴抽出ユーティリティ（ML学習スクリプトから参照）
    scoring.py          歌唱力スコア (音域/安定性/表現力)

  ml/
    train.py            20次元WORLD特徴でRandomForest学習
    train_classifier.py 6次元倍音特徴での学習（features.py用）
    test_classifier.py  テストスイート
    labeler.py          学習データラベリング

  db/
    songs.py            SQLiteアクセス (楽曲/アーティスト検索)
    users.py            Supabaseアクセス (認証/履歴/お気に入り)
```

---

## 4. 音声解析パイプライン（現行）

### 4.1 `/analyze`（アカペラ/マイク）

1. ファイル検証（拡張子/MIME/マジックバイト）
2. WAV 変換（`audio/converter.py` → 16kHz モノラル）
3. 解析実行（`analysis/pipeline.py::analyze`）
4. おすすめ曲/類似アーティスト/声質タイプの付与
5. ログイン中なら履歴保存 + プロファイル声域更新

### 4.2 `/analyze-karaoke`（カラオケ音源）

1. ファイル検証
2. 高品質 WAV 変換（44.1kHz ステレオ）
3. ボーカル分離（`audio/separator.py` — MelBandRoformers）
4. DeepFilterNet ノイズ除去（`audio/noise.py`）
5. 解析実行（`analysis/pipeline.py::analyze`）
6. 結果拡張・履歴保存

### 4.3 解析コア（`analysis/pipeline.py`）

処理フロー:

```text
1) 音声読み込み・正規化
2) WORLD 特徴抽出 (F0/SP/AP) → 20次元セグメント特徴
3) RandomForest で chest probability を推定
4) AP/HNR ゲート + RF フォールバックでフレーム分離
5) フレーム比率 + RF を併用して最終セグメントラベル決定
6) FastAPI 互換レスポンス整形（音域/比率/歌唱力分析）
```

### 4.4 地声/裏声判定ロジック

判定は `analysis/classifier.py` の `HybridClassifier` が担う。

**フレーム判定（各有声フレーム）:**
1. f0 < 330Hz (FALSETTO_HARD_MIN_HZ) → 本アプリでは地声寄りとして扱う
2. AP高 AND HNR低 → 裏声確定（ゲート）
3. AP低 AND HNR高 → 地声確定（ゲート）
4. 片側のみ成立（曖昧）→ RF chest probability でフォールバック

**セグメント判定:**
- フレーム分類結果の chest/falsetto 比率と RF の chest probability を平均
- combined >= 0.5 → chest、< 0.5 → falsetto

**20次元ベクトル RF:**
- `feature_extractor.py` の `aggregate_world_features()` で生成
- 内訳: F0統計6次元 + AP帯域特徴8次元 + SP形状特徴6次元 = 20次元
- `ml/models/register_model.joblib` に学習済みモデルを格納

### 4.5 config.py の主要定数

| 定数 | 値 | 用途 |
|------|-----|------|
| FALSETTO_HARD_MIN_HZ | 330.0 | 裏声判定の絶対下限 |
| HIGH_REGISTER_MIN_HZ | 523.0 | AP/HNR 閾値の切替ポイント (C5) |
| AP_THRESHOLD_HIGH | 0.28 | 高音域の AP ゲート閾値 |
| AP_THRESHOLD_TRANSITION | 0.35 | 遷移帯域の AP ゲート閾値 |
| HNR_THRESHOLD_HIGH | 8.0 | 高音域の HNR ゲート閾値 (dB) |
| HNR_THRESHOLD_TRANSITION | 6.0 | 遷移帯域の HNR ゲート閾値 (dB) |
| RF_CHEST_THRESHOLD | 0.60 | 曖昧フレームの RF フォールバック閾値 |

---

## 5. API 構成（実装基準）

### 5.1 認証 (`routers/auth.py`, prefix=`/auth`)

- `POST /auth/signup`
- `POST /auth/signin`
- `POST /auth/signout`
- `POST /auth/refresh`
- `POST /auth/reset-password`
- `POST /auth/update-password`

### 5.2 分析 (`routers/analysis.py`)

- `POST /analyze`
- `POST /analyze-karaoke`

### 5.3 楽曲・アーティスト (`routers/songs.py`)

- `GET /artists`
- `GET /artists/{artist_id}/songs`
- `GET /songs`
- `GET /recommend/challenge`
- `GET /recommend`
- `GET /similar-artists`

### 5.4 ユーザー (`routers/users.py`)

- `GET /profile/me`
- `PUT /profile/me`
- `PUT /profile/vocal-range`
- `POST /analysis`
- `GET /analysis/history`
- `GET /analysis/integrated-range`
- `GET /analysis/timeline`
- `GET /analysis/growth`
- `DELETE /analysis/history/{record_id}`
- `PATCH /analysis/history/{record_id}`
- `POST /favorites`
- `DELETE /favorites/{song_id}`
- `GET /favorites`
- `GET /favorites/check/{song_id}`
- `POST /favorites/batch-check`
- `POST /favorite-artists`
- `DELETE /favorite-artists/{artist_id}`
- `GET /favorite-artists`
- `GET /favorite-artists/check/{artist_id}`

---

## 6. データストア

### 6.1 SQLite（`backend/songs.db`）

- 用途: 楽曲カタログ（約5000曲、約850アーティスト）
- 主に読み取り用途
- アクセス層: `backend/db/songs.py`

### 6.2 Supabase（PostgreSQL + Auth）

- 用途: ユーザー認証、プロフィール、分析履歴、お気に入り
- アクセス層: `backend/db/users.py`, `backend/auth.py`
- スキーマ参照: `backend/supabase_migration.sql`

---

## 7. 設定・運用上の重要事項

- 解析閾値・定数は `backend/config.py` に集約する
- 音階基準は A4=442Hz（`backend/note_converter.py`）
- フロント API 呼び出しは `frontend/src/api/client.ts` の Axios インスタンスを使用
- `frontend/src/supabaseClient.ts` の null ガードを維持する
- 解析 API の公開インターフェース（`/analyze`, `/analyze-karaoke`）は互換性維持

---

## 8. 技術スタック対応表

| レイヤー | 技術 | ファイル |
|---------|------|---------|
| ボーカル分離 | MelBandRoformers (audio-separator) | `audio/separator.py` |
| ノイズ除去 | DeepFilterNet3 | `audio/noise.py` |
| ピッチ/特徴抽出 | WORLD pyworld | `analysis/feature_extractor.py` |
| フレーム判定 | AP/HNR ゲート + RF フォールバック | `analysis/classifier.py` |
| セグメント推論 | RandomForest (20次元 WORLD 特徴) | `analysis/pipeline.py` |
| 歌唱力分析 | 音域/安定性/表現力の3軸スコア | `analysis/scoring.py` |
| 楽曲推薦 | Hz 範囲マッチング + キー変更提案 | `recommender.py` |
