# PitchScout プロジェクト概要

最終更新: 2026-04-28
本番環境: https://pitch-scout.vercel.app/

---

## 1. 企画概要

### 1.1 プロダクトビジョン

**解決する課題**: 「カラオケで自分に合う曲が見つからない」「サビが高すぎて歌えなかった」「毎回同じ曲しか歌えない」——多くのカラオケユーザーが抱えるこれらの悩みを、AI 技術で解決する。

**ソリューション**: ユーザーが数秒の録音またはカラオケ音源をアップロードするだけで、AI が地声・裏声の音域を科学的に分析。約 5,000 曲・約 850 アーティストの楽曲データベースから、ユーザーの声域にマッチする楽曲を自動推薦する Web アプリケーション。

**提供価値**:

1. **声域の客観的把握** — 自分の地声・裏声の音域を数値とグラフで可視化。「なんとなく高い声が出る」を「地声は mid1C〜hiA、裏声は hiE まで」という客観的データに変換
2. **失敗しない曲選び** — 声域マッチングにより、自分が歌いきれる曲だけを提案。キー変更の提案（例: 「−2 キーで最適」）で選択肢をさらに拡大
3. **成長の可視化** — 分析履歴を時系列で記録し、ボイトレや練習による声域の変化を追跡
4. **手軽さ** — スマホのブラウザでアクセスするだけ。アプリのインストール不要、数秒の録音で分析完了

### 1.2 ターゲットユーザー

**主要ターゲット**: カラオケ初心者〜中級者

| ペルソナ | 課題 | PitchScout での解決 |
|---------|------|-------------------|
| 会社員（28 歳） | 月 1 回のカラオケで毎回同じ曲。新しい曲に挑戦したいが、合う曲がわからない | 声域分析 → おすすめ曲リストで新しいレパートリーを発見 |
| 大学生（22 歳） | 「歌ってみたらサビが高すぎた」を何度も経験 | 事前に声域マッチングで確認、キー変更の提案で失敗を回避 |
| 主婦（35 歳） | ボイトレに通っているが、成果を客観的に記録したい | 分析履歴で声域の変化を時系列グラフで可視化 |

**利用シーン**:
- カラオケ前の曲選び（「今日何歌おう？」の解決）
- カラオケ中の次の曲探し（スマホでサッと検索）
- ボイトレの成果記録（定期的に録音して声域の推移を確認）
- 友人への曲のおすすめ（「この声域ならこの曲が合うよ」）

### 1.3 コア機能

#### 声域分析（中核機能）

| 機能 | 概要 | 処理時間 | 認証 |
|------|------|---------|------|
| **マイク録音分析** | ブラウザのマイクでアカペラ録音（5〜60 秒）→ 声域分析 | 10〜30 秒 | 不要 |
| **カラオケ音源分析** | BGM 付き音源をアップロード（最大 50MB）→ ボーカル分離 → 声域分析 | 1〜5 分 | 不要 |
| **ファイルアップロード分析** | アカペラ音声ファイルを直接アップロード → 声域分析 | 10〜30 秒 | 不要 |

対応フォーマット: WAV, MP3, M4A, FLAC, WebM, MP4, MOV（動画は音声トラック抽出）

#### 楽曲検索・推薦

| 機能 | 概要 |
|------|------|
| **声域マッチング検索** | 地声・裏声の音域範囲で楽曲を絞り込み、マッチ度順に表示 |
| **キー変更提案** | 曲の音域とユーザー声域を比較し、最適なキー変更値（±6 半音）を算出 |
| **おすすめ曲提案** | 分析結果から即座に歌いやすい曲をリストアップ |
| **チャレンジ曲提案** | 少し背伸びすれば歌える曲を提案（声域拡張の練習用） |
| **類似アーティスト検索** | 音域が近いアーティストを提案し、新しいレパートリーを開拓 |
| **声質タイプ判定** | 音域の広さ・高さ・地声裏声比率から「低音型」「高音型」「バランス型」等を分類 |
| **フリーワード検索** | 曲名・アーティスト名で部分一致検索（ひらがな・カタカナ・漢字対応） |

#### ユーザー機能（要ログイン）

