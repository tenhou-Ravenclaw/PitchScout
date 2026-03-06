# ピッチスカウト アーキテクチャ

## 1. プロジェクト概要

**ピッチスカウト** は、ユーザーの声を録音・分析し、音域に合った楽曲やキー変更を提案する Web アプリ。

| 項目 | 技術 |
|------|------|
| フレームワーク (FE) | React 19 + TypeScript |
| スタイリング | Tailwind CSS 3 |
| HTTP クライアント | Axios |
| グラフライブラリ | Recharts |
| 認証 | Supabase Auth (Google OAuth / メール) |
| アイコン | Heroicons v2 |
| ビルドツール | Create React App (react-scripts) |
| フレームワーク (BE) | FastAPI (Python 3.12) |
| 楽曲 DB | SQLite (`backend/songs.db` / 約 5000 曲) |
| ユーザー DB | Supabase (PostgreSQL) |
| ピッチ検出 | torchcrepe (CREPE) |
| ボーカル分離 | Demucs (htdemucs_6s) |
| ML モデル | scikit-learn (`ml/models/register_model.joblib`) |

本番環境: `https://pitchscout.ten-hou.com`

---

## 2. バックエンド ディレクトリ構成

```
backend/
├── main.py                  # FastAPI アプリ設定・ミドルウェア・ルーター登録
├── config.py                # 音域解析の全定数・閾値（ここのみに記述）
├── models.py                # Pydantic モデル（リクエスト/レスポンス型）
├── note_converter.py        # Hz ↔ 日本語音階ラベル変換（A4=442Hz 基準）
├── auth.py                  # JWT 検証・認証ヘルパー関数
├── recommender.py           # 楽曲マッチング・似てるアーティスト・統合音域
│
├── audio/                   # 音声前処理パッケージ
│   ├── __init__.py
│   ├── converter.py         # ffmpeg WAV 変換（16kHz モノラル / 44.1kHz ステレオ）
│   ├── separator.py         # Demucs ボーカル分離（カラオケモード）
│   └── noise.py             # ノイズ除去
│
├── analysis/                # 音声解析パッケージ
│   ├── __init__.py          # analyze() を re-export
│   ├── pipeline.py          # CREPE ピッチ検出・メインパイプライン
│   ├── classifier.py        # ML 地声/裏声判定（scikit-learn + ルールベース）
│   ├── features.py          # ML 用特徴量抽出
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
├── ml/                      # ML モデル関連（学習スクリプト・モデルファイル）
│   └── models/
│       └── register_model.joblib   # 学習済み地声/裏声分類モデル
│
├── songs.db                 # SQLite 楽曲データ（約 5000 曲・850 アーティスト）
├── requirements.txt
└── .env                     # 環境変数（Supabase URL/KEY、ログレベル等）
```

### DBメンテナンス用スクリプト（非本番）

| ファイル | 用途 |
|---------|------|
| `scraper.py` | songs.db 全体を再構築 |
| `scraper_vocal_range.py` | 声域情報のスクレイピング |
| `update_db.py` | songs.db への一括更新 |
| `update_all_readings.py` | アーティスト読み仮名の一括更新 |
| `update_manual_readings.py` | 手動修正分の読み仮名更新 |
| `check_and_report.py` | DB 整合性チェック・レポート |

---

## 3. バックエンド 依存関係グラフ（循環なし）

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

## 4. バックエンド 全エンドポイント

### 認証 (`/auth/*`) — `routers/auth.py`

| メソッド | パス | 認証 | 説明 |
|----------|------|:----:|------|
| POST | `/auth/signup` | — | メール+パスワードでユーザー登録 |
| POST | `/auth/signin` | — | メール+パスワードでログイン |
| POST | `/auth/signout` | 必須 | ログアウト |
| POST | `/auth/refresh` | — | リフレッシュトークンでセッション更新 |
| POST | `/auth/reset-password` | — | パスワードリセットメール送信 |
| POST | `/auth/update-password` | 必須 | パスワード更新 |

