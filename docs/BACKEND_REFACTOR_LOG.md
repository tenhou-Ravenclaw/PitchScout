# バックエンド 修正ログ & 実装機能一覧

> 本ドキュメントは `back-daikaizou` ブランチで行った全修正の記録です。

---

## 修正ログ

### 第1フェーズ — セキュリティ・バリデーション強化

#### `routers/analysis.py` — ファイルアップロード検証の全面強化

| 修正内容 | 詳細 |
|---------|------|
| マジックバイト検証を非同期化 | `_validate_upload_file()` を `async def` に変更し `await file.seek(0)` に対応 |
| WAV 二重チェック | `RIFF`（bytes 0-3）と `WAVE`（bytes 8-11）の両方を検証。従来は RIFF のみだった |
| `_MAGIC_SIGNATURES` テーブル導入 | MP3 / FLAC / OGG / WebM / MP4 系のシグネチャを一元管理 |
| リクエスト独立ディレクトリ | Demucs 出力先を `separated/{uuid}/` にして並行リクエスト間のファイル混同を防止 |
| `except HTTPException: raise` 追加 | バリデーションの 400 エラーが generic `except Exception` に飲み込まれて 500 になるのを防止 |
| `or ".tmp"` フォールバック削除 | バリデーション通過後は必ず有効な拡張子が存在するため死コードを除去 |
| ログ絵文字除去 | `[API] [1/3] ...` 形式に統一 |

#### `audio/separator.py` — Demucs 事前チェック追加

- `shutil.which("demucs")` で `demucs` コマンドの存在を事前確認し、見つからない場合は明示的な `RuntimeError` を送出
- エラー時のメッセージに全検索パスを列挙するよう修正（デバッグ性向上）
- mode_label の絵文字（`⚡🚀💎`）を除去し、ログ表記を統一

#### `audio/converter.py` — ffmpeg null チェック追加

- `convert_to_wav()` / `convert_to_wav_hq()` の両関数で `find_ffmpeg()` 直後に null チェックを追加
- 従来は `cmd = [None, ...]` を組んでから `_run_ffmpeg()` 内部で検出していたため、早期に明示的エラーを出すよう改善

---

### 第2フェーズ — 解析パイプライン バグ修正

#### `analysis/pipeline.py` — 最高音認定バグ修正 & ログ統一

- **バグ修正**: 最高音候補の信頼度フォールバックループで `mask_max.sum() >= 1` だったのを `>= MIN_SUSTAIN_FRAMES` に修正。孤立ノイズを最高音として誤採用するケースを防止
- **ログ統一**: 全18箇所の絵文字（`✅ ⚠️ ❌ 🎵 📁 🔧 🎼 🎯 📊 🎤 📋`）を除去し `[STEP X/7]` / `[INFO]` / `[WARN]` / `[ERROR]` / `[DEBUG]` の接頭辞に統一

#### `audio/noise.py` — VAD フォールバック警告のスパム防止

- `_vad_fallback_warned` フラグを追加し、Silero VAD 未初期化時の警告を初回1回のみ出力するよう変更（フレームごとに出力されていた問題を修正）

---

### 第3フェーズ — DB 堅牢化 & ML モデル最適化

#### `db/users.py` — 全関数に try-except 追加

以下10関数にエラーハンドリングを追加。Supabase 一時障害や接続エラー時にも安全なデフォルト値を返す：

| 関数 | エラー時の返り値 |
|------|----------------|
| `get_user_profile()` | `None` |
| `update_user_profile()` | `None` |
| `create_analysis_record()` | `None` |
| `get_analysis_history()` | `[]` |
| `get_analysis_timeline()` | `[]` |
| `get_favorite_songs()` | `[]` |
| `is_favorite()` | `False` |
| `batch_check_favorites()` | `{song_id: False, ...}` |
| `get_favorite_artists()` | `[]` |
| `is_favorite_artist()` | `False` |

