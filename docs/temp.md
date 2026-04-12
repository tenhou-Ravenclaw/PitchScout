# PitchScout 全体まとめ（Backend + Frontend）

このドキュメントは、プロジェクト全体をざっくり把握するためのメモ。
詳細仕様ではなく、構成・処理フロー・主要ロジックの要点をまとめる。

最終更新: 2026-04-09

## 1. プロジェクト全体像

- 目的: 音声から声域を推定し、歌いやすい楽曲を推薦する
- フロントエンド: React 19 + TypeScript（CRA）
- バックエンド: FastAPI + Python
- 音声解析: WORLD (pyworld) + RandomForest + AP/HNR ハイブリッド判定
- ボーカル分離: MelBandRoformers (audio-separator)
- ノイズ除去: DeepFilterNet + Silero VAD
- データ:
	- 楽曲カタログ: SQLite (`backend/songs.db`, 約5000曲・約850アーティスト)
	- ユーザー情報/履歴/お気に入り: Supabase (PostgreSQL)

## 2. Frontend の役割

主に次の4つを担当する。

1. 音声入力 UI
- マイク録音
- カラオケ音源アップロード
- アカペラ音声ファイルアップロード

2. 解析リクエスト送信
- Axios クライアントを通して API 呼び出し
- 認証時は JWT を自動付与

3. 結果表示
- 地声/裏声の音域
- 推薦楽曲
- 履歴・成長グラフ

4. 認証とユーザー機能
- Supabase Auth（メール+パスワード）
- お気に入り（曲・アーティスト）・履歴・プロフィール

### 2.1 主な構造

- `App.tsx`: Router + Provider 初期化
- `routes.tsx`: ルート定義（全ページ `React.lazy()` 遅延ロード）
- `routeWrappers/`: Context とページを橋渡しするラッパーコンポーネント
- `contexts/`
	- `AuthContext.tsx`: ログイン状態管理
	- `AnalysisContext.tsx`: 解析進捗管理
	- `AppContext.tsx`: 画面共有状態（`userRange` を localStorage に永続化）
- `api/`
	- `client.ts`: Axios インスタンス（JWT 自動付与・401 リフレッシュ）
	- `analysis.ts`: 解析 API
	- `songs.ts`: 楽曲・アーティスト API
	- `listApi.ts`: リスト系 API
	- `auth.ts`: 認証 API
	- `totalRange.ts`: 統合声域 API
	- `types.ts`: API 型定義
	- `error.ts`: エラーハンドリング
- `pages/`: 各画面コンポーネント
- `components/`: UI 共通部品

### 2.2 採用技術

- React 19, TypeScript, react-router-dom v7
- Axios, Tailwind CSS, Recharts
- Supabase JS SDK
- CRA (react-scripts)

### 2.3 認証フロー（Frontend）

1. メール+パスワードで Supabase Auth を使用
2. セッションを `AuthContext` が管理
3. `api/client.ts` の interceptor が JWT を `Authorization: Bearer` に自動設定
4. 401 時は一度だけ `refreshSession()` を試行して再実行、失敗時は sign out

## 3. Backend の役割

主に次の5つを担当する。

1. API 提供
- 解析 API（マイク / カラオケ）
- 楽曲検索・推薦 API
- 認証/ユーザー API

2. 音声前処理
- WAV 変換（ffmpeg）
- MelBandRoformers でボーカル分離（カラオケモード）
- DeepFilterNet ノイズ除去

3. 声域解析
- WORLD (pyworld) で F0/SP/AP 抽出
- AP/HNR ゲート + RandomForest による地声/裏声判定
- レンジ算出・歌唱力スコアリング

4. 推薦
- 推定音域と楽曲音域の Hz マッチング

5. 永続化
- 履歴保存・プロファイル声域更新
- お気に入り管理（曲・アーティスト）

### 3.1 主な構造

- `main.py`: FastAPI 起動、CORS（`ALLOWED_ORIGINS` 環境変数）、アップロード上限50MB、ルーター登録
  - lifespan 初期化: `init_db()`（SQLite）, `init_deepfilter()`（DeepFilterNet）, `init_silero_vad()`（Silero VAD）