### 音声解析 (`/analyze*`) — `routers/analysis.py`

| メソッド | パス | 認証 | 説明 |
|----------|------|:----:|------|
| POST | `/analyze` | 任意 | アカペラ/マイク録音の音域分析（Demucs なし） |
| POST | `/analyze-karaoke` | 任意 | カラオケ音源の音域分析（Demucs ボーカル分離あり） |

> ログイン済みの場合、分析結果は自動で `analysis_history` テーブルに保存される。

### 楽曲・アーティスト — `routers/songs.py`

| メソッド | パス | 認証 | 説明 |
|----------|------|:----:|------|
| GET | `/songs` | — | 楽曲一覧（検索・ページネーション・キーおすすめ付き） |
| GET | `/artists` | — | アーティスト一覧（検索・ページネーション） |
| GET | `/artists/{artist_id}/songs` | — | 特定アーティストの楽曲一覧 |
| GET | `/recommend` | 任意 | Hz 指定でおすすめ曲取得 |
| GET | `/similar-artists` | — | Hz 指定で声が似てるアーティスト取得 |

### ユーザー — `routers/users.py`

| メソッド | パス | 認証 | 説明 |
|----------|------|:----:|------|
| GET | `/profile/me` | 必須 | 自分のプロファイル取得 |
| PUT | `/profile/me` | 必須 | プロファイル更新（display_name / avatar_url 等） |
| PUT | `/profile/vocal-range` | 必須 | 声域情報（min/max/falsetto）更新 |
| POST | `/analysis` | 必須 | 分析履歴を手動保存 |
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

```
音声ファイル受信
      │
      ▼
[STEP 1] WAV 変換 (audio/converter.py)
         ├─ /analyze         → 16kHz モノラル（マイク録音向け）
         └─ /analyze-karaoke → 44.1kHz ステレオ（Demucs 処理向け）
      │
      ▼（/analyze-karaoke のみ）
[STEP 2] Demucs ボーカル分離 (audio/separator.py)
         htdemucs_6s モデルでボーカル/BGM を分離
      │
      ▼
[STEP 3] CREPE ピッチ検出 (analysis/pipeline.py)
         複数閾値の信頼度フォールバック: 0.5 → 0.35 → 0.2 → 0.1 → 0.05 → 0.01
         CREPE_SR=16000Hz, CREPE_HOP_LENGTH=160 (10ms)
      │
      ▼
[STEP 4] ML 声区分類 (analysis/classifier.py)
         scikit-learn モデル（register_model.joblib）+ ルールベースフォールバック
         地声（chest）/ 裏声（falsetto）フレームに分類
      │
      ▼
[STEP 5] フィルタリング・補正 (analysis/pipeline.py)
         ・統計的外れ値除去（パーセンタイル + 半音ギャップ）
         ・裏声ノイズフィルタ（連続フレーム要件 / 最小比率 / RMS パワー）
         ・オクターブ補正
         ・持続音バリデーション（MIN_SUSTAIN_FRAMES=3）
      │
      ▼
[STEP 6] 歌唱力スコアリング (analysis/scoring.py)
         ・overall_score（総合）
         ・range_score（音域の広さ）
         ・stability_score（ピッチ安定性）
         ・expression_score（表現力）
      │
      ▼
[STEP 7] 楽曲推薦 (recommender.py)
         Hz 範囲マッチングで songs.db から最大 10 曲を選出
         ・DISCOVERY_SLOTS=4（お気に入り以外のアーティストから必ず確保）
         ・FAV_MAX_SLOTS=6（お気に入りアーティスト優先枠）
         ・MAX_PER_ARTIST=2（同一アーティスト最大 2 曲）
      │
      ▼
JSON レスポンス返却 + 履歴自動保存（ログイン済みの場合）
```

---

## 6. `config.py` — 解析定数一覧

全ての解析閾値・パラメータは `config.py` のみで管理。他ファイルへのハードコードは禁止。