#### `routers/users.py` — write 系エンドポイントのエラー変換

DB 関数が `None` を返した際に正しく 500 エラーを返すよう修正：

- `PUT /profile/me` → `update_user_profile()` が `None` の場合 `HTTPException(500)`
- `PUT /profile/vocal-range` → `update_vocal_range()` が `None` の場合 `HTTPException(500)`
- `POST /analysis` → `create_analysis_record()` が `None` の場合 `HTTPException(500)`

#### `analysis/classifier.py` — ML モデル更新チェックのスロットリング

- `import time` を追加
- `_last_check_time: float = 0.0` / `_CHECK_INTERVAL: float = 30.0` をモジュール変数に追加
- `_load_model_if_needed()` にタイムベーススロットリングを実装。フレームごとに `os.path.exists()` + `os.path.getmtime()` が呼ばれていた問題（数千回/解析ファイル）を解消し、30秒間隔でのみディスクチェックを実行

---

### 第4フェーズ — 細部修正

#### `analysis/features.py` — HNR 計算失敗ログ追加 & FFT サイズ統一

- `compute_hnr()` の `except Exception` で例外情報が消えていた問題を修正。`[WARN] HNR計算失敗` ログを追加
- `n_fft = 8192` のハードコードを `FFT_SPECTRUM_SIZE`（`config.py` の定数）参照に変更。`classifier.py` の `_classify_rules()` と FFT 解像度が一致するよう統一

#### `analysis/scoring.py` — STABILITY_SCALING ゼロ設定ガード

- `max(STABILITY_SCALING, 0.01)` クランプを追加。`STABILITY_SCALING = 0` に誤設定された場合に安定性スコアが常に 100 になる問題を防止

#### `recommender.py` — フォールバック互換性ヘルパー追加

- `_get_falsetto_min_hz_from_result()` ヘルパー関数を追加。旧形式（`falsetto_min` ラベル）と新形式（`falsetto_min_hz` Hz値）の両方に対応した統合音域集計を実現

#### `config.py` — コメント・ドキュメント改善

- `REGISTER_LOG_LEVEL` のデフォルト値コメントを修正（level 1 がデフォルトであることを明記）
- `GRADUATED_CONF_FAR/MID/NEAR`、`FALSETTO_RATIO_HIGH/MID/DEFAULT`、各フィルタ定数に設計根拠コメントを追加
- `REGISTER_LOG_INTERVAL` に「1フレーム = 20ms → デフォルト 100フレーム ≈ 2秒」の計算根拠を追記

#### `routers/songs.py` — メモリ上限ガード

- `filter_by_range=True` 時の全件取得に `[:_MAX_FILTER_SONGS]`（= 20000件）の安全上限を追加。DB 拡張時のメモリ圧迫を防止

#### `.gitignore` — デバッグファイルを追跡対象外に

- `debug_falsetto/` ディレクトリと `debug_falsetto_audio.py` を追加

---

## 実装済み機能一覧

### 認証・ユーザー管理

- **Supabase JWT 認証**: HTTPヘッダーから自動抽出、SDK による署名検証
- **オプショナル認証**: 未ログインでもアクセス可能なエンドポイント（`get_optional_user`）
- **メール/パスワード認証**: 登録・ログイン・ログアウト・セッションリフレッシュ
- **パスワードリセット**: メール送信フロー
- **Nullable Supabase**: 環境変数未設定時は認証なしでアプリが継続起動

### ファイルアップロード・セキュリティ

- **3層バリデーション**: 拡張子 → MIME タイプ → マジックバイト の順で検証
- **WAV 二重チェック**: `RIFF`（bytes 0-3）と `WAVE`（bytes 8-11）の両方を確認
- **シグネチャ検証**: MP3 / FLAC / OGG / WebM / MP4 / M4A / MOV をシグネチャテーブルで照合
- **Content-Type スプーフィング対策**: MIME と拡張子の一致確認
- **50MB サイズ制限**: リクエストボディの最大サイズ制御

