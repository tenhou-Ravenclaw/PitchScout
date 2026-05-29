# ピッチスカウト バックエンド アーキテクチャ

## 0. 変更点まとめ（2026-03-24）

- 分離器を Demucs から MelBandRoformers（`voc_fv6.ckpt`）へ移行
- ピッチ推定を CREPE から WORLD（`pyworld`）へ移行
- 新解析フローは MelBandRoformers → DeepFilterNet → WORLD → RandomForest
- 追加: `analysis/feature_extractor.py`, `ml/train.py`
- 置換: `audio/separator.py`, `analysis/pipeline.py`
- 依存更新: `pyworld`, `huggingface_hub`, `audio-separator[cpu]`, `numpy==2.2.0`
- API 互換性維持: `POST /analyze`, `POST /analyze-karaoke` の入出力仕様は据え置き
- 備考: `pyworld` は環境により `pip install pyworld --no-build-isolation` が必要

## 1. 概要

**ピッチスカウト バックエンド** は FastAPI (Python) で実装された音声解析・楽曲推薦 API サーバー。
マイク録音またはカラオケ音源を受け取り、CREPE によるピッチ推定と ML による声区分類を行い、
ユーザーの声域に合った楽曲をおすすめする。

| 項目 | 技術 |
|------|------|
| フレームワーク | FastAPI + Uvicorn |
| ピッチ推定 | torchcrepe (CREPE tiny/small モデル) |
| ボーカル分離 | Demucs (htdemucs_6s) |
| 声区分類 | scikit-learn ML + ルールベースフォールバック |
| 音声処理 | librosa, soundfile, torchaudio, ffmpeg |
| 楽曲 DB | SQLite (`songs.db` — 約5000曲 / 約850アーティスト) |
| ユーザー DB | Supabase (PostgreSQL) |
| 認証 | Supabase JWT (HTTPBearer) |
| 音程基準 | A4 = **442Hz**（日本のカラオケ標準） |

---

## 2. ファイル構成

```
backend/
├── main.py                  # FastAPI アプリ設定・ミドルウェア・ルーター登録
├── config.py                # 音域解析の全定数・閾値（ここのみに記述）
├── models.py                # Pydantic リクエスト / レスポンスモデル
├── note_converter.py        # Hz ↔ 日本式音程表記 変換（A4=442Hz 対応表）
├── auth.py                  # JWT 認証 Depends（get_current_user / get_optional_user）
├── recommender.py           # 楽曲マッチング・似てるアーティスト・統合音域
│
├── audio/                   # 音声前処理パッケージ
│   ├── __init__.py
│   ├── converter.py         # ffmpeg WAV 変換（16kHz モノラル / 44.1kHz ステレオ）
│   ├── separator.py         # Demucs ボーカル分離（--two-stems=vocals）
│   └── noise.py             # ノイズ除去ユーティリティ
│
├── analysis/                # 音声解析パッケージ
│   ├── __init__.py          # analyze() を re-export
│   ├── pipeline.py          # CREPE ピッチ検出・7ステップパイプライン
│   ├── classifier.py        # ML 地声/裏声判定（scikit-learn + ルールベース）
│   ├── features.py          # ML 用特徴量抽出（6次元）
│   └── scoring.py           # 歌唱力スコアリング（overall/range/stability/expression）
│
├── db/                      # データベース接続パッケージ
│   ├── __init__.py
│   ├── songs.py             # SQLite 楽曲カタログ（読み取り専用）
│   └── users.py             # Supabase ユーザーデータ（認証・履歴・お気に入り）
│
├── routers/                 # FastAPI ルーター（エンドポイント定義）
│   ├── __init__.py
│   ├── auth.py              # /auth/* （メール認証・パスワード管理）
│   ├── analysis.py          # /analyze, /analyze-karaoke
│   ├── songs.py             # /songs, /artists, /recommend, /similar-artists
│   └── users.py             # /profile/*, /analysis/*, /favorites*, /favorite-artists*
│
├── ml/                      # ML モデル関連
│   ├── models/
│   │   └── register_model.joblib   # 学習済み声区分類モデル（起動時ロード・ホットリロード対応）
│   └── train_register.py           # モデル学習スクリプト
│
├── songs.db                 # 楽曲音域データ（コミット済み・実行時読み取り専用）
├── uploads/                 # アップロードされた一時ファイル（解析後自動削除）
├── separated/               # Demucs 分離後の一時ファイル（解析後自動削除）
│
├── scraper.py               # voice-key.news スクレイパー（songs.db 構築用）
├── scraper_vocal_range.py   # 音域データ補完スクレイパー
├── update_db.py             # songs.db 一括更新スクリプト
├── update_all_readings.py   # アーティスト読み仮名一括更新
├── update_manual_readings.py # 手動読み仮名設定スクリプト
├── check_and_report.py      # データ品質チェックレポートスクリプト
│
├── supabase_migration.sql   # Supabase テーブル定義 SQL
├── requirements.txt
└── .env                     # 環境変数（Supabase URL / KEY / ログレベル等）
```