| 定数 | 値 | 説明 |
|------|----|------|
| `VOICE_MIN_HZ` | 65.0 | 人声絶対下限 (C2付近) |
| `VOICE_MAX_HZ` | 1324.0 | 人声絶対上限 (E6付近) |
| `CREPE_SR` | 16000 | CREPE サンプリングレート |
| `CREPE_HOP_LENGTH` | 160 | 10ms ホップ（高速化） |
| `CONF_THRESHOLDS` | [0.5, 0.35, 0.2, 0.1, 0.05, 0.01] | 信頼度フォールバック閾値 |
| `CONF_MIN_FRAMES` | 5 | 有効フレームの最小数 |
| `CHEST_OUTLIER_PERCENTILE` | 97 | 地声外れ値除去パーセンタイル |
| `CHEST_OUTLIER_GAP_ST` | 3 | 地声外れ値ギャップ（半音） |
| `FALSETTO_OUTLIER_PERCENTILE` | 95 | 裏声外れ値除去パーセンタイル |
| `FALSETTO_OUTLIER_GAP_ST` | 2 | 裏声外れ値ギャップ（半音） |
| `FALSETTO_DISPLAY_MIN_HZ` | 330.0 | 裏声表示下限（mid2E） |
| `FALSETTO_HARD_MIN_HZ` | 270.0 | 地声確定の上限 Hz |
| `CLEANUP_SEMITONES` | 2 | 地声/裏声混在解消幅（半音） |
| `MIN_SUSTAIN_FRAMES` | 3 | 最高音認定の最小フレーム数 |
| `FALSETTO_MIN_CONSECUTIVE` | 5 | 孤立裏声フィルタ（連続フレーム） |
| `FALSETTO_MIN_RATIO` | 0.05 | 裏声最小比率（5%未満は全地声） |
| `FALSETTO_RMS_RATIO` | 0.15 | 残留楽器フィルタ（地声 RMS の 15%未満） |
| `STABILITY_MIN_SEGMENT` | 3 | 安定性評価の最小セグメント |
| `STABILITY_SCALING` | 0.8 | 安定性スコア変換係数 |
| `REGISTER_LOG_LEVEL` | env | 0=なし 1=サマリー 2=間引き 3=全て |

---

## 7. `note_converter.py` — 音階変換

A4 = 442Hz（日本カラオケ標準）基準の対応表 `NOTE_TABLE` を中心に構成。

| 関数 | 説明 |
|------|------|
| `hz_to_label_and_hz(hz)` | Hz → (日本語ラベル, 定義Hz)。対数スケール最近傍探索。 |
| `to_japanese_notation(note)` | 後方互換。"C4" 等の文字列 → 日本語ラベル。 |
| `label_to_rank(label)` | ラベル → NOTE_TABLE インデックス（音高順位）。安定音域計算に使用。 |

**オクターブ対応表（日本語ラベル体系）:**

