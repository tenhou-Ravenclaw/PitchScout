# ピッチスカウト フロントエンド アーキテクチャ

> システム構造、状態管理、API連携、ワークフロー

**関連ドキュメント:**

- [GUIDELINES.md](./GUIDELINES.md) - デザイン・コーディング規約
- [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) - 実装詳細ガイド

---

## 1. プロジェクト概要

**ピッチスカウト**は、ユーザーの声を録音・分析し、音域に合った楽曲やキー変更を提案する Web アプリ。

| 項目              | 技術                             |
| ----------------- | -------------------------------- |
| フレームワーク    | React 19 + TypeScript            |
| スタイリング      | Tailwind CSS 3                   |
| HTTP クライアント | Axios                            |
| 認証              | Supabase Auth (Google OAuth)     |
| アイコン          | Heroicons v2                     |
| ビルドツール      | Create React App (react-scripts) |
| バックエンド      | FastAPI (Python)                 |
| 楽曲 DB           | SQLite (songs.db / 約 5000 曲)   |
| ユーザー DB       | Supabase (PostgreSQL)            |

---

## 2. ディレクトリ構成

```
src/
├── index.tsx                  # エントリポイント
├── App.tsx                    # Provider 初期化 + BrowserRouter 起動
├── routes.tsx                 # RouteObject 定義 + インラインルートラッパー関数
├── api.ts                     # 互換レイヤー（src/api/ を再エクスポート）
├── api/                       # API モジュール本体
│   ├── client.ts              # Axios インスタンス + JWT 自動付与
│   ├── types.ts               # API 型定義
│   ├── analysis.ts            # analyzeVoice / analyzeKaraoke
│   ├── songs.ts               # songs / artists 系 API
│   ├── favorites.ts           # favorites 系 API
│   ├── history.ts             # analysis history 系 API
│   ├── integratedRange.ts     # integrated-range API
│   └── index.ts               # バレルエクスポート
├── supabaseClient.ts          # Supabase クライアント初期化 (null 安全)
│
├── contexts/
│   ├── AuthContext.tsx         # 認証コンテキスト (Google OAuth)
│   ├── AppContext.tsx          # result / userRange / searchQuery 共有
│   └── AnalysisContext.tsx     # 解析進捗（progress / stepLabel）管理
│
├── components/
│   ├── layout/
│   │   ├── Header.tsx              # デスクトップヘッダー (md+ 表示)
│   │   ├── BottomNav.tsx           # モバイルボトムナビ (<md 表示)
│   │   └── Layout.tsx              # 共通レイアウト（Header/BottomNav/Outlet）
│   │
│   ├── ui/
│   │   ├── cards/
│   │   │   ├── AnalysisCardShell.tsx    # 録音/アップロード共通カード
│   │   │   ├── AuthRequiredCard.tsx     # 未ログイン時の共通カード
│   │   │   └── CenteredCardShell.tsx    # 中央配置カードの共通枠
│   │   ├── Pagination.tsx          # テーブルページネーション
│   │   ├── SearchBar.tsx           # 楽曲検索バー
│   │   ├── SyllableIndex.tsx       # 五十音インデックス
│   │   ├── ErrorBanner.tsx         # エラー表示バナー
│   │   ├── Toast.tsx               # トースト通知
│   │   └── LogoSplash.tsx          # ロゴシャドウアニメーション
│   │
│   └── features/
│       ├── Recorder.tsx            # マイク録音 + 波形ビジュアライザー
│       ├── Recorder.css            # Recorder 専用スタイル
│       ├── KaraokeUploader.tsx     # カラオケ音源アップロード
│       └── ResultView.tsx          # 分析結果表示 (音域・スコア・おすすめ曲)
│
├── hooks/
│   ├── useToast.ts             # トースト通知管理
│   ├── useFavoriteArtists.ts   # お気に入りアーティスト取得
│   └── useFavoriteSongs.ts     # お気に入り曲取得デバウンス
│
├── constants/
│   └── songListConstants.ts    # 楽曲検索定数・ユーティリティ
│
├── utils/
│   └── keyBadge.ts             # キーバッジ色付けロジック
│
├── pages/
│   ├── Home.tsx                # メニュー画面 (録音方法選択グリッド)
│   ├── Landing.tsx             # ランディング画面 (NEW RECORD / HISTORY)
│   ├── LoginPage.tsx           # ログイン画面 (Google OAuth ボタン)
│   ├── AnalysisResultPage.tsx  # 分析結果ダッシュボード (レーダーチャート付き)
│   ├── SongListPage.tsx        # 楽曲一覧 (アーティスト別グリッド + 曲テーブル)
│   ├── FavoritesPage.tsx       # お気に入り一覧
│   ├── HistoryPage.tsx         # 分析履歴一覧
│   ├── GuidePage.tsx           # 使い方ガイド
│   ├── RecorderPage.tsx        # マイク / カラオケ録音ラッパー
│   ├── UploaderPage.tsx        # 音源アップロード
│   └── ResultPage.tsx          # 録音/アップロード直後の中間結果
│
├── styles/
│   └── LogoSplash.css          # ロゴシャドウアニメーション専用
│
├── assets/
│   └── logo.png                # アプリロゴ
│
├── App.test.tsx                # テスト
├── setupTests.ts               # テスト設定
├── react-app-env.d.ts          # CRA 型定義
└── reportWebVitals.ts          # パフォーマンス計測

**ファイル総数**: 61 ファイル（2026-02-26 時点、`find src -type f` 実測）
```