---

## 3. 依存関係グラフ（循環なし）

```
config.py, note_converter.py          ← 依存なし（ベース層）
audio/converter.py                    ← ffmpeg（外部コマンド）
audio/separator.py                    ← Demucs（PyTorch）
audio/noise.py                        ← librosa
analysis/features.py                  ← numpy, librosa, config
analysis/scoring.py                   ← numpy, math, config
analysis/classifier.py                ← analysis.features, config
analysis/pipeline.py                  ← analysis.classifier, analysis.scoring,
                                         note_converter, config
analysis/__init__.py                  ← analysis.pipeline（re-export）
db/songs.py                           ← sqlite3 のみ
db/users.py                           ← db.songs, supabase-py
recommender.py                        ← note_converter, db.songs, numpy, math
auth.py                               ← db.users
routers/auth.py                       ← auth, models
routers/analysis.py                   ← audio.*, analysis, recommender,
                                         db.users, auth
routers/songs.py                      ← db.songs, db.users, recommender, auth
routers/users.py                      ← db.users, recommender, auth, models
main.py                               ← routers.*, db.songs
```

---

## 4. API エンドポイント一覧

### 認証 (`/auth/*`) — `routers/auth.py`

| メソッド | パス | 認証 | 説明 |
|----------|------|:----:|------|
| POST | `/auth/signup` | — | メール+パスワードでユーザー登録 |
| POST | `/auth/signin` | — | メール+パスワードでログイン → JWT 返却 |
| POST | `/auth/signout` | 必須 | ログアウト |
| POST | `/auth/refresh` | — | リフレッシュトークンでセッション更新 |
| POST | `/auth/reset-password` | — | パスワードリセットメール送信 |
| POST | `/auth/update-password` | 必須 | パスワード更新 |

### 音声解析 — `routers/analysis.py`

| メソッド | パス | 認証 | 説明 |
|----------|------|:----:|------|
| POST | `/analyze` | 任意 | アカペラ/マイク録音の音域分析（Demucs なし）。ログイン済みなら履歴自動保存 |
| POST | `/analyze-karaoke` | 任意 | カラオケ音源の音域分析（Demucs ボーカル分離あり）。ログイン済みなら履歴自動保存 |

### 楽曲・アーティスト — `routers/songs.py`

| メソッド | パス | 認証 | 説明 |
|----------|------|:----:|------|
| GET | `/songs` | — | 楽曲一覧（検索・ページネーション・キーおすすめ付き） |
| GET | `/artists` | — | アーティスト一覧（検索・ページネーション） |
| GET | `/artists/{artist_id}/songs` | — | 特定アーティストの楽曲一覧（声域指定でキー推薦付き） |
| GET | `/recommend` | 任意 | Hz 指定でおすすめ曲取得 |
| GET | `/similar-artists` | — | Hz 指定で声が似てるアーティスト取得 |

### ユーザー — `routers/users.py`