- `config.py`: 解析閾値・定数を一元管理
- `models.py`: Pydantic モデル
- `note_converter.py`: Hz ↔ 音階ラベル変換（A4=442Hz）
- `recommender.py`: 楽曲推薦・類似アーティスト・声質タイプ判定
- `auth.py`: 認証ヘルパー（`get_current_user` / `get_optional_user`）
- `routers/`: エンドポイント定義（FastAPI `APIRouter`）
	- `analysis.py`: `/analyze`, `/analyze-karaoke`
	- `songs.py`: `/songs`, `/artists`, `/recommend`, `/recommend/challenge`, `/similar-artists`
	- `users.py`: `/profile/*`, `/analysis/*`（`/analysis/growth` 含む）, `/favorites*`（`batch-check` 含む）, `/favorite-artists*`
	- `auth.py`: `/auth/*`
- `analysis/`: 解析コア
	- `pipeline.py`: WORLD + RF 推論メインフロー
	- `feature_extractor.py`: WORLD 特徴抽出（F0/SP/AP → フレーム音響特徴 → セグメント特徴20次元）
	- `classifier.py`: HybridClassifier（AP/HNR ゲート先行 + RF フォールバック）
	- `scoring.py`: 歌唱力スコアリング
	- `features.py`: 倍音特徴抽出ユーティリティ（ML 学習スクリプトから参照）
- `audio/`: 音声前処理
	- `converter.py`: ffmpeg WAV 変換
	- `separator.py`: MelBandRoformers ボーカル分離
	- `noise.py`: DeepFilterNet ノイズ除去 / Silero VAD
- `db/`: データアクセス
	- `songs.py`: SQLite（楽曲・アーティスト）
	- `users.py`: Supabase（ユーザー・履歴・お気に入り）
- `ml/`: 学習関連
	- `train.py`: VocalSet を用いた胸声検出器の学習（StandardScaler + RandomForest Pipeline）
	- `models/register_model.joblib`: 学習済みモデル + メタデータ（chest_label, chest_probability_threshold 等）
	- `training_data/`: 特徴量キャッシュ（`world_dataset.npz`）
	- 学習データ: VocalSet（chest/modal 系中心。falsetto ラベルは不十分なため、裏声は推論時に AP ルールで判定）

## 4. 音声解析パイプライン（要点）

### 4.1 `/analyze`（アカペラ/マイク）

1. ファイル検証（拡張子/MIME/マジックバイト）
2. WAV 変換（16kHz モノラル, `audio/converter.py`）
3. 解析実行（`analysis/pipeline.py::analyze`）
4. おすすめ曲/類似アーティスト/声質タイプの付与
5. ログイン中なら履歴保存 + プロファイル声域更新

### 4.2 `/analyze-karaoke`（カラオケ音源）

1. ファイル検証
2. 高品質 WAV 変換（44.1kHz ステレオ）
3. MelBandRoformers でボーカル分離（`audio/separator.py`）
4. DeepFilterNet ノイズ除去（`audio/noise.py`）
5. 解析実行（`analysis/pipeline.py::analyze`）
6. 結果拡張・履歴保存

### 4.3 解析コア（`analysis/pipeline.py`）

`pipeline.py` 内でおおむね次の順序で処理する。

1. WAV 読み込み（soundfile）
2. WORLD 特徴抽出（`feature_extractor.py`）
   - pyworld で F0 / SP(スペクトル包絡) / AP(非周期性指標) を取得
3. フレーム音響特徴の算出（`extract_frame_acoustic_features`, 9次元）
   - f0, f0_std: 基本周波数とその標準偏差
   - ap_mean, ap_std: 非周期性指標の平均/標準偏差
   - hnr: 調波対雑音比
   - sp_tilt: スペクトル傾斜
   - h1_h2: 第1倍音と第2倍音の差
   - hcount: 有効倍音数
   - harmonic_score: 倍音スコア
4. セグメント特徴（20次元）を集約（`aggregate_world_features`）
   - F0 統計 (6次元): f0_mean, f0_std, logf0_mean, logf0_std, f0_range, voiced_ratio
   - AP 帯域別 (8次元): ap_global/low/mid/high の mean, std
   - SP 形状 (6次元): sp_centroid/rolloff/flatness の mean, std
5. RandomForest（Pipeline: StandardScaler + RFC）で chest confidence（胸声信頼度）を推定
6. Gate-first Hybrid 判定でフレーム分類（`classifier.py::HybridClassifier`）
7. セグメントラベル決定（chest/falsetto 比率 + RF 信頼度）
8. レンジ算出（overall / chest / falsetto の min/max）
9. 歌唱力分析（`scoring.py`）
10. 音階ラベル化して結果返却

## 5. ノイズ除去の多段処理（`audio/noise.py`）

カラオケモード（`/analyze-karaoke`）では MelBandRoformers 分離後に以下の多段ノイズ処理を行う。