### 2.1 主要ディレクトリ説明

#### `pages/` — ページコンポーネント統一ディレクトリ

- 全 11 個のページコンポーネントを集約
- 各ページは **Context 非依存** で、Props を受け取り表示のみを行う
- `routes.tsx` 内の **インラインルートラッパー関数** が Context と受け渡しを担当

#### `hooks/` — 再利用フックの集約

- `useToast`: トースト通知ロジック（4 ページで使用）
- `useFavoriteArtists`: お気に入りアーティスト取得（デバウンス付き）
- `useFavoriteSongs`: お気に入り曲の一括取得と更新

#### `constants/` — 定数とユーティリティ

- `songListConstants.ts`: 楽曲検索用の五十音インデックス・検索エイリアス（150+ 行）

#### `utils/` — 共有ユーティリティ

- `keyBadge.ts`: キーバッジの色付けロジック

#### `styles/` — グローバルスタイル

- `src/index.css`: Tailwind @layer components で共有 CSS クラス定義
  - `.table-container`: テーブルベースカード
  - `.table-header`: テーブルヘッダースタイル
  - `.table-row`: テーブル行スタイル (group対応)
  - `.key-badge-*`: キーバッジの色分け（perfect/good/ok/hard/default）
  - `.title-gradient-*`: タイトル用グラデーション（cyan-fuchsia / cyber）
  - `.btn-primary-cyan`: ログインなどの主要ボタン
  - `.btn-back-link`: 戻るリンクボタン
- `LogoSplash.css`: ロゴシャドウアニメーション専用

---

## 3. 画面遷移（Router + URL設計）

現行フロントエンドは `ViewState` ではなく、`react-router-dom` による URL ルーティングで画面管理を行う。

### 3.1 ルーティング方針

- `App.tsx` は `BrowserRouter` + Provider 初期化を担当する
- `routes.tsx` で URL と画面コンポーネントを定義し、**ページごとのインラインルートラッパー関数** を含む
- `Layout.tsx` 配下に `Outlet` を配置し、`Header` / `BottomNav` を共通レイアウトとして扱う
- **ルートラッパー関数** が AppContext / AuthContext を読み取り、ページコンポーネントに Props で渡す
- ページコンポーネント（`src/pages/` 配下）は **Context に直接依存しない** — Props のみを受け取る設計

#### インラインルートラッパーパターン

`routes.tsx` 内にルート専用のラッパー関数が定義される：

```typescript
// Context/遷移をラッパーで吸収し、ページへ Props を渡す
const HomeRoute = () => {
  const navigate = useNavigate();
  const { isAnalyzing } = useAnalysis();
  return (
    <Home
      onNormalClick={() => navigate("/record")}
      onKaraokeClick={() => navigate("/karaoke")}
      onUploadClick={() => navigate("/upload")}
      onHistoryClick={() => navigate("/history")}
      isAnalyzing={isAnalyzing}
    />
  );
};

const AnalysisRoute = () => {
  const { isAuthenticated } = useAuth();
  const { result } = useAppContext();
  return <AnalysisResultPage result={result} isAuthenticated={isAuthenticated} />;
};

const ResultRoute = () => {
  const navigate = useNavigate();
  const { result, isFromHistory } = useAppContext();
  return (
    <ResultPage
      result={result}
      isFromHistory={isFromHistory}
      onBack={() => navigate(isFromHistory ? "/history" : "/menu")}
    />
  );
};
```

**メリット:**

- `routeWrappers/` ディレクトリ不要 — routes.tsx で全て完結
- ページコンポーネントが Context に依存しない — 再利用性・テスト性向上
- ファイル総数削減（-6 ファイル）
- ルート側で依存注入を一元化できる（認証・遷移・共有 state）