### 音声処理パイプライン

- **2エンドポイント方式**:
  - `POST /analyze` — マイク録音/アカペラ（Demucs なし、16kHz モノラル変換）
  - `POST /analyze-karaoke` — カラオケ音源（Demucs 分離あり、44.1kHz ステレオ変換）
- **ボーカル分離**: Demucs 3モデル選択（`htdemucs_6s` 超高速 / `htdemucs` 高速 / `htdemucs_ft` 高品質）
- **ノイズ除去**: DeepFilterNet3（残留楽器除去）+ Silero VAD（フレーム単位の歌声スコアリング）
- **ピッチ検出**: torchcrepe（`weighted_argmax` → `viterbi` → なし の順に自動フォールバック）
- **GPU 自動選択**: CUDA → MPS（Apple Silicon）→ CPU の優先順位でフォールバック

### 音域解析エンジン

- **段階的信頼度要求**: 中央値から遠い音程ほど高い信頼度を要求（外れ値除去の精度向上）
- **地声/裏声 ML 判定**: scikit-learn モデル + ルールベースフォールバック（mtime ホットリロード、30秒スロットリング）
- **倍音特徴量**: H1-H2差・倍音本数・倍音スロープ・HNR・スペクトル重心の6特徴量
- **裏声ノイズフィルタ（5段階）**:
  1. 連続フレーム要件（100ms 未満の孤立群を除去）
  2. 最小比率フィルタ（全体の 1% 未満は地声に再分類）
  3. RMS パワーフィルタ（地声中央 RMS の 15% 未満を除去）
  4. Silero VAD フィルタ（フレーム単位の音声スコア閾値）
  5. 救済ロジック（地声 P97 + 4半音以内は高音地声として復帰）
- **外れ値除去**: パーセンタイルベース + 孤立フレーム除去
- **オクターブ補正**: FFT スペクトル照合で CREPE の 1オクターブ低検出を修正
- **最高音堅牢化**: `MIN_SUSTAIN_FRAMES` フレーム以上持続しない音は最高音から除外

### 歌唱力スコアリング

| 軸 | 重み | 計算方法 |
|----|------|---------|
| 音域広さ | 30% | 半音数 / 30半音 × 100（30半音でプロ級） |
| ピッチ安定性 | 45% | 持続音セグメント内のセント標準偏差の加重平均 |
| 表現力 | 25% | 声区使い分け度（diversity）+ 音域活用度（IQR） |
| **総合スコア** | — | 加重平均 |

### 楽曲推薦システム

- **通常推薦** (`/recommend`): Hz 範囲マッチング（低音ペナルティ ×6 / 高音 ×8 / 中心差 ×2）
- **チャレンジ推薦** (`/recommend/challenge`): あと 1〜5 半音で届く曲
- **キー変更推薦**: ±7半音の範囲で最適キーを算出（fit: perfect / good / ok / hard）
- **アーティスト多様性**: 同一アーティスト最大 2 曲
- **お気に入りアーティスト優先**: DISCOVERY_SLOTS（4曲）で他アーティスト、FAV_MAX_SLOTS（6曲）でお気に入り枠
- **似たアーティスト検索** (`/similar-artists`): 全楽曲中央値ベースの音域類似度

### 声質タイプ判定

8 分類（ハイトーン・ミックス / パワフル・ハイトーン / ミドル・ミックス / バリトン・ミックス / ハイトーン・パワー / ミドル・パワー / バリトン・パワー / テノール・バランス）

### ユーザー機能

