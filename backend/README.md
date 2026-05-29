# Backend API

PitchScout の FastAPI バックエンドです。音声変換、ボーカル分離、声域解析、楽曲検索、推薦、認証済みユーザーデータの保存を担当します。

## セットアップ

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip wheel
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

サーバーは `http://127.0.0.1:8000` で起動します。

`backend/.env`:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-backend-supabase-key-here
JWT_SECRET=<generated-secret>
MAX_CONCURRENT_VOICE_ANALYSES=2
MAX_CONCURRENT_KARAOKE_ANALYSES=1
PITCHSCOUT_SAVE_DEBUG_AUDIO=false
```

`SUPABASE_KEY` はバックエンド専用です。service role など強いキーを使う場合は、絶対にフロントエンドへ渡さず、`backend/.env` もコミットしないでください。

## 起動時に初期化するもの

- SQLite 楽曲 DB (`songs.db`)
- DeepFilterNet3
- Silero VAD

DeepFilterNet の依存がない環境では警告を出して処理を継続します。Python 3.12 系では DeepFilterNet が有効、Python 3.14 系では audio-separator 新版を優先する依存構成です。

## 運用上の保護

- `/analyze` と `/analyze-karaoke` は同期エンドポイントとして threadpool で実行されます。
- `MAX_CONCURRENT_VOICE_ANALYSES` と `MAX_CONCURRENT_KARAOKE_ANALYSES` で、プロセスごとの同時解析数を制限します。
- 上限に達した場合は `429` を返します。
- `PITCHSCOUT_SAVE_DEBUG_AUDIO=false` が既定です。ユーザー音声を含む WAV を保存するため、本番では有効化しないでください。

## 音声解析

| エンドポイント | 用途 | 処理 |
|----------------|------|------|
| `POST /analyze` | アカペラ・マイク録音 | 16kHz mono WAV 変換 -> WORLD -> AP/HNR + RandomForest |
| `POST /analyze-karaoke` | BGM 付きカラオケ音源 | 44.1kHz stereo WAV 変換 -> MelBandRoformers -> DeepFilterNet -> WORLD -> AP/HNR + RandomForest |

どちらも `multipart/form-data` で `file` を受け取り、任意で `no_falsetto` を指定できます。ログイン済みユーザーの JWT があれば、分析履歴も保存します。

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -F "file=@recording.webm"
```

```bash
curl -X POST http://127.0.0.1:8000/analyze-karaoke \
  -F "file=@karaoke.mp3"
```

## 楽曲 API

| メソッド | パス | 説明 |
|----------|------|------|
| `GET` | `/songs` | 楽曲一覧・検索・音域フィルタ |
| `GET` | `/artists` | アーティスト一覧・検索 |
| `GET` | `/artists/{artist_id}/songs` | アーティスト別楽曲一覧 |
| `GET` | `/recommend` | 声域に合うおすすめ曲 |
| `GET` | `/recommend/challenge` | 少し背伸びするチャレンジ曲 |
| `GET` | `/similar-artists` | 声域が近いアーティスト |

### 楽曲検索

```bash
curl "http://127.0.0.1:8000/songs?q=Lemon&limit=20"
```

`q` は曲名、アーティスト名、ふりがなに部分一致します。音域パラメータを付けるとキー推薦情報を付与できます。

```bash
curl "http://127.0.0.1:8000/songs?chest_min_hz=130&chest_max_hz=440&falsetto_max_hz=659&filter_by_range=true"
```

### おすすめ曲

```bash
curl "http://127.0.0.1:8000/recommend?chest_min_hz=130&chest_max_hz=440&chest_avg_hz=220&falsetto_max_hz=659&limit=10"
```

ログイン済みの場合は、お気に入りアーティストを優先しつつ、ディスカバリー枠を残して推薦します。

### チャレンジ曲

```bash
curl "http://127.0.0.1:8000/recommend/challenge?chest_min_hz=130&chest_max_hz=440&chest_avg_hz=220&falsetto_max_hz=659&limit=5"
```

通常推薦の下限より少し難しい曲のうち、低音・高音ペナルティが現実的な範囲のものを返します。

## 認証・ユーザー API

| メソッド | パス | 説明 |
|----------|------|------|
| `POST` | `/auth/signup` | メール登録 |
| `POST` | `/auth/signin` | ログイン |
| `POST` | `/auth/signout` | ログアウト |
| `POST` | `/auth/refresh` | セッション更新 |
| `POST` | `/auth/reset-password` | パスワードリセットメール送信 |
| `POST` | `/auth/update-password` | パスワード更新 |
| `GET/PUT` | `/profile/me` | プロファイル取得・更新 |
| `PUT` | `/profile/vocal-range` | 現在の声域更新 |
| `GET` | `/analysis/history` | 分析履歴 |
| `GET` | `/analysis/integrated-range` | 統合声域 |
| `GET` | `/analysis/timeline` | 声域タイムライン |
| `GET` | `/analysis/growth` | 成長指標 |
| `GET/POST` | `/favorites` | お気に入り楽曲 |
| `GET/POST` | `/favorite-artists` | お気に入りアーティスト |

## 楽曲データベース

`songs.db` は同梱済みなので通常は再構築不要です。現在の DB には 5,428 曲・858 アーティストが含まれます。

| ソース | 曲数 |
|--------|------|
| voice-key.news | 3,871 |
| vocal-range.com | 1,557 |

更新する場合:

```bash
cd backend
rm -f songs.db
python scraper.py
python scraper_vocal_range.py
python update_all_readings.py
```

## モデル再学習

```bash
cd backend
source venv/bin/activate
python ml/train.py \
  --dataset-root ml/vocalset_data/FULL \
  --manifest ml/training_data/vocalset_manifest.csv
```

主な出力:

- `ml/models/register_model.joblib`
- `ml/training_data/world_dataset.npz`

## ヘルスチェック

```bash
curl http://127.0.0.1:8000/health
```

```json
{ "status": "ok" }
```