1. **DeepFilterNet3**（ニューラルネットワークベース）
   - 残留楽器音・背景ノイズを除去
   - `DFN_ATTENUATION_LIMIT_DB`（デフォルト20dB）で減衰上限を制御
   - `main.py` の lifespan で `init_deepfilter()` により起動時初期化

2. **Silero VAD**（Voice Activity Detection）
   - 歌声区間と非歌声区間（楽器ハーモニクス等）を判別
   - `SILERO_VAD_THRESHOLD`（デフォルト0.3、話し声向け0.5より低め）で歌声を拾いやすく設定
   - 裏声フレームの過剰除去を防ぐ安全弁あり（`VAD_MAX_REMOVAL_RATIO`, `VAD_NARROW_CLUSTER_SEMITONES`）
   - `main.py` の lifespan で `init_silero_vad()` により起動時初期化

3. **noisereduce**（後方互換、従来方式）

## 6. `classifier.py` の現在方針

`HybridClassifier` によるゲート先行ハイブリッド判定を採用。

設計方針:
- AP（非周期性指標）と HNR（倍音対ノイズ比）を主要ゲートとする
- 両条件成立で裏声確定、片側のみ成立は曖昧扱いで RF にフォールバック
- 判定ハード下限（mid2E = 330Hz）未満は常に地声確定

`HybridClassifier.classify_frame()` の判断順:

1. f0 < `FALSETTO_HARD_MIN_HZ`（330Hz）→ 地声確定
2. AP高 AND HNR低 → 裏声（強条件）
3. AP高 XOR HNR低 → RF の chest confidence でフォールバック判定
4. それ以外 → 地声

閾値は `config.py` に集約:
- `AP_THRESHOLD_HIGH` / `AP_THRESHOLD_TRANSITION`: AP ゲート（高音域/遷移帯域）
- `HNR_THRESHOLD_HIGH` / `HNR_THRESHOLD_TRANSITION`: HNR ゲート
- `RF_CHEST_THRESHOLD`: RF フォールバック時の胸声確定閾値

## 7. データフロー（簡略）

1. Frontend が音声をアップロード（マイク録音 or ファイル）
2. Backend が前処理（WAV変換、必要に応じてボーカル分離・ノイズ除去）
3. WORLD + RF Hybrid で声域を解析して JSON 返却
4. Frontend が結果画面へ反映
5. ログイン中なら Supabase に履歴保存・プロファイル声域更新
6. 推薦 API と組み合わせて曲提案

## 8. 設定・運用上の注意

- 解析しきい値は `config.py` に集約（他ファイルにハードコードしない）
- A4 は 442Hz 基準（`note_converter.py`）
- CORS は `ALLOWED_ORIGINS` 環境変数で制御（未設定時は localhost のみ）
- 認証は `supabaseClient.ts`（null 許容）/ `db/users.py` の有効性に依存
- 重い処理（MelBandRoformers + DeepFilterNet + 長尺解析）は API 応答時間が長くなりやすい
- フロントエンドの API タイムアウトは10分（ボーカル分離に必要、短縮禁止）

## 9. いまの課題感（大まか）

- 長尺カラオケ音源で解析時間が長い（MelBandRoformers + DeepFilterNet が律速）
- AP/HNR ゲートの閾値が裏声の検出率に直結するチューニング課題
- ノイズ除去（DeepFilterNet）を強くすると本物の裏声まで落ちるトレードオフ
- Silero VAD の閾値調整（歌声は話し声と特性が異なるため低めに設定中）

## 10. どこを見れば良いか（用途別）

- 解析結果が不自然: `backend/analysis/pipeline.py`, `backend/analysis/classifier.py`, `backend/analysis/feature_extractor.py`, `backend/config.py`
- ボーカル分離の品質: `backend/audio/separator.py`（MelBandRoformers）
- ノイズ除去の調整: `backend/audio/noise.py`（DeepFilterNet / Silero VAD）, `backend/config.py`（`DFN_ATTENUATION_LIMIT_DB`, `SILERO_VAD_THRESHOLD`）
- ML モデルの再学習: `backend/ml/train.py`, `backend/ml/models/register_model.joblib`
- ログイン不具合: `frontend/src/contexts/AuthContext.tsx`, `frontend/src/supabaseClient.ts`, `backend/auth.py`
- API 通信不具合: `frontend/src/api/client.ts`, `backend/routers/*.py`
- 推薦の精度/件数: `backend/recommender.py`, `backend/db/songs.py`