### 3.2 URL 一覧（現行）

| Path         | 画面           | 役割                            |
| ------------ | -------------- | ------------------------------- |
| `/`          | LandingRoute   | ランディング                    |
| `/menu`      | HomeRoute      | 録音導線の入口                  |
| `/record`    | RecorderPage   | マイク録音                      |
| `/karaoke`   | RecorderPage   | カラオケ録音                    |
| `/upload`    | UploaderPage   | 音源アップロード                |
| `/result`    | ResultPage     | 録音/アップロード直後の中間結果 |
| `/analysis`  | AnalysisRoute  | 分析ダッシュボード（詳細表示）  |
| `/songs`     | SongListRoute  | 楽曲/アーティスト検索           |
| `/favorites` | FavoritesRoute | お気に入り                      |
| `/history`   | HistoryRoute   | 分析履歴                        |
| `/guide`     | GuidePage      | 使い方ガイド                    |
| `/login`     | LoginPage      | ログイン                        |

### 3.3 設計方針

- `/result`: 録音・アップロード導線に閉じた結果確認ページ。
- `/analysis`: 履歴統合音域・比較・詳細分析を扱う分析ハブ。
- `Header` / `BottomNav` からの常時遷移は `/analysis`, `/songs`, `/favorites`, `/history`, `/guide`, `/login` を中心に整理する。

### 3.4 遷移図

```
        ┌──────────┐
        │ landing  │
        └────┬─────┘
          ▼
        ┌──────────┐
        │   menu   │
        └─┬────┬───┘
          │    │
    ┌───────────┘    └───────────┐
    ▼                            ▼
  ┌──────────┐                 ┌──────────┐
  │ record   │                 │  upload  │
  │ karaoke  │                 │          │
  └────┬─────┘                 └────┬─────┘
    └──────────────┬─────────────┘
          ▼
        ┌──────────┐
        │  result  │（録音導線の一部）
        └──────────┘

  常時アクセス（Header / BottomNav）:
    analysis, songs, favorites, history, guide, login
```

> **補足**: 旧 `ViewState` ベース記述は廃止し、URL ルーティングを単一の遷移基盤とする。

> **詳細**: `/result` と `/analysis` の責務分離、エラーUX統一、API/Context不変条件については [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) を参照。

---

## 4. 状態管理

### AuthContext (グローバル)

```
AuthProvider (App.tsx でラップ)
  └── useAuth() で以下を提供:
        user: User | null         ← Supabase User オブジェクト
        isAuthenticated: boolean
        isLoading: boolean
        loginWithGoogle(): Promise<void>
        logout(): Promise<void>
```

- Supabase クライアントが `null` (env 未設定) の場合、認証機能は無効化されるが**アプリは正常動作する**
- `onAuthStateChange` でリダイレクト後のセッション復帰を監視

### AppContext（グローバル）

| State           | 型                       | 用途                       |
| --------------- | ------------------------ | -------------------------- |
| `result`        | `AnalysisResult \| null` | 最新の分析結果             |
| `userRange`     | `UserRange \| null`      | ユーザー音域（キー提案用） |
| `searchQuery`   | `string`                 | 楽曲検索クエリ             |
| `isFromHistory` | `boolean`                | 履歴経由の結果表示フラグ   |

### AnalysisContext（グローバル）

| State         | 型                       | 用途             |
| ------------- | ------------------------ | ---------------- |
| `isAnalyzing` | `boolean`                | 解析中フラグ     |
| `progress`    | `number`                 | 解析進捗（0-100） |
| `stepLabel`   | `string`                 | 進捗ステップ文言 |

### localStorage キー

| キー         | 内容                                    |
| ------------ | --------------------------------------- |
| `voiceRange` | `UserRange` (JSON) — 音域データの永続化 |

---

## 5. API 連携

### フロントエンド API 構成

- 現在の API 実装は `src/api/` 配下のモジュール群に分割されている。
- `src/api.ts` は互換性維持のための再エクスポート層で、既存 import を壊さない。
- 以後の新規実装は `src/api/` 配下への追加を基本とする。

| モジュール               | 役割                                       |
| ------------------------ | ------------------------------------------ |
| `api/client.ts`          | Axios 設定、10分タイムアウト、JWT 自動付与 |
| `api/types.ts`           | `AnalysisResult` など API 契約型           |
| `api/analysis.ts`        | 音声解析エンドポイント                     |
| `api/songs.ts`           | 楽曲/アーティスト検索                      |
| `api/favorites.ts`       | お気に入り操作                             |
| `api/history.ts`         | 履歴取得/削除                              |
| `api/integratedRange.ts` | 統合音域取得                               |
| `api/error.ts`           | API エラーのユーザー向けメッセージ変換     |
| `api/index.ts`           | バレル再エクスポート                       |