| メソッド | パス | 認証 | 説明 |
|----------|------|:----:|------|
| GET | `/profile/me` | 必須 | 自分のプロファイル取得 |
| PUT | `/profile/me` | 必須 | プロファイル更新（display_name / avatar_url 等） |
| PUT | `/profile/vocal-range` | 必須 | 声域情報（min/max/falsetto）更新 |
| POST | `/analysis` | 必須 | 分析履歴を手動保存（声域も同時更新） |
| GET | `/analysis/history` | 必須 | 分析履歴取得（新しい順、最大 100 件） |
| GET | `/analysis/integrated-range` | 必須 | 直近 N 件の統合音域・おすすめ曲取得 |
| GET | `/analysis/timeline` | 必須 | 直近 N 件のタイムライン＋安定音域取得（成長グラフ用） |
| DELETE | `/analysis/history/{record_id}` | 必須 | 分析履歴削除 |
| PATCH | `/analysis/history/{record_id}` | 必須 | 分析履歴の file_name 等を更新 |
| POST | `/favorites` | 必須 | お気に入り楽曲追加 |
| DELETE | `/favorites/{song_id}` | 必須 | お気に入り楽曲削除 |
| GET | `/favorites` | 必須 | お気に入り楽曲一覧 |
| GET | `/favorites/check/{song_id}` | 必須 | お気に入り登録確認 |
| POST | `/favorite-artists` | 必須 | お気に入りアーティスト追加（上限 10 組） |
| DELETE | `/favorite-artists/{artist_id}` | 必須 | お気に入りアーティスト削除 |
| GET | `/favorite-artists` | 必須 | お気に入りアーティスト一覧 |
| GET | `/favorite-artists/check/{artist_id}` | 必須 | お気に入りアーティスト確認 |

---

## 5. 音声解析パイプライン

`analysis/pipeline.py` の `analyze()` 関数が全体を統括するオーケストレータ。

```
POST /analyze (マイク)          POST /analyze-karaoke (カラオケ)
       │                                    │
       ▼                                    ▼
audio/converter.py                 audio/converter.py
  convert_to_wav()                   convert_to_wav_hq()
  (16kHz・モノラル)                  (44.1kHz・ステレオ)
       │                                    │
       │                          audio/separator.py
       │                            separate_vocals()
       │                            [Demucs htdemucs_6s]
       │                            --two-stems=vocals
       │                                    │
       └─────────────┬──────────────────────┘
                     ▼
             analysis/pipeline.py
                 analyze()
                     │
      ┌──────────────┤
      │              ▼
      │   [STEP 1/7] _load_audio()
      │     soundfile で WAV 読込、ステレオ→モノラル変換
      │     バリデーション（0.3秒未満・無音チェック）
      │
      │   [STEP 2/7] _preprocess()
      │     音量正規化 → 16kHz リサンプル → PyTorch テンソル化
      │     デバイス選択 (CUDA or CPU)
      │
      │   [STEP 3/7] _run_pitch_detection()
      │     torchcrepe.predict() で F0・信頼度を全フレーム推定
      │     CONF_THRESHOLDS: 0.5 → 0.35 → 0.2 → 0.1 → 0.05 → 0.01
      │
      │   [STEP 4/7] _filter_frames()
      │     信頼度フィルタ（段階的緩和）
      │     人声絶対範囲フィルタ（65Hz ～ 1324Hz）
      │     非現実的範囲除去（中央値±1.5oct 下 / ±1.75oct 上）
      │
      │   [STEP 5/7] オクターブ補正・重心計算
      │     fix_octave_errors() でオクターブ誤検出を修正
      │     信頼度重み付き中央値 (median_freq) 計算
      │
      │   [STEP 6/7] _classify_frames()
      │     analysis/classifier.py で地声 / 裏声 / unknown 判定
      │     裏声ノイズ3段階フィルタ（連続フレーム / RMS / 最小比率）
      │     統計的外れ値除去・孤立極端値除去
      │     最高音付近の地声・裏声混在解消
      │
      │   [STEP 7/7] _build_result()
      │     地声・裏声の min/max を Hz → 日本式音程表記に変換
      │     最高音堅牢化（MIN_SUSTAIN_FRAMES=3 フレーム以上持続）
      │     声区バランス計算（chest_ratio / falsetto_ratio）
      │     analysis/scoring.py で歌唱力スコアを計算
      │
      ▼
  routers/analysis.py: _enrich_result()
    recommend_songs()       ← recommender.py
    find_similar_artists()  ← recommender.py
    classify_voice_type()   ← recommender.py
      │
      ▼ (ログイン済みの場合)
  db/users.py: create_analysis_record()  ← Supabase に履歴保存
  db/users.py: update_vocal_range()      ← プロファイルの声域を最新化
      │
      ▼
  JSON レスポンス返却
  cleanup_files() ← BackgroundTask で一時ファイル削除
```

