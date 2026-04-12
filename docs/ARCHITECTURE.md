# PitchScout アーキテクチャ（最新版）

最終更新: 2026-04-09  
対象リポジトリ: 2026_team11/PitchScout

本ドキュメントは、現在の実装コードを基準に構成を整理したものです。
要件・設計の参照元は `docs/requirements/REQUIREMENTS.md` ですが、実際の動作は本書の「実装現況」を優先します。

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
        ├─ audio/converter.py
        ├─ audio/separator.py (MelBandRoformers)
        ├─ audio/noise.py (DeepFilterNet / Silero VAD)
        └─ analysis/pipeline.py (WORLD + RandomForest + AP hybrid)

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
  recommender.py        楽曲推薦・類似アーティスト
  auth.py               認証ヘルパー

  routers/
    auth.py             /auth/*
    users.py            /profile/*, /analysis/*(growth含む), /favorites*(batch-check含む), /favorite-artists*
    songs.py            /songs, /artists, /recommend, /recommend/challenge, /similar-artists
    analysis.py         /analyze, /analyze-karaoke

  audio/
    converter.py        WAV変換
    separator.py        MelBandRoformersでボーカル分離
    noise.py            DeepFilterNet / Silero VAD

  analysis/
    pipeline.py         現行メイン推論
    feature_extractor.py WORLD特徴抽出・AP分離
    scoring.py          歌唱力スコア
    classifier.py       HybridClassifier（AP/HNRゲート先行+RFフォールバック）
    features.py         倍音特徴抽出ユーティリティ（ML学習スクリプトから参照）

  db/
    songs.py            SQLiteアクセス
    users.py            Supabaseアクセス
```

---

## 4. 音声解析パイプライン（現行）

### 4.1 `/analyze`（アカペラ/マイク）

1. ファイル検証（拡張子/MIME/マジックバイト）
2. WAV 変換（`audio/converter.py`）
3. 解析実行（`analysis/pipeline.py::analyze`）
4. おすすめ曲/類似アーティスト/声質タイプの付与
5. ログイン中なら履歴保存 + プロファイル声域更新

### 4.2 `/analyze-karaoke`（カラオケ音源）

1. ファイル検証
2. 高品質 WAV 変換
3. ボーカル分離（`audio/separator.py`）
   - 実装は MelBandRoformers（audio-separator）
4. DeepFilterNet ノイズ除去
5. 解析実行（`analysis/pipeline.py::analyze`）
6. 結果拡張・履歴保存

### 4.3 解析コア（`analysis/pipeline.py`）

- WORLD 特徴抽出（`feature_extractor.py`）
  - F0 / SP / AP
- セグメント特徴（20次元）を作成
- `register_model.joblib`（RandomForest）で chest 信頼度推定
- AP ベース規則と組み合わせた hybrid 判定
- レンジ算出（overall/chest/falsetto）
- 歌唱力分析（`analysis/scoring.py`）

### 4.4 地声/裏声判定の現況

現行経路は `analysis/pipeline.py` → `analysis/classifier.py` (`HybridClassifier`) が中心です。

- フレーム判定（主判定）:
  - `analysis/classifier.py` の `HybridClassifier.classify_frame()` が全有声フレームを分類
  - AP/HNR ゲート先行: AP高 AND HNR低 → 裏声、どちらも低い → 地声
  - 曖昧フレーム（片側のみ成立）→ RandomForest の `chest_confidence` でフォールバック
- セグメント判定:
  - フレーム分類結果の chest/falsetto 比率から最終ラベルを決定
- 学習用ユーティリティ:
  - `analysis/features.py`（H1-H2/hcount/slope/HNR など。`ml/` の学習スクリプトから参照）
  - `analysis/feature_extractor.py` の `split_register_by_aperiodicity`（AP ベース分離関数、現行パイプラインでは未使用）

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

## 8. 既知のドキュメント差分メモ

過去資料に「Demucs / CREPE」表記が残っている箇所がありますが、現行実装は以下です。

- ボーカル分離: MelBandRoformers（`backend/audio/separator.py`）
- ピッチ/特徴抽出: WORLD pyworld（`backend/analysis/feature_extractor.py`）
- フレーム判定: HybridClassifier — AP/HNR ゲート先行 + RF フォールバック（`backend/analysis/classifier.py`）
- セグメント推論: RandomForest（20次元 WORLD 特徴 → chest confidence）（`backend/analysis/pipeline.py`）
- ノイズ除去: DeepFilterNet + Silero VAD（`backend/audio/noise.py`）

`config.py` に AP/HNR ゲート閾値、VAD パラメータ、DeepFilterNet 設定などが追加されています。
実装確認時は本ドキュメントと対象ソースコードを優先してください。
