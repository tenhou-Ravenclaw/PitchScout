# ピッチスカウト フロントエンド アーキテクチャ

## 1. プロジェクト概要

**ピッチスカウト**は、ユーザーの声を録音・分析し、音域に合った楽曲やキー変更を提案する Web アプリ。

| 項目 | 技術 |
|------|------|
| フレームワーク | React 19 + TypeScript |
| スタイリング | Tailwind CSS 3 |
| HTTP クライアント | Axios |
| 認証 | Supabase Auth (Google OAuth) |
| アイコン | Heroicons v2 |
| ビルドツール | Create React App (react-scripts) |
| バックエンド | FastAPI (Python) |
| 楽曲 DB | SQLite (songs.db / 約 5000 曲) |
| ユーザー DB | Supabase (PostgreSQL) |

---

## 2. ディレクトリ構成

```
src/
├── index.tsx                  # エントリポイント
├── App.tsx                    # ルートコンポーネント・ViewState 管理・画面切替
├── api.ts                     # Axios クライアント・API 関数・UserRange 型
├── supabaseClient.ts          # Supabase クライアント初期化 (null 安全)
│
├── contexts/
│   └── AuthContext.tsx         # 認証コンテキスト (Google OAuth)
│
├── components/
│   ├── Header.tsx              # デスクトップヘッダー (md+ 表示)
│   ├── BottomNav.tsx           # モバイルボトムナビ (<md 表示)
│   ├── Recorder.tsx            # マイク録音 + 波形ビジュアライザー
│   ├── KaraokeUploader.tsx     # カラオケ音源アップロード
│   └── ResultView.tsx          # 分析結果表示 (音域・スコア・おすすめ曲)
│
├── Landing.tsx                 # ランディング画面 (NEW RECORD / HISTORY)
├── Home.tsx                    # メニュー画面 (録音方法選択グリッド)
├── LoginPage.tsx               # ログイン画面 (Google OAuth ボタン)
├── AnalysisResultPage.tsx      # 分析結果ダッシュボード (レーダーチャート付き)
├── SongListPage.tsx            # 楽曲一覧 (アーティスト別グリッド + 曲テーブル)
├── GuidePage.tsx               # 使い方ガイド
├── PlaceholderPage.tsx         # 開発中画面の汎用プレースホルダー
├── RecordingSelectionPage.tsx  # 録音方法選択 (旧 UI・未使用)
│
├── assets/
│   └── logo.png                # アプリロゴ
│
├── App.css                     # App 用 CSS
├── index.css                   # グローバル CSS (Tailwind ディレクティブ)
├── HomePage.css                # Landing 用カスタム CSS (アニメーション等)
│
├── App.test.tsx                # テスト
├── setupTests.ts               # テスト設定
├── react-app-env.d.ts          # CRA 型定義
└── reportWebVitals.ts          # パフォーマンス計測
```

---

## 3. 画面遷移 (ViewState)

`App.tsx` で定義された `ViewState` 型により、全 11 画面を管理:

```typescript
type ViewState =
  | "landing"    // ランディング
  | "menu"       // メニュー (録音方法選択)
  | "recorder"   // 録音
  | "uploader"   // カラオケ音源アップロード
  | "result"     // 分析結果 (ResultView)
  | "analysis"   // 分析ダッシュボード (AnalysisResultPage)
  | "songList"   // 楽曲一覧
  | "history"    // 履歴 (Placeholder)
  | "mypage"     // マイページ (Placeholder)
  | "guide"      // 使い方ガイド
  | "login";     // ログイン
```

### 遷移図 (ASCII)

```
                    ┌──────────┐
                    │ landing  │  ← 初期画面
                    └────┬─────┘
                 ┌───────┴────────┐
                 ▼                ▼
            ┌────────┐      ┌─────────┐
            │  menu  │      │ history │ (Placeholder)
            └──┬─┬─┬─┘      └─────────┘
       ┌───────┘ │ └────────┐
       ▼         ▼          ▼
  ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ recorder │ │ recorder │ │ uploader │
  │ (通常)   │ │(カラオケ)│ │          │
  └────┬─────┘ └────┬─────┘ └──────────┘
       └──────┬─────┘
              ▼
        ┌──────────┐     ┌──────────┐
        │  result  │────▶│ analysis │
        └──────────┘     └──────────┘

  Header/BottomNav から常にアクセス可能:
    songList, guide, login, analysis
```

> **設計意図**: React Router を使わず `useState<ViewState>` で画面を切り替える SPA パターン。ハッカソン規模ではシンプルで十分。

---

## 4. デザインルール

### カラーパレット (ダークテーマ)