---

## 6. モジュール詳細

### `main.py` — アプリ設定

- `lifespan`: 起動時に `db/songs.py` の `init_db()` を呼んで SQLite を初期化
- CORS: `ALLOWED_ORIGINS` 環境変数でカンマ区切り指定（未設定時は `localhost:3000`）
- アップロード上限: 50MB（Content-Length + 実測サイズの両方でチェック）
- ルーター登録: `auth.router`, `users.router`, `songs.router`, `analysis.router`

### `analysis/pipeline.py` — 音声解析（旧 `analyzer.py`）

- **`analyze(wav_path, already_separated, no_falsetto)`**: オーケストレータ。7ステップの関数で構成
- **`fix_octave_errors(f0, conf)`**: CREPE がオクターブ誤検出したフレームを中央値基準で修正
- **`remove_unrealistic_range(f0, conf)`**: 中央値から 1.5oct 下 / 1.75oct 上を外れたフレームを除去
- **`remove_isolated_extremes(notes)`**: 隣接フレーム数が不足する孤立した高音フレームを除去
- **`remove_statistical_outliers(notes, percentile, max_semitones_gap)`**: パーセンタイル外れ値除去

### `analysis/classifier.py` — 声区判定（旧 `register_classifier.py`）

- **`classify_register(frame, sr, f0, median_freq, already_separated, crepe_conf)`**: 1フレームを地声 / 裏声 / unknown に分類
- **ハイブリッド判定構造**:
  1. ハード下限チェック (`FALSETTO_HARD_MIN_HZ=270Hz`): これ以下は無条件で地声
  2. CREPE 信頼度チェック: ノイズゲート（0.35未満）は unknown
  3. ML モデル推論: `analysis/features.py` で6特徴量抽出 → scikit-learn モデルで確率計算
  4. ML 信頼度が閾値未満ならルールベースフォールバック
- **ML モデル**: `ml/models/register_model.joblib`。起動時ロード・ファイル変更時ホットリロード対応

### `analysis/features.py` — 特徴量抽出（旧 `feature_extractor.py`）

| 特徴量 | 内容 |
|--------|------|
| `h1_h2` | H1 - H2 差 (dB)。正値が大きい ≈ 裏声（breathiness） |
| `hcount` | 有効倍音本数。多い ≈ 地声（倍音豊富） |
| `slope` | 倍音減衰スロープ (dB/harmonic)。急傾斜 ≈ 地声 |
| `hnr` | 調波対雑音比 (0-1)。高 ≈ 地声（有声音が安定） |
| `centroid_r` | スペクトル重心 / f0。高 ≈ 裏声（高調波成分が多い） |
| `f0` | 基本周波数 (Hz)。高 ≈ 裏声の可能性が上がる |

### `analysis/scoring.py` — 歌唱力スコア（旧 `recommender.py` から分離）

| 指標 | 重み | 算出方法 |
|------|------|---------|
| `range_score` | 30% | `range_semitones / 30 × 100`（30半音=2.5oct で満点） |
| `stability_score` | 45% | 持続音セグメント内のピッチ標準偏差（セント）から逆算 |
| `expression_score` | 25% | 地声・裏声の使い分け多様性 + 音域活用度 (IQR) |
| `overall_score` | — | 上3指標の加重平均 |