| NOTE_TABLE オクターブ | プレフィックス | 例 |
|----------------------|---------------|----|
| Octave 1 (C1〜G#1) | `lowlow` | `lowlowC`, `lowlowG#` |
| Octave 1 (A1〜B1) | `low` | `lowA`, `lowB` |
| Octave 2 (C2〜G#2) | `low` | `lowC`, `lowG#` |
| Octave 2 (A2〜B2) | `mid1` | `mid1A`, `mid1B` |
| Octave 3 (C3〜G#3) | `mid1` | `mid1C`, `mid1G#` |
| Octave 3 (A3〜B3) | `mid2` | `mid2A`, `mid2B` |
| Octave 4 (C4〜G#4) | `mid2` | `mid2C`, `mid2G#` |
| Octave 4 (A4〜B4) | `hi` | `hiA`, `hiB` |
| Octave 5 (C5〜G#5) | `hi` | `hiC`, `hiG#` |
| Octave 5 (A5〜B5) | `hihi` | `hihiA`, `hihiB` |
| Octave 6 (C6〜G#6) | `hihi` | `hihiC`, `hihiG#` |
| Octave 6 (A6〜B6) | `hihihi` | `hihihiA`, `hihihiB` |
| Octave 7 (C7〜E7) | `hihihi` | `hihihiC`, `hihihiE` |

---

## 8. `models.py` — Pydantic モデル一覧

| モデル | 用途 |
|--------|------|
| `SignUpRequest` | メール登録リクエスト（email, password, display_name） |
| `SignInRequest` | メールログインリクエスト（email, password） |
| `RefreshTokenRequest` | セッションリフレッシュ（refresh_token） |
| `PasswordResetRequest` | パスワードリセットメール送信（email） |
| `PasswordUpdateRequest` | パスワード更新（new_password、8文字以上） |
| `UserProfileUpdate` | プロファイル更新（display_name / avatar_url / dam_account_id） |
| `VocalRangeUpdate` | 声域更新（vocal_range_min / max / falsetto_max） |
| `AnalysisCreate` | 分析履歴保存（vocal_range_* / source_type / file_name） |
| `AnalysisUpdate` | 分析履歴 file_name 更新 |
| `AnalysisResponse` | 分析履歴レスポンス型 |
| `FavoriteSongAdd` | お気に入り楽曲追加（song_id） |
| `FavoriteSongResponse` | お気に入り楽曲レスポンス型 |
| `FavoriteArtistAdd` | お気に入りアーティスト追加（artist_id, artist_name） |
| `FavoriteArtistResponse` | お気に入りアーティストレスポンス型 |
| `SongResponse` | 楽曲情報レスポンス型 |
| `ArtistResponse` | アーティスト情報レスポンス型 |

---

## 9. `auth.py` — 認証ヘルパー

| 関数 | 説明 |
|------|------|
| `get_current_user(credentials)` | JWT 検証してユーザー情報を返す。`Depends(get_current_user)` で保護エンドポイントに使用。 |
| `get_optional_user(credentials)` | 未ログインでも `None` を返すオプショナル認証。`Depends(get_optional_user)` で任意認証エンドポイントに使用。 |
| `sign_up_with_email(email, password, display_name)` | Supabase Auth でユーザー登録 |
| `sign_in_with_email(email, password)` | Supabase Auth でログイン |
| `sign_out()` | ログアウト |
| `refresh_session(refresh_token)` | セッションリフレッシュ |
| `request_password_reset(email)` | パスワードリセットメール送信 |
| `update_password(user_id, new_password)` | パスワード更新（Admin API） |

Supabase クライアントが `None`（環境変数未設定）の場合、`_ensure_auth_available()` が HTTP 503 を返す。

---

## 10. `db/users.py` — Supabase ユーザーデータ関数

| 関数 | 説明 |
|------|------|
| `get_user_profile(user_id)` | プロファイル取得 |
| `update_user_profile(user_id, data)` | プロファイル更新 |
| `update_vocal_range(user_id, vocal_min, vocal_max, falsetto)` | 現在の声域を更新 |
| `create_analysis_record(user_id, ...)` | 分析履歴を新規作成（result_json 含む） |
| `get_analysis_history(user_id, limit)` | 分析履歴取得（新しい順） |
| `get_analysis_timeline(user_id, limit)` | 分析タイムライン取得（**古い順**・グラフ用） |
| `delete_analysis_record(user_id, record_id)` | 分析履歴削除 |
| `update_analysis_record(user_id, record_id, data)` | 分析履歴更新 |
| `add_favorite_song(user_id, song_id)` | お気に入り楽曲追加 |
| `remove_favorite_song(user_id, song_id)` | お気に入り楽曲削除 |
| `get_favorite_songs(user_id, limit)` | お気に入り楽曲一覧（SQLite と N+1 回避結合） |
| `is_favorite(user_id, song_id)` | お気に入り確認 |
| `add_favorite_artist(user_id, artist_id, artist_name)` | お気に入りアーティスト追加（上限 10 組） |
| `remove_favorite_artist(user_id, artist_id)` | お気に入りアーティスト削除 |
| `get_favorite_artists(user_id, limit)` | お気に入りアーティスト一覧（古い順） |
| `is_favorite_artist(user_id, artist_id)` | お気に入りアーティスト確認 |
| `get_favorite_artist_ids(user_id)` | アーティスト ID リスト取得（recommender 用） |

---

## 11. `recommender.py` — 楽曲推薦・類似アーティスト

| 関数 | 説明 |
|------|------|
| `recommend_songs(chest_min_hz, chest_max_hz, chest_avg_hz, falsetto_max_hz, limit, favorite_artist_ids)` | Hz 範囲マッチングでおすすめ曲を返す |
| `recommend_key_for_song(lowest_note, highest_note, user_min_hz, user_max_hz)` | 1 曲のキー推奨値（±N）と難易度 fit を返す |
| `find_similar_artists(chest_min_hz, chest_max_hz, chest_avg_hz, limit)` | 声が似てるアーティスト一覧を返す |
| `classify_voice_type(chest_min_hz, chest_max_hz, chest_avg_hz, falsetto_max_hz, chest_ratio)` | 声質タイプ（ハイトーン等）を判定 |
| `aggregate_vocal_range(records, favorite_artist_ids)` | 分析履歴複数件から統合音域を計算 |
| `label_to_hz(label)` | カラオケ表記ラベル → Hz 変換（DB の表記揺れも吸収） |

**おすすめ曲配分ルール:**
- `DISCOVERY_SLOTS = 4`：お気に入り以外のアーティストから必ず確保
- `FAV_MAX_SLOTS = 6`：お気に入りアーティストの曲で埋める
- `MAX_PER_ARTIST = 2`：同一アーティスト最大 2 曲（多様性確保）

**音階表記の互換処理（DB の表記揺れ対策）:**
- `mid1A` / `mid1A#` / `mid1B` → `mid2A` / `mid2A#` / `mid2B` と同周波数にマッピング
- `loX` → `lowX` の表記揺れを吸収

---

## 12. 安定音域アルゴリズム（成長グラフ機能）

`GET /analysis/timeline` エンドポイント（`routers/users.py`）が実装。

```
直近 N 件（デフォルト 40 件）の分析履歴から各ラベルの出現回数を集計。

STABLE_THRESHOLD = 4 回以上出現したラベルのうち:
  stable_chest_max  = label_to_rank() で最高音を選択
  stable_chest_min  = label_to_rank() で最低音を選択
  stable_falsetto_max = label_to_rank() で最高音を選択

label_to_rank() は NOTE_TABLE のインデックス（0 = lowlowC）を音高順位として使用。
```

---

## 13. フロントエンド ディレクトリ構成

```
frontend/src/
├── index.tsx                    # エントリポイント
├── App.tsx                      # ルートコンポーネント（Suspense / レイアウト）
├── routes.tsx                   # useRoutes() によるルート定義（全ルート lazy ロード）
├── supabaseClient.ts            # Supabase クライアント初期化（null 安全）
│
├── contexts/
│   ├── AuthContext.tsx           # 認証状態（user / isAuthenticated / login / logout）
│   ├── AnalysisContext.tsx       # 解析進捗 UI（タイマー制御のステップ表示）
│   └── AppContext.tsx            # アプリ全体状態（userRange を localStorage に永続化）
│
├── api/
│   ├── client.ts                 # Axios インスタンス（JWT 自動付与インターセプター）
│   ├── types.ts                  # API 型定義（AnalysisResult / Song / TimelinePoint 等）
│   ├── analysis.ts               # /analyze, /analyze-karaoke ラッパー
│   ├── songs.ts                  # /songs, /artists ラッパー
│   ├── listApi.ts                # /analysis/history, /favorites, /favorite-artists ラッパー
│   ├── totalRange.ts             # /analysis/integrated-range, /analysis/timeline ラッパー
│   ├── auth.ts                   # /auth/* ラッパー
│   ├── error.ts                  # エラーメッセージ変換ユーティリティ
│   └── index.ts                  # バレル（全モジュール re-export）
│
├── pages/                        # ページコンポーネント（Context 非依存）
│   ├── LandingPage.tsx
│   ├── HomePage.tsx
│   ├── RecordingPage.tsx
│   ├── HistoryPage.tsx           # 分析履歴一覧 + 声域成長グラフ
│   ├── AnalysisResultPage.tsx
│   ├── SongListPage.tsx
│   ├── FavoritesPage.tsx
│   ├── MyPage.tsx
│   ├── GuidePage.tsx
│   ├── LoginPage.tsx
│   ├── PasswordResetPage.tsx
│   └── PasswordChangePage.tsx
│
├── routeWrappers/                # Context → ページへの Props ブリッジ
│   ├── PasswordResetRoute.tsx
│   └── PasswordChangeRoute.tsx
│
├── components/
│   ├── layout/
│   │   ├── Layout.tsx            # 共通レイアウト（Header / BottomNav / Suspense）
│   │   ├── Header.tsx
│   │   └── BottomNav.tsx
│   ├── features/
│   │   ├── Recorder.tsx          # マイク録音 + 波形ビジュアライザー
│   │   ├── KaraokeUploader.tsx   # カラオケ音源アップロード
│   │   ├── ResultView.tsx        # 分析結果表示
│   │   └── VocalGrowthChart.tsx  # 声域成長折れ線グラフ（Recharts）
│   └── ui/                       # 汎用 UI コンポーネント群
│
├── hooks/
│   └── useToast.ts               # トースト通知カスタムフック
│
└── assets/
    └── logo.png
```

---

## 14. フロントエンド API 型定義（主要なもの）

```typescript
// api/types.ts

interface AnalysisResult {
  overall_min: string; overall_max: string;
  overall_min_hz: number; overall_max_hz: number;
  chest_min?: string; chest_max?: string;
  chest_min_hz?: number; chest_max_hz?: number;
  falsetto_min?: string; falsetto_max?: string;
  falsetto_max_hz?: number;
  singing_analysis?: SingingAnalysis;
  voice_type?: VoiceType;
  recommended_songs?: RecommendedSong[];
  similar_artists?: SimilarArtist[];
}

interface AnalysisHistoryRecord {
  id: string; user_id: string;
  vocal_range_min: string | null; vocal_range_max: string | null;
  falsetto_max: string | null;
  source_type: string; file_name: string | null;
  created_at: string;
  result_json?: AnalysisResult | null;
}

// 成長グラフ用
interface TimelinePoint {
  date: string;
  chest_min: string | null; chest_max: string | null;
  falsetto_max: string | null;
  chest_min_hz: number | null; chest_max_hz: number | null;
  falsetto_max_hz: number | null;
}
interface StableRange {
  chest_min: string | null; chest_max: string | null; falsetto_max: string | null;
}
interface AnalysisTimeline {
  timeline: TimelinePoint[]; stable_range: StableRange;
}
```

---

## 15. 認証フロー

```
【Google OAuth】
  ユーザー → loginWithGoogle() → supabase.auth.signInWithOAuth({ provider: "google" })
           → Google 認証画面 → リダイレクト後 onAuthStateChange 発火
           → JWT を Axios インターセプターで自動付与

【メール認証】
  ユーザー → /auth/signup (バックエンド) → メール確認
  ユーザー → /auth/signin (バックエンド) → access_token / refresh_token 取得
           → フロントが supabase.auth.setSession() でセッション確立

【パスワードリセット】
  /auth/reset-password → Supabase がリセットメール送信
  リセットリンク踏む → PasswordResetPage / PasswordChangePage
  /auth/update-password (要 JWT) → Supabase Admin API でパスワード更新

【Supabase null ガード】
  supabaseClient.ts は環境変数未設定の場合 null を返す。
  auth.py の _ensure_auth_available() が null チェックして HTTP 503 を返す。
  → 認証機能なしでも楽曲検索・解析のみ動作可能。
```

---

## 16. デュアルデータベース設計

### SQLite (`backend/songs.db`)

- 約 5000 曲、約 850 アーティスト
- コミット済み・実行時は**読み取り専用**
- スキーマ: `songs` テーブル（id, title, artist, artist_id, lowest_note, highest_note, falsetto_note, note, source）
- `artists` テーブル（id, name, slug, reading, song_count）
- 再構築: `rm -f songs.db && python scraper.py`

### Supabase (PostgreSQL)

- スキーマ: `backend/supabase_migration.sql`
- 主要テーブル:
  - `user_profiles`：display_name, current_vocal_range_*, avatar_url
  - `analysis_history`：vocal_range_*, falsetto_max, source_type, file_name, result_json (JSONB)
  - `favorite_songs`：user_id, song_id
  - `favorite_artists`：user_id, artist_id, artist_name

---

## 17. ミドルウェア・設定（`main.py`）

| 設定 | 内容 |
|------|------|
| アップロード上限 | 50MB（`MAX_UPLOAD_BYTES`）。Content-Length ヘッダーと実測サイズの両方でチェック。 |
| CORS | `ALLOWED_ORIGINS` 環境変数でカンマ区切り指定。未設定時は `localhost:3000` のみ。 |
| ルーター登録 | `auth.router`, `users.router`, `songs.router`, `analysis.router`（プレフィックスなし、`/auth/` のみ `/auth` プレフィックス付き） |
| lifespan | 起動時に `db/songs.py` の `init_db()` を呼び出し SQLite を初期化。 |

---

## 18. ログ規則

| 接頭辞 | 用途 |
|--------|------|
| `[API]` | エンドポイント受付・完了ログ |
| `[STEP X/Y]` | 音声解析パイプラインの進捗 |
| `[DEBUG]` | 詳細情報（閾値・フレーム数等） |
| `[INFO]` | 処理サマリー（音域検出結果等） |
| `[WARN]` | 非致命的な警告（お気に入り取得失敗等） |
| `[ERROR]` | 致命的なエラー（認証失敗・例外等） |

---

## 19. 開発環境セットアップ

### バックエンド

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # ← 必須（Homebrew uvicorn と競合する）
pip install -r requirements.txt
cp .env.example .env              # SUPABASE_URL, SUPABASE_KEY 等を設定
uvicorn main:app --reload         # http://localhost:8000
curl http://localhost:8000/health # ヘルスチェック
```

### フロントエンド

```bash
cd frontend
npm install
cp .env.example .env              # REACT_APP_SUPABASE_URL 等を設定
npm start                         # http://localhost:3000
npm run build                     # 本番ビルド → frontend/build/
npm test -- --watchAll=false      # CI モードでテスト一括実行
```

### 環境変数

**バックエンド (`backend/.env`)**

```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=<anon-key>
JWT_SECRET=<secret-key>
REGISTER_LOG_LEVEL=1     # 0=none 1=summary 2=decimated 3=all
ALLOWED_ORIGINS=https://pitchscout.ten-hou.com,http://localhost:3000
```

**フロントエンド (`frontend/.env`)**

```
REACT_APP_SUPABASE_URL=https://xxx.supabase.co
REACT_APP_SUPABASE_ANON_KEY=<anon-key>
REACT_APP_API_URL=        # 省略可。開発時は localhost:8000、本番では /api
```

> 環境変数が未設定でも楽曲検索・音声解析は動作する（認証機能のみ無効）。

---

## 20. デプロイ・運用

詳細: `QUICKSTART.md`, `DEPLOYMENT.md`, `GoogleCloud/` を参照。

- **Nginx**: `nginx-pitchscout.conf` でフロントエンド静的ファイルと `/api` のプロキシを設定
- **本番 CORS**: `ALLOWED_ORIGINS` 環境変数で必要最小限のオリジンに制限する
- **ffmpeg**: システム依存（音声変換に必須）
- **GPU**: Demucs は GPU があれば自動利用（なければ CPU フォールバック）