### フロントエンド API 関数（公開API）

| 関数                                        | メソッド | エンドポイント                  | 説明                            |
| ------------------------------------------- | -------- | ------------------------------- | ------------------------------- |
| `analyzeVoice(blob)`                        | POST     | `/analyze`                      | マイク録音の音域分析            |
| `analyzeKaraoke(file, filename)`            | POST     | `/analyze-karaoke`              | カラオケ音源の音域分析 (Demucs) |
| `getSongs(limit, offset, query, userRange)` | GET      | `/songs`                        | 楽曲検索 + キーおすすめ         |
| `getArtists(limit, offset, query)`          | GET      | `/artists`                      | アーティスト一覧                |
| `getArtistSongs(artistId, userRange)`       | GET      | `/artists/{id}/songs`           | 指定アーティストの楽曲          |
| `getFavoriteArtists()`                      | GET      | `/favorite-artists`             | お気に入りアーティスト一覧      |
| `addFavoriteArtist(artistId, artistName)`   | POST     | `/favorite-artists`             | お気に入りアーティスト追加      |
| `removeFavoriteArtist(artistId)`            | DELETE   | `/favorite-artists/{artist_id}` | お気に入りアーティスト削除      |
| `getFavorites(limit)`                       | GET      | `/favorites`                    | お気に入り曲一覧                |
| `addFavorite(songId)`                       | POST     | `/favorites`                    | お気に入り曲追加                |
| `removeFavorite(songId)`                    | DELETE   | `/favorites/{song_id}`          | お気に入り曲削除                |
| `checkFavorite(songId)`                     | GET      | `/favorites/check/{song_id}`    | 楽曲のお気に入り状態確認        |
| `getAnalysisHistory(limit)`                 | GET      | `/analysis/history`             | 分析履歴取得                    |
| `deleteAnalysisHistory(recordId)`           | DELETE   | `/analysis/history/{record_id}` | 分析履歴削除                    |
| `getIntegratedVocalRange(limit)`            | GET      | `/analysis/integrated-range`    | 統合音域取得                    |

### バックエンド主要エンドポイント

| メソッド | パス                         | 認証 | 説明                               |
| -------- | ---------------------------- | ---- | ---------------------------------- |
| POST     | `/analyze`                   | 任意 | アカペラ音源分析                   |
| POST     | `/analyze-karaoke`           | 任意 | カラオケ音源分析 (Demucs BGM 除去) |
| GET      | `/songs`                     | 不要 | 楽曲一覧 + キーおすすめ            |
| GET      | `/recommend`                 | 不要 | おすすめ曲取得                     |
| GET      | `/similar-artists`           | 不要 | 似ているアーティスト取得           |
| POST     | `/auth/signup`               | 不要 | メールでユーザー登録               |
| POST     | `/auth/signin`               | 不要 | メールでログイン                   |
| POST     | `/auth/signout`              | 必須 | ログアウト                         |
| POST     | `/auth/refresh`              | 不要 | セッションリフレッシュ             |
| POST     | `/auth/reset-password`       | 不要 | パスワードリセットメール送信       |
| POST     | `/auth/update-password`      | 必須 | パスワード更新                     |
| GET      | `/profile/me`                | 必須 | プロファイル取得                   |
| PUT      | `/profile/me`                | 必須 | プロファイル更新                   |
| PUT      | `/profile/vocal-range`       | 必須 | 声域情報更新                       |
| POST     | `/analysis`                  | 必須 | 分析履歴保存                       |
| GET      | `/analysis/history`          | 必須 | 分析履歴取得                       |
| POST     | `/favorites`                 | 必須 | お気に入り追加                     |
| DELETE   | `/favorites/{song_id}`       | 必須 | お気に入り削除                     |
| GET      | `/favorites`                 | 必須 | お気に入り一覧                     |
| GET      | `/favorites/check/{song_id}` | 必須 | お気に入り確認                     |

### 認証トークン自動付与

```typescript
// api/client.ts — Axios interceptor
API.interceptors.request.use(async (config) => {
  if (supabase) {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});
```

フロントエンドは Supabase と直接通信して OAuth を処理し、取得した JWT をバックエンド API リクエストに自動付与する。

---

## 6. 主要ワークフロー

### 録音 → 分析フロー