安定性の目安: 10 cents → 約 92 点（プロ相当）/ 25 cents → 約 80 点 / 40 cents → 約 68 点

### `audio/converter.py` — 音声変換（旧 `audio_converter.py`）

- **`convert_to_wav(input_path, output_dir)`**: マイク/アカペラ用。**16kHz・モノラル**（CREPE の入力仕様に合わせる）
- **`convert_to_wav_hq(input_path, output_dir)`**: Demucs 前処理用。**44.1kHz・ステレオ・16bit PCM**（Demucs の学習仕様に合わせる）
- ffmpeg の実行パスは `find_ffmpeg()` で自動探索（PATH → Homebrew → 固定パス候補）

### `audio/separator.py` — ボーカル分離（旧 `vocal_separator.py`）

- **`separate_vocals(input_wav_path, output_dir, ultra_fast_mode)`**: Demucs を subprocess で呼び出す
- `htdemucs_6s` モデル、`--two-stems=vocals` でボーカルと BGM のみ分離
- 出力パス: `{output_dir}/{model_name}/{stem_name}/vocals.wav`
- ファイルが見つからない場合は glob で再帰検索してフォールバック

### `recommender.py` — 推薦エンジン

- **`recommend_songs(..., favorite_artist_ids)`**: 全楽曲をスコアリング。
  - `DISCOVERY_SLOTS=4`: お気に入り以外のアーティストから必ず確保
  - `FAV_MAX_SLOTS=6`: お気に入りアーティスト優先枠
  - `MAX_PER_ARTIST=2`: 同一アーティスト最大 2 曲（多様性確保）
- **`find_similar_artists(...)`**: アーティスト最低音・最高音の中央値で比較
- **`classify_voice_type(...)`**: 平均声域と裏声使用度で7種類の声質タイプを返す
- **`recommend_key_for_song(...)`**: -7〜+7 半音シフトで最適キーを探索。fit = perfect / good / ok / hard
- **`aggregate_vocal_range(records, favorite_artist_ids)`**: 分析履歴複数件から統合音域を計算

**音階表記の互換処理（DB の表記揺れ対策）:**
- `mid1A/A#/B` → `mid2A/A#/B` と同周波数にマッピング
- `loX` → `lowX` の表記揺れを吸収（`_NOTE_ALIASES` 辞書）

### `db/songs.py` — SQLite 楽曲カタログ（旧 `database.py`）

- `songs.db` は起動時読み取り専用で運用
- **検索ロジック**: クエリがひらがな/カタカナのみなら `reading` 列（読み仮名）で検索。それ以外は楽曲名・アーティスト名のテキスト検索
- カタカナをひらがなに正規化して混在検索に対応

### `db/users.py` — Supabase ユーザーデータ（旧 `database_supabase.py`）

| 関数 | 説明 |
|------|------|
| `get_user_profile(user_id)` | プロファイル取得 |
| `update_user_profile(user_id, data)` | プロファイル更新 |
| `update_vocal_range(user_id, min, max, falsetto)` | 声域情報更新 |
| `create_analysis_record(user_id, ...)` | 分析履歴保存（result_json も格納） |
| `get_analysis_history(user_id, limit)` | 分析履歴取得（新しい順） |
| `get_analysis_timeline(user_id, limit)` | 分析タイムライン取得（**古い順**・成長グラフ用） |
| `delete_analysis_record(user_id, record_id)` | 分析履歴削除 |
| `update_analysis_record(user_id, record_id, data)` | 分析履歴更新 |
| `add_favorite_song / remove_favorite_song / get_favorite_songs / is_favorite` | お気に入り楽曲 CRUD |
| `add_favorite_artist / remove_favorite_artist / get_favorite_artists / is_favorite_artist` | お気に入りアーティスト CRUD（上限 10 組） |
| `get_favorite_artist_ids(user_id)` | アーティスト ID リスト取得（recommend_songs 用） |