| 機能 | 概要 |
|------|------|
| **分析履歴** | 過去の分析結果を時系列で保存・閲覧。声域の推移グラフで成長を可視化 |
| **統合声域** | 複数回の分析結果を統合し、総合的な声域範囲を算出 |
| **お気に入り楽曲** | 気になる曲をブックマークし、カラオケ時に参照 |
| **お気に入りアーティスト** | 好きなアーティストを登録し、新曲追加時に素早くアクセス |
| **プロファイル管理** | 表示名・現在の声域情報の管理 |

### 1.4 分析の出力

分析完了後、以下の情報がユーザーに提示される:

**声域データ**:
- 地声最低音・最高音（例: lowG〜hiA）
- 裏声最高音（例: hiE）
- 地声率・裏声率（%）— 歌唱中に地声と裏声をどの程度使い分けているか
- 音域の広さ（半音数）

**歌唱力スコア**（3 軸評価）:
- **音域スコア** — 音域の広さと高さを総合評価
- **安定性スコア** — ピッチの安定度、ビブラートの質
- **表現力スコア** — 声区の使い分け、ダイナミクスの幅

**楽曲推薦**:
- おすすめ曲リスト（マッチ度スコア付き）
- 各曲の推奨キー変更値（例: 「原曲キー」「+2 で最適」）
- 類似アーティスト一覧
- 声質タイプ（例: 「高音型・地声寄り」）

### 1.5 音程表記

日本のカラオケ標準に準拠したオクターブラベルを使用:

```
lowlow → low → mid1 → mid2 → hi → hihi → hihihi
```

基準音: **A4 = 442Hz**（日本のカラオケ標準。国際標準の 440Hz ではない）

### 1.6 楽曲データベース

- **楽曲数**: 約 5,000 曲
- **アーティスト数**: 約 850 組
- **データソース**: voice-key.news の公開音域情報をスクレイピング（音源・歌詞は含まない）
- **保持情報**: 曲名、アーティスト名、最低音、地声最高音、裏声最高音
- **ストレージ**: SQLite（`backend/songs.db`）としてリポジトリにコミット済み、実行時は読み取り専用
- **更新方法**: `rm -f songs.db && python scraper.py` で再構築

### 1.7 成功指標（KPI）

| 指標 | 目標値 |
|------|--------|
| ユーザー登録数 | 月間 100 名（初年度） |
| 分析実行回数 | ユーザーあたり月 3 回以上 |
| 30 日リテンション | 40% 以上 |
| 分析成功率 | 90% 以上（エラーなく完了） |
| NPS スコア | 40 以上 |

---

## 2. アーキテクチャ概要

### 2.1 全体構成

フロントエンド（React/TypeScript）とバックエンド（FastAPI/Python）の 2 層構成。データストアは SQLite（楽曲カタログ）と Supabase（ユーザーデータ）のデュアル DB 設計。

```
┌─────────────────────────────────────────────────┐
│  フロントエンド (React 19 / TypeScript / CRA)    │
│  ├─ routes.tsx + routeWrappers/                 │
│  ├─ Contexts (Auth / App / Analysis)            │
│  └─ api/client.ts (Axios + JWT 自動付与)        │
└───────────────┬─────────────────────────────────┘
                │ HTTPS
                v
┌─────────────────────────────────────────────────┐
│  バックエンド (FastAPI / Python)                  │
│  ├─ routers/ (auth / users / songs / analysis)  │
│  ├─ audio/   (変換 / ボーカル分離 / ノイズ除去)   │
│  ├─ analysis/(パイプライン / 分類器 / スコア)     │
│  ├─ recommender.py (楽曲マッチング)              │
│  └─ db/      (SQLite / Supabase アクセス層)     │
└───────┬──────────────────┬──────────────────────┘
        v                  v
┌──────────────┐  ┌────────────────────┐
│ SQLite       │  │ Supabase           │
│ songs.db     │  │ (PostgreSQL+Auth)  │
│ ~5000曲      │  │ ユーザー/履歴/     │
│ ~850アーティスト│ │ お気に入り         │
│ (読み取り専用) │  │                    │
└──────────────┘  └────────────────────┘
```

### 2.2 音声解析パイプライン