| 用途 | カラー | Tailwind クラス例 |
|------|--------|-------------------|
| 背景 (ベース) | Slate 900 | `bg-slate-900` |
| カード背景 | Slate 900/60 + blur | `bg-slate-900/60 backdrop-blur-md` |
| ボーダー | White 10% | `border border-white/10` |
| アクセント (主) | Cyan | `text-cyan-400`, `border-cyan-500/30` |
| アクセント (副) | Pink / Rose | `text-pink-500`, `text-rose-400` |
| 成功 / 地声 | Indigo | `bg-indigo-500` |
| 成功 / 裏声 | Emerald | `bg-emerald-400` |
| スコア (高) | Emerald | `text-emerald-500` |
| スコア (中) | Sky / Amber | `text-sky-500`, `text-amber-500` |
| スコア (低) | Rose | `text-rose-400` |

### Glassmorphism カードパターン

```
bg-slate-900/60 backdrop-blur-md rounded-2xl shadow-xl border border-white/10
```

### レスポンシブ方針

| ブレークポイント | ナビゲーション |
|------------------|----------------|
| `md` 以上 (768px+) | `Header` を表示 (`hidden md:flex`) |
| `md` 未満 | `BottomNav` を表示 (`md:hidden`) |
| コンテンツ | `pb-24 md:pb-0` で BottomNav 分の余白を確保 |

---

## 5. コンポーネント一覧

### Header

| Props | 型 | 説明 |
|-------|----|------|
| `onLogoClick` | `() => void` (optional) | ロゴクリック → landing へ |
| `onMenuClick` | `() => void` | 「録音」ナビクリック |
| `onAnalysisClick` | `() => void` | 「分析結果」ナビクリック |
| `onSongListClick` | `() => void` | 「楽曲一覧」ナビクリック |
| `onGuideClick` | `() => void` | 「使い方ガイド」ナビクリック |
| `currentView` | `string` | 現在の ViewState (アクティブ表示用) |
| `searchQuery` | `string` | 検索バーの値 |
| `onSearchChange` | `(query: string) => void` | 検索入力ハンドラ |
| `isAuthenticated` | `boolean` | ログイン状態 |
| `userName` | `string \| null` | 表示名 |
| `onLoginClick` | `() => void` | ログインボタン |
| `onLogoutClick` | `() => void` | ログアウトボタン |

### BottomNav

| Props | 型 | 説明 |
|-------|----|------|
| `currentView` | `string` | 現在の ViewState |
| `onViewChange` | `(view: any) => void` | 画面切替 |
| `isAuthenticated` | `boolean` | ログイン状態 (マイページ/ログイン切替) |

### Recorder

| Props | 型 | 説明 |
|-------|----|------|
| `onResult` | `(data: any) => void` | 分析結果コールバック |
| `initialUseDemucs` | `boolean` | true: カラオケモード (BGM 除去) |

- Web Audio API で波形ビジュアライザー (Canvas) を描画
- MediaRecorder API でブラウザ録音

### KaraokeUploader

- Props なし (自己完結コンポーネント)
- 対応フォーマット: WAV, MP3, M4A, AAC, MP4, OGG, FLAC, WMA, WebM
- 内部で `ResultView` を使用して結果を表示

### ResultView

| Props | 型 | 説明 |
|-------|----|------|
| `result` | `any` | バックエンドからの分析結果オブジェクト |

表示セクション:
1. 声質タイプ + 全体音域
2. 地声/裏声バランスバー
3. 地声・裏声の詳細カード
4. 歌唱力スコア (総合・音域・安定性・表現力)
5. 声が似ているアーティスト
6. おすすめ曲リスト

---

## 6. 状態管理

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

### App.tsx ローカルステート

| State | 型 | 用途 |
|-------|----|------|
| `view` | `ViewState` | 現在表示中の画面 |
| `isKaraokeMode` | `boolean` | 録音モード (通常 / カラオケ) |
| `result` | `any` | 最新の分析結果 |
| `searchQuery` | `string` | 楽曲検索クエリ |
| `userRange` | `UserRange \| null` | ユーザーの音域 (キーおすすめ用) |

### localStorage キー

| キー | 内容 |
|------|------|
| `voiceRange` | `UserRange` (JSON) — 音域データの永続化 |
| `lastResult` | 分析結果 (JSON) — 最新結果の永続化 |

---

## 7. API 連携

### フロントエンド API 関数 (`api.ts`)

| 関数 | メソッド | エンドポイント | 説明 |
|------|----------|----------------|------|
| `analyzeVoice(blob)` | POST | `/analyze` | マイク録音の音域分析 |
| `analyzeKaraoke(file, filename)` | POST | `/analyze-karaoke` | カラオケ音源の音域分析 (Demucs) |
| `getSongs(limit, offset, query, userRange)` | GET | `/songs` | 楽曲検索 + キーおすすめ |

