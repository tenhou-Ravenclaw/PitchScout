# ピッチスカウト バックエンド アーキテクチャ

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
├── main.py                  # 全 API エンドポイント定義（唯一のエントリポイント）
├── analyzer.py              # 音声解析パイプライン（CREPE → 声区分類 → 結果集計）
├── register_classifier.py   # 地声 / 裏声 判定（ML + ルールベースハイブリッド）
├── feature_extractor.py     # ML 用特徴量抽出（6次元）
├── recommender.py           # 歌唱力分析・おすすめ曲・似てるアーティスト・キー計算
├── vocal_separator.py       # Demucs ボーカル分離ラッパー
├── audio_converter.py       # ffmpeg ラッパー（WAV 変換 2種）
├── database.py              # SQLite アクセス（楽曲・アーティスト検索）
├── database_supabase.py     # Supabase アクセス（認証・履歴・お気に入り）
├── auth.py                  # JWT 認証 Depends（get_current_user / get_optional_user）
├── models.py                # Pydantic リクエスト / レスポンスモデル
├── config.py                # 解析閾値・定数の一元管理
├── note_converter.py        # Hz ↔ 日本式音程表記 変換（A4=442Hz 対応表）
│
├── ml/
│   ├── models/
│   │   └── register_model.joblib   # 学習済み声区分類モデル
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
├── update_manual_readings.py # 手動で読み仮名を設定するスクリプト
├── check_and_report.py      # データ品質チェックレポートスクリプト
├── noise_reducer.py         # ノイズ低減ユーティリティ（実験用）
│
├── requirements.txt         # Python 依存パッケージ
├── .env                     # 環境変数（Supabase URL / KEY / JWT_SECRET）
└── supabase_migration.sql   # Supabase テーブル定義 SQL
```

---

## 3. API エンドポイント一覧

エントリポイントは `main.py` のみ。全エンドポイントをここで定義する。

### 認証 (`/auth/*`)

| メソッド | パス | 認証 | 説明 |
|----------|------|------|------|
| POST | `/auth/signup` | 不要 | メールでユーザー登録 |
| POST | `/auth/signin` | 不要 | メールでログイン → JWT 返却 |
| POST | `/auth/signout` | 必須 | ログアウト |
| POST | `/auth/refresh` | 不要 | リフレッシュトークンでセッション更新 |
| POST | `/auth/reset-password` | 不要 | パスワードリセットメール送信 |
| POST | `/auth/update-password` | 必須 | パスワード更新 |

### ユーザープロファイル (`/profile/*`)

| メソッド | パス | 認証 | 説明 |
|----------|------|------|------|
| GET | `/profile/me` | 必須 | 自分のプロファイル取得 |
| PUT | `/profile/me` | 必須 | プロファイル更新 |
| PUT | `/profile/vocal-range` | 必須 | 声域情報更新 |

### 分析履歴 (`/analysis/*`)

| メソッド | パス | 認証 | 説明 |
|----------|------|------|------|
| POST | `/analysis` | 必須 | 分析履歴を手動保存（声域も同時更新） |
| GET | `/analysis/history` | 必須 | 自分の分析履歴一覧（最新50件） |
| GET | `/analysis/integrated-range` | 必須 | 直近N件の統合音域取得 |
| DELETE | `/analysis/history/{id}` | 必須 | 分析履歴削除 |
| PATCH | `/analysis/history/{id}` | 必須 | ファイル名などの更新 |

### お気に入り楽曲 (`/favorites/*`)

| メソッド | パス | 認証 | 説明 |
|----------|------|------|------|
| POST | `/favorites` | 必須 | お気に入りに楽曲追加 |
| DELETE | `/favorites/{song_id}` | 必須 | お気に入りから楽曲削除 |
| GET | `/favorites` | 必須 | お気に入り楽曲一覧 |
| GET | `/favorites/check/{song_id}` | 必須 | お気に入り登録確認 |

### お気に入りアーティスト (`/favorite-artists/*`)

| メソッド | パス | 認証 | 説明 |
|----------|------|------|------|
| POST | `/favorite-artists` | 必須 | お気に入りアーティスト追加（上限10組） |
| DELETE | `/favorite-artists/{artist_id}` | 必須 | お気に入りアーティスト削除 |
| GET | `/favorite-artists` | 必須 | お気に入りアーティスト一覧 |
| GET | `/favorite-artists/check/{artist_id}` | 必須 | お気に入り登録確認 |

### 楽曲・アーティスト（認証不要）

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/artists` | アーティスト一覧（ページネーション・検索対応） |
| GET | `/artists/{id}/songs` | アーティストの楽曲一覧（声域指定でキー推薦付き） |
| GET | `/songs` | 楽曲一覧・検索（声域指定でキー推薦付き） |
| GET | `/recommend` | 音域 Hz 指定でおすすめ曲取得 |
| GET | `/similar-artists` | 音域 Hz 指定で似てるアーティスト取得 |

### 音声解析（認証オプショナル）

| メソッド | パス | 説明 |
|----------|------|------|
| POST | `/analyze` | アカペラ / マイク録音用（Demucs なし）。ログイン済みなら履歴自動保存 |
| POST | `/analyze-karaoke` | カラオケ音源用（Demucs ボーカル分離あり）。ログイン済みなら履歴自動保存 |

---

## 4. 音声解析パイプライン

`analyzer.py` の `analyze()` 関数が全体を統括するオーケストレータ。
内部は7ステップのパイプライン関数に分割されている。

```
POST /analyze (マイク)      POST /analyze-karaoke (カラオケ)
       │                              │
       ▼                              ▼
convert_to_wav()            convert_to_wav_hq()
  (16kHz・モノラル)           (44.1kHz・ステレオ)
       │                              │
       │                     separate_vocals() [Demucs]
       │                       htdemucs_6s モデル
       │                       --two-stems=vocals
       │                              │
       └──────────────┬───────────────┘
                      ▼
              analyze(wav_path)
                      │
           ┌──────────┤
           │          ▼
           │  [STEP 1/7] _load_audio()
           │    soundfile でWAV読込、ステレオ→モノラル変換
           │    バリデーション（0.3秒未満・無音チェック）
           │
           │  [STEP 2/7] _preprocess()
           │    音量正規化 → 16kHz リサンプル → PyTorch テンソル化
           │    デバイス選択 (CUDA or CPU)
           │
           │  [STEP 3/7] _run_pitch_detection()
           │    torchcrepe.predict() で F0・信頼度を全フレーム推定
           │    デコーダー: weighted_argmax → viterbi → none (フォールバック)
           │    モデル: tiny → small (フォールバック)
           │
           │  [STEP 4/7] _filter_frames()
           │    信頼度フィルタ（CONF_THRESHOLDS: 0.5 → 0.01 段階的緩和）
           │    人声絶対範囲フィルタ（65Hz ～ 1324Hz）
           │    非現実的範囲除去（中央値±1.5oct 下 / ±1.75oct 上）
           │
           │  [STEP 5/7] （_filter_frames 内）
           │    オクターブ補正 (fix_octave_errors)
           │    信頼度重み付き中央値 (median_freq) 計算
           │
           │  [STEP 6/7] _classify_frames()
           │    フレームごとに classify_register() で地声 / 裏声 / unknown 判定
           │    段階的信頼度要求（中央値から遠いほど高信頼度を要求）
           │    裏声ノイズ3段階フィルタ（連続フレーム / RMS / 最小比率）
           │    統計的外れ値除去 (remove_statistical_outliers)
           │    孤立極端値除去 (remove_isolated_extremes)
           │    最高音付近の地声・裏声混在解消
           │
           │  [STEP 7/7] _build_result()
           │    地声・裏声それぞれの min/max を Hz → 日本式音程表記に変換
           │    最高音堅牢化 (_get_robust_max: 持続フレーム数チェック)
           │    声区バランス計算 (chest_ratio / falsetto_ratio)
           │    歌唱力分析 (analyze_singing_ability)
           │
           ▼
      _enrich_result()
        おすすめ曲 (recommend_songs)
        似てるアーティスト (find_similar_artists)
        声質タイプ (classify_voice_type)
           │
           ▼ (ログイン済みの場合)
      create_analysis_record()  ← Supabase に履歴保存
      update_vocal_range()      ← プロファイルの声域を最新化
           │
           ▼
      JSON レスポンス返却
      cleanup_files() ← BackgroundTask で一時ファイル削除
```

---

## 5. モジュール詳細

### `main.py` — エントリポイント

- 全エンドポイントの定義
- `_enrich_result(result, user)`: 解析結果に おすすめ曲・似てるアーティスト・声質タイプを付加する共通ヘルパー
- `cleanup_files(*paths)`: 一時ファイルを背景タスクで削除するユーティリティ
- 起動時に `init_db()` を呼んで SQLite を初期化

### `analyzer.py` — 音声解析

- **`analyze(wav_path, already_separated, no_falsetto)`**: オーケストレータ。内部を7ステップの関数で構成
- **`fix_octave_errors(f0, conf)`**: CREPE がオクターブ誤検出したフレームを中央値基準で修正。ただし高信頼度の高音跳躍フレームは補正しない
- **`remove_unrealistic_range(f0, conf)`**: 中央値から 1.5oct 下 / 1.75oct 上を外れたフレームを除去（非対称：下は厳格、上は緩和）
- **`remove_isolated_extremes(notes)`**: 1 半音以内の隣接フレーム数が一定数未満の孤立した高音フレームを除去
- **`remove_statistical_outliers(notes, percentile, max_semitones_gap)`**: P{percentile} から max_semitones_gap 半音以上離れたフレームを外れ値として除去
- **`check_octave_by_spectrum(y_seg, sr, candidate_hz)`**: FFT でスペクトルエネルギーを比較し、CREPE が 1 オクターブ低く推定した最高音を修正
- **`filter_falsetto_consecutive/rms/min_ratio`**: Demucs 残留楽器を裏声と誤認しないための3段階ノイズフィルタ

### `register_classifier.py` — 声区判定

- **`classify_register(frame, sr, f0, median_freq, already_separated, crepe_conf)`**: 1フレームを地声 / 裏声 / unknown に分類するメイン関数
- **ハイブリッド判定構造**:
  1. ハード下限チェック (FALSETTO_HARD_MIN_HZ = 270Hz): これ以下は無条件で地声
  2. CREPE 信頼度チェック: ノイズゲート（0.35未満）は unknown
  3. ML モデル推論: `extract_features()` で6特徴量抽出 → sklearn モデルで確率計算
  4. ML 信頼度チェック: 信頼度が閾値未満なら次へ
  5. ルールベースフォールバック: H1-H2 差 + HNR + スペクトル重心 + 倍音比率 で判定
- **MLモデル**: `ml/models/register_model.joblib` (joblib 形式)。起動時ロード・ファイル変更時ホットリロード対応

### `feature_extractor.py` — 特徴量抽出

| 特徴量 | 内容 |
|--------|------|
| `h1_h2` | H1 - H2 差 (dB)。正値が大きい ≈ 裏声（breathiness） |
| `hcount` | 有効倍音本数。多い ≈ 地声（倍音豊富） |
| `slope` | 倍音減衰スロープ (dB/harmonic)。急傾斜 ≈ 地声 |
| `hnr` | 調波対雑音比 (0-1)。高 ≈ 地声（有声音が安定） |
| `centroid_r` | スペクトル重心 / f0。高 ≈ 裏声（高調波成分が多い） |
| `f0` | 基本周波数 (Hz)。高 ≈ 裏声の可能性が上がる |

### `recommender.py` — 推薦エンジン

- **`recommend_songs(chest_min_hz, chest_max_hz, chest_avg_hz, falsetto_max_hz, limit, favorite_artist_ids)`**:
  全楽曲を走査してスコアリング。スコア = 100 - 低音ペナルティ - 高音ペナルティ - 中心音ずれ。
  お気に入りアーティスト登録がある場合: DISCOVERY_SLOTS(4曲)は必ずお気に入り以外から選ぶ
- **`find_similar_artists(chest_min_hz, chest_max_hz, chest_avg_hz, limit)`**:
  アーティストごとに全楽曲の最低音・最高音の中央値を計算して比較
- **`classify_voice_type(chest_min_hz, chest_max_hz, chest_avg_hz, falsetto_max_hz, chest_ratio)`**:
  平均声域 Hz でレンジクラス（バス / バリトン / テノール / ハイテノール）を決定。
  高音有無・裏声使用度の組み合わせで7種類の声質タイプを返す
- **`recommend_key_for_song(song_lowest_note, song_highest_note, user_min_hz, user_max_hz)`**:
  -7〜+7 半音シフトで最適キー（ペナルティ最小）を探索。fit = perfect / good / ok / hard

### `audio_converter.py` — 音声変換

- **`convert_to_wav(input_path, output_dir)`**: マイク録音 / アカペラ用。**16kHz・モノラル**に変換
  CREPE のサンプリングレート (16kHz) に合わせるため。Demucs 前処理には使わない
- **`convert_to_wav_hq(input_path, output_dir)`**: Demucs 前処理用。**44.1kHz・ステレオ・16bit PCM**
  Demucs は 44.1kHz ステレオで学習されており、低品質音声だと分離精度が大幅低下する
- ffmpeg の実行パスは `find_ffmpeg()` で自動探索（PATH → Homebrew → 固定パス候補）

### `vocal_separator.py` — ボーカル分離

- **`separate_vocals(input_wav_path, output_dir, ultra_fast_mode)`**: Demucs を subprocess で呼び出す
- `ultra_fast_mode=True` 時は `htdemucs_6s` を使用（デフォルト）。`--two-stems=vocals` でボーカルと BGM のみ分離
- 出力パス: `{output_dir}/{model_name}/{stem_name}/vocals.wav`
- ファイルが見つからない場合は glob で再帰検索してフォールバック

### `database.py` — SQLite（楽曲データ）

- `songs.db` は起動時読み取り専用で運用（本番時は scraper.py で再構築）
- **テーブル構造**:
  - `artists(id, name, slug, song_count, reading)` — 約850アーティスト
  - `songs(id, title, artist_id, lowest_note, highest_note, falsetto_note, note, source)` — 約5000曲
- **検索ロジック**: クエリがひらがな / カタカナのみなら `reading` 列（読み仮名）で検索（`_query_mode`）。
  それ以外は楽曲名・アーティスト名のテキスト検索
- カタカナをひらがなに正規化（`_hiragana_normalize`）して混在検索に対応

### `database_supabase.py` — Supabase（ユーザーデータ）

- `supabase` クライアントを環境変数から初期化。`SUPABASE_URL` または `SUPABASE_KEY` が未設定なら `None` を返す（認証なしでもアプリが動作するよう設計）
- **主な関数**:

| 関数 | 説明 |
|------|------|
| `get_user_profile(user_id)` | ユーザープロファイル取得 |
| `update_user_profile(user_id, data)` | プロファイル更新 |
| `update_vocal_range(user_id, min, max, falsetto)` | 声域情報更新 |
| `create_analysis_record(user_id, ...)` | 分析履歴保存（result_json も格納） |
| `get_analysis_history(user_id, limit)` | 分析履歴取得 |
| `get_integrated_vocal_range(user_id, limit)` | 直近N件の最低音・最高音の統合音域計算 |
| `add_favorite_song(user_id, song_id)` | お気に入り楽曲追加 |
| `remove_favorite_song(user_id, song_id)` | お気に入り楽曲削除 |
| `get_favorite_songs(user_id, limit)` | お気に入り楽曲一覧（songs.db と JOIN して曲情報を付加） |
| `add_favorite_artist(user_id, artist_id, artist_name)` | お気に入りアーティスト追加（上限10組） |
| `get_favorite_artist_ids(user_id)` | お気に入りアーティスト ID 一覧（recommend_songs 用） |

### `auth.py` — 認証

- **`get_current_user(credentials)`**: `Authorization: Bearer {token}` から JWT を取得し、Supabase で検証。失敗時は HTTP 401
- **`get_optional_user(credentials)`**: 認証ヘッダーがなければ `None` を返す（未ログインユーザーも利用可能なエンドポイント用）
- Supabase の `auth.get_user(token)` でサーバー側トークン検証

### `models.py` — Pydantic モデル

| モデル | 用途 |
|--------|------|
| `SignUpRequest` | メール登録（email, password, display_name） |
| `SignInRequest` | ログイン（email, password） |
| `UserProfileUpdate` | プロファイル更新（display_name, avatar_url, dam_account_id） |
| `VocalRangeUpdate` | 声域更新（vocal_range_min, vocal_range_max, falsetto_max — 日本式表記） |
| `AnalysisCreate` | 分析履歴手動保存（vocal_range_min/max, falsetto_max, source_type, file_name） |
| `AnalysisUpdate` | 履歴更新（file_name のみ） |
| `FavoriteSongAdd` | お気に入り楽曲追加（song_id） |
| `FavoriteArtistAdd` | お気に入りアーティスト追加（artist_id, artist_name） |

### `config.py` — 定数管理

解析に関わる全閾値をこのファイルに集約。チューニング時はここだけ変更する。

| カテゴリ | 主要定数 |
|----------|---------|
| ピッチ検出 | `VOICE_MIN_HZ=65`, `VOICE_MAX_HZ=1324`, `CREPE_SR=16000`, `CREPE_HOP_LENGTH=160` |
| 信頼度フィルタ | `CONF_THRESHOLDS=[0.5,0.35,0.2,0.1,0.05,0.01]`, `CONF_MIN_FRAMES=5` |
| 外れ値除去 | `CHEST_OUTLIER_PERCENTILE=97`, `FALSETTO_OUTLIER_PERCENTILE=75` |
| 裏声ノイズ | `FALSETTO_MIN_CONSECUTIVE=5`, `FALSETTO_MIN_RATIO=0.05`, `FALSETTO_RMS_RATIO=0.15` |
| 声区 ML 判定 | `FALSETTO_HARD_MIN_HZ=270`, `ML_CONF_THRESHOLD_LOW_F0=0.75` |
| 安定性スコア | `STABILITY_MIN_SEGMENT=3`, `STABILITY_SCALING=0.8` |
| ログ制御 | `REGISTER_LOG_LEVEL=1`（env で上書き可。0=なし / 1=サマリー / 2=間引き / 3=全て） |

### `note_converter.py` — 音程変換

- A4 = **442Hz**（日本カラオケ標準）基準の対応表 (`NOTE_TABLE`)
- オクターブ表記: `lowlow` / `low` / `mid1` / `mid2` / `hi` / `hihi` / `hihihi`
- **`hz_to_label_and_hz(hz)`**: 対数スケールで最近傍を検索して日本式表記に変換
- DB 側の表記ゆれ（`mid1A/B` = `mid2A/B` 相当、`loX` = `lowX`）は `recommender.py` 側の `_NOTE_ALIASES` で吸収

---

## 6. データベース設計

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
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT NOT NULL,
    artist_id    INTEGER NOT NULL REFERENCES artists(id),
    lowest_note  TEXT,                -- 最低音（日本式表記 例: mid1C）
    highest_note TEXT,                -- 最高音
    falsetto_note TEXT,               -- 裏声最高音
    note         TEXT,                -- 補足メモ
    source       TEXT DEFAULT 'voice-key.news'
);
```

- 実行時は**読み取り専用**。書き込みは `scraper.py` 実行時のみ
- 再構築: `rm -f songs.db && python scraper.py`

### Supabase (PostgreSQL) — ユーザーデータ

スキーマ詳細は `supabase_migration.sql` を参照。主要テーブル:

| テーブル | 説明 |
|----------|------|
| `profiles` | ユーザープロファイル（display_name, vocal_range_min/max, falsetto_max） |
| `analysis_records` | 分析履歴（声域・source_type・ファイル名・result_json） |
| `favorite_songs` | お気に入り楽曲（user_id + song_id） |
| `favorite_artists` | お気に入りアーティスト（user_id + artist_id + artist_name、上限10組） |

---

## 7. 歌唱力スコア計算

`recommender.py` の `analyze_singing_ability()` が算出する4指標:

| 指標 | 重み | 算出方法 |
|------|------|---------|
| 音域スコア (`range_score`) | 30% | `range_semitones / 30 × 100`（30半音=2.5oct で満点） |
| 安定性スコア (`stability_score`) | 45% | 持続音セグメント内のピッチ標準偏差（セント）から逆算 |
| 表現力スコア (`expression_score`) | 25% | 地声・裏声の使い分け多様性 + 音域活用度 (IQR) |
| 総合スコア (`overall_score`) | — | 上3指標の加重平均 |

安定性の目安:
- 10 cents 偏差 → 約 92 点（プロレベル）
- 25 cents → 約 80 点（上手い素人）
- 40 cents → 約 68 点（普通のカラオケ）

---

## 8. ログ規約

バックエンドのログ接頭辞:

| 接頭辞 | 用途 |
|--------|------|
| `[API]` | エンドポイント受信・完了 |
| `[STEP X/7]` | 解析パイプラインの進捗 |
| `[INFO]` | 通常の処理情報 |
| `[DEBUG]` | 詳細なデバッグ情報 |
| `[WARN]` | 非致命的な警告（処理は継続） |
| `[ERROR]` | エラー（処理中断の可能性） |
| `[FILTER]` | 裏声ノイズフィルタの適用ログ |

声区判定のログ量は `REGISTER_LOG_LEVEL` 環境変数で制御（本番では 1 推奨）。

---

## 9. セキュリティ・運用上の注意

- CORS は現在 `allow_origins=["*"]`。本番では必要最小オリジンに限定すること
- `.env` ファイル（SUPABASE_URL / SUPABASE_KEY / JWT_SECRET）は絶対にコミットしない
- 一時ファイル (`uploads/`, `separated/`) は `BackgroundTasks` で解析後即削除
- Supabase の service_role キー (`SUPABASE_KEY`) はバックエンド専用。フロントエンドには anon キーのみ使う
- 解析閾値は `config.py` 以外にハードコードしない

---

## 10. 開発セットアップ

```bash
cd backend

# 1. 仮想環境の作成と有効化
python3 -m venv venv
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate           # Windows

# 2. 依存パッケージのインストール
pip install -r requirements.txt

# 3. 環境変数の設定
cp .env.example .env              # SUPABASE_URL / SUPABASE_KEY を記入

# 4. 開発サーバー起動
uvicorn main:app --reload         # http://localhost:8000

# 5. ヘルスチェック
curl http://localhost:8000/docs   # Swagger UI

# songs.db の再構築（必要な場合のみ）
rm -f songs.db && python scraper.py
```

**重要**: 必ず `source venv/bin/activate` を先に実行すること。
Homebrew のグローバル uvicorn と venv の依存パッケージが競合する。

### システム依存

- `ffmpeg` — 音声変換に必須 (`brew install ffmpeg`)
- GPU (CUDA) — CREPE・Demucs が自動認識。なければ CPU で動作（低速）