| 機能 | エンドポイント |
|------|--------------|
| プロファイル取得・更新 | `GET/PUT /profile/me` |
| 声域情報更新 | `PUT /profile/vocal-range` |
| 分析履歴一覧 | `GET /analysis/history` |
| 分析履歴削除・更新 | `DELETE/PATCH /analysis/history/{id}` |
| 統合音域（複数履歴集計） | `GET /analysis/integrated-range` |
| タイムライン（グラフ用） | `GET /analysis/timeline` |
| 音域成長サマリー | `GET /analysis/growth` |
| お気に入り楽曲 CRUD | `GET/POST/DELETE /favorites` |
| お気に入り楽曲 一括確認 | `POST /favorites/batch-check` |
| お気に入りアーティスト CRUD | `GET/POST/DELETE /favorite-artists` |
| お気に入りアーティスト確認 | `GET /favorite-artists/check/{id}` |

- **自動履歴保存**: ログイン済みユーザーの解析結果を自動的に履歴へ記録、声域プロファイルも自動更新
- **タイムライン安定音域**: 直近 N 件中 4 回以上出現したラベルを確定済みとして返却
- **N+1 回避**: `get_songs_by_ids()` による楽曲一括取得、`batch_check_favorites()` による一括お気に入り確認

### データベース

| DB | 用途 | 特徴 |
|----|------|------|
| SQLite (`songs.db`) | 楽曲カタログ（約5000曲、約850アーティスト） | 実行時は読み取り専用。再構築: `rm -f songs.db && python scraper.py` |
| Supabase | 認証・ユーザーデータ・分析履歴・お気に入り | クラウド PostgreSQL。スキーマ: `supabase_migration.sql` |

- **カタカナ対応検索**: NFKC 正規化 + ひらがな変換（U+30A1〜U+30F6）で読み仮名検索
- **LIKE エスケープ**: `%` / `_` を適切にエスケープ

### 設定管理 (`config.py`)

全解析パラメータを一元管理。チューニング時は `config.py` のみを変更すればよい設計：

- 音高検出（VOICE_MIN/MAX_HZ、CREPE_SR、CREPE_HOP_LENGTH）
- 信頼度フィルタリング閾値（CONF_THRESHOLDS、CONF_MIN_FRAMES）
- 外れ値除去パラメータ（パーセンタイル、半音ギャップ）
- 段階的信頼度（GRADUATED_CONF_FAR/MID/NEAR）
- 裏声ノイズフィルタ各種閾値（MIN_CONSECUTIVE、MIN_RATIO、RMS_RATIO）
- DeepFilterNet 減衰上限（DFN_ATTENUATION_LIMIT_DB）
- Silero VAD 閾値（SILERO_VAD_THRESHOLD）
- FFT サイズ（FFT_SPECTRUM_SIZE）— `classifier.py` と `features.py` で共有
- お気に入りアーティスト上限（FAVORITE_ARTIST_LIMIT）
- ログレベル（REGISTER_LOG_LEVEL: 0=なし / 1=サマリー / 2=間引き / 3=全て）

### ログ・デバッグ

- **接頭辞統一**: `[API]` / `[STEP X/Y]` / `[INFO]` / `[DEBUG]` / `[WARN]` / `[ERROR]` / `[FILTER]`
- **絵文字なし**: 全本番コードからログ絵文字を除去済み（ログ解析ツールでの処理を容易化）
- **VAD 初期化警告**: 未初期化時は初回のみ警告（毎フレーム出力のスパム防止）
- **ML モデル状態**: 起動時1回、および初回解析時に使用モデルとパスをログ出力

### エラーハンドリング方針

- **HTTP ステータス統一**: バリデーションエラー 400 / 認証エラー 401 / 未認証 403 / 未発見 404 / 解析失敗 422 / 内部エラー 500 / Supabase 未設定 503
- **HTTPException の保護**: `except HTTPException: raise` を解析エンドポイントの `except Exception` より前に配置し、400 エラーが 500 に化けることを防止
- **DB エラー安全返却**: `db/users.py` の全関数が try-except を持ち、エラー時は空リスト / False / None を返却
- **音声処理フォールバック**: DeepFilterNet 失敗 → Demucs 出力そのまま使用。torchcrepe デコーダー失敗 → 次のデコーダーに自動切り替え