### バックエンド主要エンドポイント

| メソッド | パス | 認証 | 説明 |
|----------|------|------|------|
| POST | `/analyze` | 任意 | アカペラ音源分析 |
| POST | `/analyze-karaoke` | 任意 | カラオケ音源分析 (Demucs BGM 除去) |
| GET | `/songs` | 不要 | 楽曲一覧 + キーおすすめ |
| GET | `/recommend` | 不要 | おすすめ曲取得 |
| GET | `/similar-artists` | 不要 | 似ているアーティスト取得 |
| POST | `/auth/signup` | 不要 | メールでユーザー登録 |
| POST | `/auth/signin` | 不要 | メールでログイン |
| POST | `/auth/signout` | 必須 | ログアウト |
| POST | `/auth/refresh` | 不要 | セッションリフレッシュ |
| POST | `/auth/reset-password` | 不要 | パスワードリセットメール送信 |
| POST | `/auth/update-password` | 必須 | パスワード更新 |
| GET | `/profile/me` | 必須 | プロファイル取得 |
| PUT | `/profile/me` | 必須 | プロファイル更新 |
| PUT | `/profile/vocal-range` | 必須 | 声域情報更新 |
| POST | `/analysis` | 必須 | 分析履歴保存 |
| GET | `/analysis/history` | 必須 | 分析履歴取得 |
| POST | `/favorites` | 必須 | お気に入り追加 |
| DELETE | `/favorites/{song_id}` | 必須 | お気に入り削除 |
| GET | `/favorites` | 必須 | お気に入り一覧 |
| GET | `/favorites/check/{song_id}` | 必須 | お気に入り確認 |

### 認証トークン自動付与

```typescript
// api.ts — Axios interceptor
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

## 8. 主要ワークフロー

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
                         setView("result")
                         localStorage に保存
                         │
                         ResultView で表示
```

### 楽曲検索フロー

```
Header 検索バー入力  →  onSearchChange(query)
                         setSearchQuery(query)
                         setView("songList")
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

## 9. 主要型定義

### UserRange (`api.ts`)

```typescript
interface UserRange {
  chest_min_hz: number;    // 地声最低音 (Hz)
  chest_max_hz: number;    // 地声最高音 (Hz)
  falsetto_max_hz?: number; // 裏声最高音 (Hz)
}
```

### Song (`SongListPage.tsx`)

```typescript
interface Song {
  id: number;
  title: string;
  artist: string;
  lowest_note: string | null;   // "C3" 形式
  highest_note: string | null;
  falsetto_note: string | null;
  note: string | null;
  source: string;
  recommended_key?: number;     // キー変更推奨値 (±N)
  fit?: string;                 // "perfect" | "good" | "ok" | "hard"
}
```

### 分析結果オブジェクト (バックエンド返却)

```typescript
// ResultView / AnalysisResultPage が受け取る result の主要フィールド
{
  // 音域
  overall_min: string;        // "C3"
  overall_max: string;        // "G5"
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
  chest_ratio: number;        // 0-100
  falsetto_ratio: number;     // 0-100
  chest_count: number;        // フレーム数
  falsetto_count: number;

  // 声質タイプ
  voice_type: {
    voice_type: string;       // "ハイトーン" etc.
    range_class: string;      // "高音域" etc.
    description: string;
  };

  // 歌唱力分析
  singing_analysis: {
    overall_score: number;    // 0-100
    range_score: number;
    range_semitones: number;
    stability_score: number;
    expression_score: number;
  };

  // おすすめ
  recommended_songs: Array<{ id, title, artist, match_score, recommended_key, fit, ... }>;
  similar_artists: Array<{ id, name, similarity_score, typical_lowest, typical_highest }>;

  // エラー時
  error?: string;
}
```

---

## 10. 開発環境セットアップ

### 前提条件

- Node.js 18+
- Python 3.10+ (バックエンド)

### フロントエンド

```bash
cd frontend
npm install
cp .env.example .env   # Supabase の URL と Anon Key を設定
npm start              # http://localhost:3000
```

### 環境変数 (`frontend/.env`)

```
REACT_APP_SUPABASE_URL=https://xxx.supabase.co
REACT_APP_SUPABASE_ANON_KEY=eyJ...
```

> 環境変数が未設定でもアプリは動作する（認証機能のみ無効）。

### バックエンド

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # Supabase サービスキー等を設定
uvicorn main:app --reload  # http://127.0.0.1:8000
```

### バックエンド環境変数 (`backend/.env`)

```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...           # service_role キー
SUPABASE_JWT_SECRET=xxx
```