### `auth.py` — 認証

- **`get_current_user(credentials)`**: JWT を Supabase で検証。`Depends(get_current_user)` で保護エンドポイントに使用
- **`get_optional_user(credentials)`**: 未ログインなら `None` を返す。`Depends(get_optional_user)` で任意認証エンドポイントに使用
- Supabase が `None`（環境変数未設定）の場合は `_ensure_auth_available()` が HTTP 503 を返す

### `note_converter.py` — 音程変換

- A4 = **442Hz**（日本カラオケ標準）基準の対応表 `NOTE_TABLE`（C1〜E7、77エントリ）
- **`hz_to_label_and_hz(hz)`**: 対数スケールで最近傍を検索して日本式表記に変換
- **`label_to_rank(label)`**: ラベル → NOTE_TABLE インデックス（音高順位）。安定音域計算で使用
- **`to_japanese_notation(note)`**: 後方互換。"C4" 等の文字列 → 日本語ラベル

**オクターブ対応（日本語ラベル体系）:**

| NOTE_TABLE 範囲 | プレフィックス | 例 |
|----------------|---------------|----|
| C1〜G#1 | `lowlow` | `lowlowC` |
| A1〜B1 | `low` | `lowA`, `lowB` |
| C2〜G#2 | `low` | `lowC` |
| A2〜B2 | `mid1` | `mid1A`, `mid1B` |
| C3〜G#3 | `mid1` | `mid1C` |
| A3〜B3 | `mid2` | `mid2A`, `mid2B` |
| C4〜G#4 | `mid2` | `mid2C` |
| A4〜B4 | `hi` | `hiA`, `hiB` |
| C5〜G#5 | `hi` | `hiC` |
| A5〜B5 | `hihi` | `hihiA`, `hihiB` |
| C6〜G#6 | `hihi` | `hihiC` |
| A6〜B6 | `hihihi` | `hihihiA`, `hihihiB` |
| C7〜E7 | `hihihi` | `hihihiC` |

### `config.py` — 定数管理

解析に関わる全閾値をこのファイルに集約。**他ファイルへのハードコードは禁止**。

| カテゴリ | 主要定数 |
|----------|---------|
| ピッチ検出 | `VOICE_MIN_HZ=65`, `VOICE_MAX_HZ=1324`, `CREPE_SR=16000`, `CREPE_HOP_LENGTH=160` |
| 信頼度フィルタ | `CONF_THRESHOLDS=[0.5,0.35,0.2,0.1,0.05,0.01]`, `CONF_MIN_FRAMES=5` |
| 外れ値除去 | `CHEST_OUTLIER_PERCENTILE=97`, `CHEST_OUTLIER_GAP_ST=3`, `FALSETTO_OUTLIER_PERCENTILE=95` |
| 裏声ノイズ | `FALSETTO_MIN_CONSECUTIVE=5`, `FALSETTO_MIN_RATIO=0.05`, `FALSETTO_RMS_RATIO=0.15` |
| 声区 ML 判定 | `FALSETTO_HARD_MIN_HZ=270`, `ML_CONF_THRESHOLD_LOW_F0=0.75`, `CREPE_NOISE_GATE=0.35` |
| 最高音堅牢化 | `MIN_SUSTAIN_FRAMES=3` |
| 安定性スコア | `STABILITY_MIN_SEGMENT=3`, `STABILITY_SCALING=0.8` |
| ログ制御 | `REGISTER_LOG_LEVEL=1`（env で上書き可。0=なし / 1=サマリー / 2=間引き / 3=全て） |

---

## 7. 安定音域アルゴリズム（成長グラフ機能）

`GET /analysis/timeline` が実装。直近 N 件の分析履歴から安定した音域を判定する。

```python
STABLE_THRESHOLD = 4  # 直近N件中4回以上出現したラベルを「安定」とみなす

chest_max_counts = Counter(r.get("vocal_range_max") for r in records if r.get("vocal_range_max"))
# ...同様に chest_min, falsetto_max も集計

stable_chest_max = max(candidates, key=label_to_rank)   # 最高音を選択
stable_chest_min = min(candidates, key=label_to_rank)   # 最低音を選択
stable_falsetto  = max(candidates, key=label_to_rank)   # 最高音を選択
```