```
ユーザー操作              フロントエンド                 バックエンド
─────────────────────────────────────────────────────────────────────
menu で録音方法選択  →  Recorder コンポーネント表示
                         │
録音開始ボタン押下   →  MediaRecorder.start()
                         Web Audio API で波形描画
                         │
録音停止ボタン押下   →  MediaRecorder.stop()
                         Blob 生成
                         │
                         analyzeVoice(blob)       →  POST /analyze
                         or analyzeKaraoke(blob)  →  POST /analyze-karaoke
                                                       │
                                                       WAV 変換
                                                       (Demucs BGM 除去)
                                                       analyzer.analyze()
                                                       おすすめ曲追加
                                                       │
                         result を受信           ←  JSON レスポンス
                         │
                         setResult(data)
                         navigate("/result")
                         │
                         ResultPage (ResultView) で表示
```

### 楽曲検索フロー

```
Header 検索バー入力  →  onSearchChange(query)
                         setSearchQuery(query)
                         navigate("/songs")
                         │
SongListPage           →  500ms デバウンス後
                         getSongs(500, 0, query, userRange)
                         │                        →  GET /songs?q=...&chest_min_hz=...
                         │
                         アーティスト別グリッド表示
                         │
アーティスト選択     →  曲テーブル表示 (キーバッジ付き)
```

### 認証フロー (Google OAuth)

```
ログインボタン押下   →  loginWithGoogle()
                         supabase.auth.signInWithOAuth({ provider: "google" })
                         │
                         Google 認証画面にリダイレクト
                         │
認証成功             →  元の URL にリダイレクト
                         onAuthStateChange が発火
                         setUser(session.user)
                         │
                         以降の API リクエストに JWT 自動付与
```

---

## 7. 主要型定義

### UserRange

```typescript
interface UserRange {
  chest_min_hz: number; // 地声最低音 (Hz)
  chest_max_hz: number; // 地声最高音 (Hz)
  falsetto_max_hz?: number; // 裏声最高音 (Hz)
}
```

### Song

```typescript
interface Song {
  id: number;
  title: string;
  artist: string;
  lowest_note: string | null; // "C3" 形式
  highest_note: string | null;
  falsetto_note: string | null;
  note: string | null;
  source: string;
  recommended_key?: number; // キー変更推奨値 (±N)
  fit?: string; // "perfect" | "good" | "ok" | "hard"
}
```

### AnalysisResult（分析結果オブジェクト）

```typescript
interface AnalysisResult {
  // 音域
  overall_min: string; // "C3"
  overall_max: string; // "G5"
  overall_min_hz: number;
  overall_max_hz: number;
  chest_min: string;
  chest_max: string;
  chest_min_hz: number;
  chest_max_hz: number;
  falsetto_min?: string;
  falsetto_max?: string;
  falsetto_min_hz?: number;
  falsetto_max_hz?: number;
  chest_ratio: number; // 0-100
  falsetto_ratio: number; // 0-100
  chest_count: number; // フレーム数
  falsetto_count: number;

  // 声質タイプ
  voice_type: {
    voice_type: string; // "ハイトーン" etc.
    range_class: string; // "高音域" etc.
    description: string;
  };

  // 歌唱力分析
  singing_analysis: {
    overall_score: number; // 0-100
    range_score: number;
    range_semitones: number;
    stability_score: number;
    expression_score: number;
  };

  // おすすめ
  recommended_songs: RecommendedSong[];
  similar_artists: SimilarArtist[];

  // エラー時
  error?: string;
}
```

---

## 8. 開発環境セットアップ

### 前提条件

- Node.js 18+
- Python 3.10+ (バックエンド)

### フロントエンド

```bash
cd frontend
npm install
# .env を手動作成して Supabase の URL と Anon Key を設定
npm start              # http://localhost:3000
```

### 環境変数 (`frontend/.env`)

```
REACT_APP_SUPABASE_URL=https://xxx.supabase.co
REACT_APP_SUPABASE_ANON_KEY=your-supabase-anon-key
```

> 環境変数が未設定でもアプリは動作する（認証機能のみ無効）。

### バックエンド

```bash
cd backend
pip install -r requirements.txt
# .env を手動作成して Supabase サービスキー等を設定
uvicorn main:app --reload  # http://127.0.0.1:8000
```

### バックエンド環境変数 (`backend/.env`)

```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your-backend-supabase-key
SUPABASE_JWT_SECRET=xxx
```

---

## 関連ドキュメント

- [GUIDELINES.md](./GUIDELINES.md) - デザイン・コーディング規約
- [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) - 実装詳細ガイド
- [../../docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) - バックエンドアーキテクチャ
- [../../docs/requirements/REQUIREMENTS.md](../../docs/requirements/REQUIREMENTS.md) - プロジェクト要件定義
