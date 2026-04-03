# Backend API

声域解析と楽曲音域検索を提供する FastAPI バックエンド。

## セットアップ

```bash
cd backend

# 仮想環境の作成と有効化
python3 -m venv venv
source venv/bin/activate

# ビルド系ツール更新
python -m pip install --upgrade pip wheel

# pyworld は環境依存で build isolation 失敗があるため先に導入
python -m pip install "setuptools<81"
pip install pyworld --no-build-isolation

# 依存関係インストール
pip install -r requirements.txt

# サーバー起動
uvicorn main:app --reload
```

サーバーは `http://localhost:8000` で起動します。

### 楽曲データベースの構築（任意）

`songs.db` はリポジトリに含まれているため通常は不要ですが、データを更新したい場合:

```bash
rm -f songs.db
python scraper.py
```

音域速報（voice-key.news）から約 260 組・3,900 曲のデータを取得します（約 8 分）。

---

## エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| `POST` | `/analyze` | アカペラ/マイク録音から音域を解析 |
| `POST` | `/analyze-karaoke` | カラオケ音源から音域を解析 (ボーカル分離あり) |
| `GET` | `/songs` | 楽曲一覧を取得 (検索対応) |

---

## 📊 処理時間について

### `/analyze` (アカペラ・マイク録音)
- **処理時間**: 約10〜30秒
- **用途**: ボーカルのみの音源、マイク録音

### `/analyze-karaoke` (カラオケ音源)
- **処理時間**: 約1〜3分
- **分離モデル**: MelBandRoformers (`voc_fv6.ckpt`)
- **用途**: 伴奏付きの音源からボーカルを自動分離

#### 高速化のポイント
1. **チェックポイント再利用**: 初回ダウンロード後はローカルキャッシュを再利用
2. **CPU環境前提最適化**: `audio-separator[cpu]` を利用
3. **最適化された音域分析**: WORLD 特徴ベースで推論

---

## モデル再学習（WORLD版）

```bash
cd backend
source venv/bin/activate

# 例: manifest を使った学習
python ml/train.py \
  --dataset-root ml/vocalset_data/FULL \
  --manifest ml/training_data/vocalset_manifest.csv
```

学習後の出力:
- `ml/models/register_model.joblib`
- `ml/training_data/world_dataset.npz`

---

## エンドポイント詳細

### POST /analyze

録音した音声ファイルから声域を解析する。

**リクエスト**: `multipart/form-data`

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| `file` | ファイル | 音声ファイル（.webm, .wav 等） |

```bash
curl -X POST http://localhost:8000/analyze \
  -F "file=@recording.webm"
```

---

### GET /health

サーバーの稼働状態を確認する。

```bash
curl http://localhost:8000/health
```

**レスポンス**:

```json
{ "status": "ok" }
```

---

### GET /songs/search

曲名またはアーティスト名で楽曲を検索する（部分一致）。

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `q` | string | はい | 検索キーワード（1文字以上） |

```bash
curl "http://localhost:8000/songs/search?q=Lemon"
```

**レスポンス**:

```json
{
  "results": [
    {
      "id": 353,
      "title": "Lemon",
      "artist": "米津玄師",
      "range": {
        "lowest": "mid1B",
        "highest": "hiB",
        "falsetto": "hiB"
      },
      "note": "ラスサビのみ地声hiB...",
      "source": "voice-key.news"
    }
  ]
}
```

検索結果は最大 20 件まで返します。

---

### GET /songs/{id}

楽曲 ID を指定して音域データを取得する。

```bash
curl http://localhost:8000/songs/1
```

**レスポンス**:

```json
{
  "id": 1,
  "title": "ANTENNA",
  "artist": "Mrs. GREEN APPLE",
  "range": {
    "lowest": "mid1D#",
    "highest": "hiA#",
    "falsetto": "hiE"
  },
  "note": "サビとBメロで地声hiA#計5回使用。",
  "source": "voice-key.news"
}
```

楽曲が見つからない場合は `404` を返します。

---

### GET /artists

アーティスト一覧を取得する。

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| `limit` | int | いいえ | 100 | 取得件数（1〜500） |
| `offset` | int | いいえ | 0 | 取得開始位置 |

```bash
curl "http://localhost:8000/artists?limit=3"
```

**レスポンス**:

```json
{
  "artists": [
    { "id": 233, "name": "04 Limited Sazabys", "slug": "04-limited-sazabys", "song_count": 17 },
    { "id": 186, "name": "AAA", "slug": "aaa", "song_count": 16 },
    { "id": 85, "name": "AKASAKI", "slug": "akasaki", "song_count": 4 }
  ]
}
```

---

### GET /artists/{id}/songs

指定アーティストの全楽曲を取得する。

```bash
curl http://localhost:8000/artists/7/songs
```

**レスポンス**:

```json
{
  "songs": [
    {
      "id": 353,
      "title": "Lemon",
      "artist": "米津玄師",
      "range": {
        "lowest": "mid1B",
        "highest": "hiB",
        "falsetto": "hiB"
      },
      "note": "ラスサビのみ地声hiB...",
      "source": "voice-key.news"
    }
  ]
}
```

アーティストが見つからない場合は `404` を返します。

---

## 音域表記について

楽曲の音域はカラオケ音域表記で記録されています。

| 表記 | 音域帯 | ピアノ音名 |
|------|--------|-----------|
| `lowF`〜`lowB` | 低音域 | F2〜B2 |
| `mid1C`〜`mid1B` | 中低音域 | C3〜B3 |
| `mid2C`〜`mid2B` | 中高音域 | C4〜B4 |
| `hiA`〜`hiG` | 高音域 | A4〜G5 |
| `hihiA`〜`hihiG` | 超高音域 | A5〜G6 |

`#` が付くとシャープ（半音上）です。例: `mid1C#` = C#3

## データソース

楽曲音域データは [音域速報（voice-key.news）](https://voice-key.news/) から取得しています。