PitchScout の中核機能。2 つのエンドポイントで入口が異なるが、解析コアは共通。

#### マイク録音 (`POST /analyze`)

```
音声ファイル → WAV変換(16kHz mono) → 解析コア → 結果整形
```

#### カラオケ音源 (`POST /analyze-karaoke`)

```
音声ファイル → WAV変換(44.1kHz stereo)
  → MelBandRoformers ボーカル分離
  → DeepFilterNet ノイズ除去
  → 解析コア → 結果整形
```

#### 解析コア (`analysis/pipeline.py`)

```
1. 音声読み込み・正規化
2. WORLD 特徴抽出 (F0 / SP / AP)
3. 20次元セグメント特徴ベクトル生成
   └─ F0統計(6) + AP帯域(8) + SP形状(6) = 20次元
4. RandomForest で chest probability を推定
5. AP/HNR ゲート + RF フォールバックでフレーム分類
6. セグメント単位の地声/裏声ラベル決定
7. 統計的外れ値除去・オクターブ補正
8. 歌唱力スコアリング (音域/安定性/表現力)
9. 楽曲推薦・類似アーティスト・声質タイプ付与
```

#### 地声/裏声判定 (`analysis/classifier.py`)

HybridClassifier による 3 段階判定:

1. **低音域ルール**: f0 < 330Hz → 本アプリでは地声寄りとして扱う
2. **AP/HNR ゲート**: 非周期性成分(AP)と調波対雑音比(HNR)の閾値判定
3. **RF フォールバック**: ゲートが曖昧な場合、RandomForest の chest probability で判定

### 2.3 技術スタック

#### フロントエンド

| 技術 | 用途 |
|------|------|
| React 19 | UI フレームワーク |
| TypeScript | 型安全な開発 |
| Tailwind CSS | スタイリング |
| Axios | API 通信（JWT 自動付与） |
| Supabase JS SDK | 認証・セッション管理 |
| Recharts | グラフ描画 |
| React Router | ルーティング（全ページ遅延ロード） |

#### バックエンド

| 技術 | 用途 |
|------|------|
| FastAPI / Uvicorn | Web フレームワーク |
| pyworld | WORLD ベースのピッチ・スペクトル特徴抽出 |
| audio-separator | MelBandRoformers によるボーカル分離 |
| deepfilternet | DeepFilterNet3 ノイズ除去 |
| scikit-learn / joblib | RandomForest 声区分類モデル |
| librosa / soundfile | 音声 I/O・処理 |
| torch / torchaudio | 音声処理基盤 |
| ffmpeg | 音声フォーマット変換（システム依存） |

#### インフラ・データ

| 技術 | 用途 |
|------|------|
| SQLite | 楽曲カタログ（読み取り専用、コミット済み） |
| Supabase | 認証・ユーザーデータ（PostgreSQL + Auth） |
| Google Cloud | 本番ホスティング |

### 2.4 ディレクトリ構成

```
PitchScout/
├── frontend/               # React/TypeScript フロントエンド
│   └── src/
│       ├── api/            # Axios インスタンス (client.ts)
│       ├── contexts/       # Auth / App / Analysis Context
│       ├── pages/          # ページコンポーネント
│       ├── routeWrappers/  # Context ↔ Page の橋渡し
│       ├── routes.tsx      # 全ルート定義 (React.lazy)
│       └── supabaseClient.ts  # Supabase (null 許容)
│
├── backend/                # FastAPI/Python バックエンド
│   ├── main.py             # アプリ設定・ミドルウェア・ルーター登録
│   ├── config.py           # 解析閾値・定数の一元管理
│   ├── models.py           # Pydantic モデル定義
│   ├── auth.py             # JWT 認証ヘルパー
│   ├── note_converter.py   # Hz ↔ 音階ラベル (A4=442Hz)
│   ├── recommender.py      # 楽曲マッチング・声質タイプ判定
│   ├── routers/
│   │   ├── auth.py         # /auth/* 認証エンドポイント
│   │   ├── users.py        # /profile/*, /analysis/*, /favorites*
│   │   ├── songs.py        # /songs, /artists, /recommend
│   │   └── analysis.py     # /analyze, /analyze-karaoke
│   ├── audio/
│   │   ├── converter.py    # ffmpeg WAV 変換
│   │   ├── separator.py    # MelBandRoformers ボーカル分離
│   │   └── noise.py        # DeepFilterNet ノイズ除去 + Silero VAD
│   ├── analysis/
│   │   ├── pipeline.py     # メイン解析パイプライン
│   │   ├── classifier.py   # HybridClassifier (AP/HNR + RF)
│   │   ├── feature_extractor.py  # WORLD 特徴抽出・20次元集約
│   │   ├── features.py     # 倍音特徴ユーティリティ
│   │   └── scoring.py      # 歌唱力スコア (3軸)
│   ├── ml/                 # モデル学習・テスト
│   ├── db/
│   │   ├── songs.py        # SQLite アクセス層
│   │   └── users.py        # Supabase アクセス層
│   └── songs.db            # SQLite 楽曲 DB (コミット済み)
│
└── docs/                   # ドキュメント
    ├── PROJECT_OVERVIEW.md  # 本書
    ├── ARCHITECTURE.md      # 詳細アーキテクチャ
    ├── DEPLOYMENT.md        # デプロイ手順
    └── requirements/
        └── REQUIREMENTS.md  # 要件定義書
```

