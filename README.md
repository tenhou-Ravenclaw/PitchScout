# PitchScout

> 声域を分析し、カラオケで歌いやすい曲とキーを探す Web アプリケーション。

本番環境: https://pitch-scout.vercel.app/

![プロダクトイメージ](homePage.png)

## 概要

PitchScout は、マイク録音やカラオケ音源から地声・裏声の音域を分析し、楽曲データベースと照合して歌いやすい曲を推薦するサービスです。

カラオケで「サビが高すぎた」「自分に合う曲がわからない」「毎回同じ曲になる」という悩みに対して、声域の可視化、キー変更提案、分析履歴、お気に入り管理をまとめて提供します。

## 主な機能

| 機能 | 内容 |
|------|------|
| マイク録音分析 | ブラウザのマイクで録音したアカペラ音声を分析 |
| カラオケ音源分析 | BGM 付き音源をアップロードし、ボーカル分離後に声域を分析 |
| ファイルアップロード分析 | WAV, MP3, M4A, FLAC, WebM, MP4, MOV などを分析 |
| 地声/裏声分類 | WORLD 特徴、AP/HNR ゲート、RandomForest で声区を推定 |
| 楽曲推薦 | 声域マッチ度順に曲を推薦し、推奨キー変更値を付与 |
| チャレンジ曲提案 | 少し練習すれば届く範囲の曲を提案 |
| 類似アーティスト検索 | 音域が近いアーティストを提示 |
| 分析履歴 | ログイン時に分析結果を保存し、声域の変化を確認 |
| お気に入り | 楽曲・アーティストを保存し、推薦時に優先表示 |

## 分析パイプライン

### `/analyze`

```text
音声ファイル
  -> ffmpeg で 16kHz mono WAV へ変換
  -> WORLD 特徴抽出 (F0 / SP / AP)
  -> AP/HNR ゲート + RandomForest で地声/裏声判定
  -> 音域・スコア・推薦結果を返却
```

### `/analyze-karaoke`

```text
音声ファイル
  -> ffmpeg で 44.1kHz stereo WAV へ変換
  -> MelBandRoformers でボーカル分離
  -> DeepFilterNet で残留ノイズ除去
  -> WORLD 特徴抽出
  -> AP/HNR ゲート + RandomForest で地声/裏声判定
  -> 音域・スコア・推薦結果を返却
```

## 技術スタック

| レイヤー | 技術 |
|----------|------|
| フロントエンド | React 19, TypeScript, React Router, Tailwind CSS, Axios, Recharts |
| 認証 | Supabase Auth |
| バックエンド | FastAPI, Uvicorn, Pydantic |
| 音声変換 | ffmpeg |
| ボーカル分離 | audio-separator / MelBandRoformers |
| ノイズ除去 | DeepFilterNet3, Silero VAD |
| 解析 | pyworld, librosa, soundfile, NumPy |
| 声区分類 | scikit-learn, joblib, RandomForest |
| データ | SQLite (`backend/songs.db`), Supabase PostgreSQL |

## 楽曲データベース

同梱の SQLite DB には、現在 5,428 曲・858 アーティストの音域データが入っています。

| ソース | 曲数 |
|--------|------|
| voice-key.news | 3,871 |
| vocal-range.com | 1,557 |

保持している情報は、曲名、アーティスト名、最低音、地声最高音、裏声最高音、出典です。音源や歌詞は含みません。

## API

| カテゴリ | パス | メソッド | 認証 |
|----------|------|----------|------|
| health | `/health` | GET | 不要 |
| auth | `/auth/signup` | POST | 不要 |
| auth | `/auth/signin` | POST | 不要 |
| auth | `/auth/signout` | POST | 必要 |
| auth | `/auth/refresh` | POST | 不要 |
| auth | `/auth/reset-password` | POST | 不要 |
| auth | `/auth/update-password` | POST | 必要 |
| analysis | `/analyze` | POST | 任意 |
| analysis | `/analyze-karaoke` | POST | 任意 |
| songs | `/songs` | GET | 不要 |
| songs | `/artists` | GET | 不要 |
| songs | `/artists/{artist_id}/songs` | GET | 不要 |
| songs | `/recommend` | GET | 任意 |
| songs | `/recommend/challenge` | GET | 不要 |
| songs | `/similar-artists` | GET | 不要 |
| users | `/profile/me` | GET/PUT | 必要 |
| users | `/profile/vocal-range` | PUT | 必要 |
| users | `/analysis/history` | GET | 必要 |
| users | `/analysis/integrated-range` | GET | 必要 |
| users | `/analysis/timeline` | GET | 必要 |
| users | `/analysis/growth` | GET | 必要 |
| users | `/favorites` | GET/POST | 必要 |
| users | `/favorite-artists` | GET/POST | 必要 |

## セットアップ

### 前提条件

- Node.js 18+
- Python 3.12 推奨
- ffmpeg
- Supabase プロジェクト（認証・履歴機能を使う場合）

Python 3.14 系でも依存関係は分岐していますが、DeepFilterNet は現状 Python 3.12 系で有効です。

### バックエンド

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip wheel
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

`backend/.env`:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-backend-supabase-key-here
JWT_SECRET=<generated-secret>
MAX_CONCURRENT_VOICE_ANALYSES=2
MAX_CONCURRENT_KARAOKE_ANALYSES=1
PITCHSCOUT_SAVE_DEBUG_AUDIO=false
```

`SUPABASE_KEY` はバックエンド専用です。service role など強いキーを使う場合は、絶対にフロントエンドへ渡さず、`backend/.env` もコミットしないでください。`PITCHSCOUT_SAVE_DEBUG_AUDIO` はユーザー音声を保存するため、本番では `false` のままにします。

### フロントエンド

```bash
cd frontend
npm install
npm start
```

`frontend/.env`:

```env
REACT_APP_API_URL=http://127.0.0.1:8000
REACT_APP_SUPABASE_URL=https://your-project-ref.supabase.co
REACT_APP_SUPABASE_ANON_KEY=your-anon-key-here
```

開発時のフロントエンドは `http://localhost:3000`、バックエンドは `http://127.0.0.1:8000` で起動します。

## 楽曲 DB の更新

`backend/songs.db` はリポジトリに含まれているため、通常の起動では再構築不要です。データを更新する場合は、バックエンドの仮想環境を有効化したうえで実行します。

```bash
cd backend
rm -f songs.db
python scraper.py
python scraper_vocal_range.py
python update_all_readings.py
```

## ドキュメント

- [プロジェクト概要](docs/PROJECT_OVERVIEW.md)
- [アーキテクチャ](docs/ARCHITECTURE.md)
- [デプロイ手順](docs/DEPLOYMENT.md)
- [バックエンド README](backend/README.md)
- [フロントエンド README](frontend/README.md)

## ライセンス

MIT License