`label_to_rank()` は `NOTE_TABLE` のインデックス（0 = lowlowC）を音高順位として使用。

---

## 8. データベース設計

### SQLite (`songs.db`) — 楽曲データ

```sql
CREATE TABLE artists (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    slug       TEXT NOT NULL UNIQUE,  -- URL-friendly 名
    song_count INTEGER DEFAULT 0,
    reading    TEXT                   -- ひらがな読み仮名（かな検索用）
);

CREATE TABLE songs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT NOT NULL,
    artist_id     INTEGER NOT NULL REFERENCES artists(id),
    lowest_note   TEXT,                -- 最低音（日本式表記 例: mid1C）
    highest_note  TEXT,                -- 最高音
    falsetto_note TEXT,                -- 裏声最高音
    note          TEXT,                -- 補足メモ
    source        TEXT DEFAULT 'voice-key.news'
);
```

- 実行時は**読み取り専用**。再構築: `rm -f songs.db && python scraper.py`

### Supabase (PostgreSQL) — ユーザーデータ

スキーマ詳細は `supabase_migration.sql` を参照。主要テーブル:

| テーブル | 説明 |
|----------|------|
| `user_profiles` | display_name, current_vocal_range_min/max, current_falsetto_max, avatar_url |
| `analysis_history` | vocal_range_min/max, falsetto_max, source_type, file_name, result_json (JSONB) |
| `favorite_songs` | user_id + song_id |
| `favorite_artists` | user_id + artist_id + artist_name（上限 10 組） |

---

## 9. ログ規約

| 接頭辞 | 用途 |
|--------|------|
| `[API]` | エンドポイント受信・完了 |
| `[STEP X/7]` | 解析パイプラインの進捗 |
| `[INFO]` | 通常の処理情報 |
| `[DEBUG]` | 詳細なデバッグ情報 |
| `[WARN]` | 非致命的な警告（処理は継続） |
| `[ERROR]` | エラー（処理中断の可能性） |

声区判定のログ量は `REGISTER_LOG_LEVEL` 環境変数で制御（本番では 1 推奨）。

---

## 10. セキュリティ・運用上の注意

- CORS は `ALLOWED_ORIGINS` 環境変数で制御。本番では必要最小オリジンに限定すること
- `.env`（SUPABASE_URL / SUPABASE_KEY / JWT_SECRET）は絶対にコミットしない
- 一時ファイル（`uploads/`, `separated/`）は `BackgroundTasks` で解析後即削除
- Supabase の `SUPABASE_KEY`（anon or service_role）はバックエンド専用。フロントエンドには別途 anon キーのみ使う
- 解析閾値は `config.py` 以外にハードコードしない

---

## 11. 開発セットアップ

```bash
cd backend

# 1. 仮想環境の作成と有効化（必須）
python3 -m venv venv
source venv/bin/activate   # macOS / Linux
# venv\Scripts\activate    # Windows

# 2. 依存パッケージのインストール
pip install -r requirements.txt

# 3. 環境変数の設定
cp .env.example .env       # SUPABASE_URL / SUPABASE_KEY を記入

# 4. 開発サーバー起動
uvicorn main:app --reload  # http://localhost:8000

# 5. 動作確認
curl http://localhost:8000/health  # ヘルスチェック
# http://localhost:8000/docs       # Swagger UI

# songs.db の再構築（必要な場合のみ）
rm -f songs.db && python scraper.py
```

> **重要**: 必ず `source venv/bin/activate` を先に実行すること。
> Homebrew のグローバル uvicorn と venv の依存パッケージが競合する。

### システム依存

- `ffmpeg` — 音声変換に必須（`brew install ffmpeg`）
- GPU (CUDA) — CREPE・Demucs が自動認識。なければ CPU で動作（低速）