### 2.5 認証フロー

```
[ブラウザ] ── Supabase JS SDK ──> [Supabase Auth] (OAuth/Email)
    │                                     │
    │  JWT セッション取得                    │
    v                                     v
[Axios インターセプター]            [Supabase PostgreSQL]
  Authorization: Bearer <JWT>        ユーザーデータ (RLS)
    │
    v
[FastAPI] ── auth.py: get_current_user ── JWT 検証
```

- ログイン不要でも分析・楽曲検索は利用可能
- `supabaseClient.ts` は環境変数未設定時に `null` を返し、認証なしでもアプリが動作する

### 2.6 API エンドポイント一覧

| カテゴリ | パス | メソッド | 認証 |
|---------|------|---------|------|
| **認証** | `/auth/signup` | POST | 不要 |
| | `/auth/signin` | POST | 不要 |
| | `/auth/signout` | POST | 必要 |
| | `/auth/refresh` | POST | 不要 |
| | `/auth/reset-password` | POST | 不要 |
| | `/auth/update-password` | POST | 必要 |
| **分析** | `/analyze` | POST | 任意 |
| | `/analyze-karaoke` | POST | 任意 |
| **楽曲** | `/songs` | GET | 不要 |
| | `/artists` | GET | 不要 |
| | `/artists/{id}/songs` | GET | 不要 |
| | `/recommend` | GET | 不要 |
| | `/recommend/challenge` | GET | 不要 |
| | `/similar-artists` | GET | 不要 |
| **ユーザー** | `/profile/me` | GET/PUT | 必要 |
| | `/profile/vocal-range` | PUT | 必要 |
| | `/analysis/history` | GET | 必要 |
| | `/analysis/integrated-range` | GET | 必要 |
| | `/analysis/timeline` | GET | 必要 |
| | `/analysis/growth` | GET | 必要 |
| | `/favorites` | GET/POST | 必要 |
| | `/favorites/{song_id}` | DELETE | 必要 |
| | `/favorite-artists` | GET/POST | 必要 |
| | `/favorite-artists/{id}` | DELETE | 必要 |

---

## 3. 設計上の重要な判断

| 判断事項 | 採用方針 | 理由 |
|---------|---------|------|
| A4 基準音 | 442Hz | 日本のカラオケ標準 |
| 声区分離 | MelBandRoformers | Demucs より高精度・軽量 |
| ピッチ抽出 | WORLD (pyworld) | CREPE より特徴量が豊富 (F0/SP/AP) |
| 声区分類 | AP/HNR ゲート + RF | 物理的指標優先、曖昧時のみ ML フォールバック |
| 状態管理 | React Context のみ | Redux/Zustand 不使用（アプリ規模に適合） |
| 楽曲 DB | SQLite (読み取り専用) | コミット済みで環境非依存、起動が速い |
| ユーザー DB | Supabase | 認証・RLS・リアルタイム対応 |
| 閾値管理 | config.py 集約 | ハードコード禁止、チューニング容易 |

---
