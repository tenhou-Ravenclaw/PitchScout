# CLAUDE.md

このファイルは Claude Code がこのリポジトリで作業する際のガイドラインです。
Cursor: `.cursor/rules/` / Copilot: `.github/copilot-instructions.md` にも同じ規約がある。

## 絶対制約

### 必須 (MUST)
- **MUST**: 新機能追加前に影響範囲を全て調査する（コンポーネント、API、型定義、Context、設定）
- **MUST**: 実装前に設計書を参照する（`docs/requirements/REQUIREMENTS.md`, `docs/ARCHITECTURE.md`）
- **MUST**: フロントエンドの API 通信は `api.ts` の axios インスタンスのみ使う
- **MUST**: `supabaseClient.ts` の null ガード（`supabase === null`）を維持する
- **MUST**: 日本語でドキュメンテーションコメントを書く（Python docstring / TypeScript JSDoc）
- **MUST**: 全関数に型を付ける（Python 型ヒント / TypeScript は `any` 禁止）

### 禁止 (NEVER / DON'T)
- **NEVER**: フロントエンドの10分タイムアウトを短縮しない（Demucs 解析に必要）
- **NEVER**: `config.py` 以外に解析の閾値・定数をハードコードしない
- **NEVER**: `.env` やシークレットをログ出力・コミットしない
- **NEVER**: A4 = 440Hz を使わない（日本のカラオケ標準は A4 = 442Hz）
- **DON'T**: Redux/Zustand を導入しない（React Context のみ使用）
- **DON'T**: `main.py` 以外にエンドポイント、`models.py` 以外にモデルを定義しない

## 開発ワークフロー

コード変更前に以下の手順を守ること:

1. **影響範囲の調査** — 変更対象の関連ファイルを全て特定する
2. **設計書の確認** — `REQUIREMENTS.md`、`ARCHITECTURE.md`、必要に応じて `GoogleCloud/` を参照する
3. **既存パターンの確認** — 再利用できるユーティリティや共通処理を調べる。新ライブラリ導入は既存アーキテクチャとの整合性を確認する
4. **実装方針の策定** — 非自明な変更では plan モードで実装方針を固めてから着手する
5. **実装** — 本ファイルのコーディング規約に従い、ドキュメンテーションコメントを含める
6. **テスト確認** — 既存テストがある場合、改変前後で通ることを確認する

## プロジェクト概要

**ピッチスカウト (PitchScout)** — AI による声域分析＋カラオケ選曲マッチング Web アプリ。
マイクで歌唱するか、カラオケ音源をアップロードすると、バックエンドが CREPE ピッチ検出と ML 分類で地声/裏声の声域を分析し、約5000曲のデータベースから楽曲を推薦する。

本番環境: https://pitchscout.ten-hou.com

## アーキテクチャ

```
フロントエンド (React/TS)               バックエンド (FastAPI/Python)
─────────────────                      ──────────────────────
routes.tsx (useRoutes)                 main.py (全エンドポイント)
  └─ routeWrappers/ ──props──> pages   ├─ analyzer.py (CREPE ピッチ解析)
contexts/ (Auth, Analysis, App)        ├─ register_classifier.py (ML 地声/裏声判定)
api.ts (axios, 自動認証) ──HTTP──>     ├─ vocal_separator.py (Demucs ボーカル分離)
supabaseClient.ts (null許容)           ├─ recommender.py (楽曲マッチング)
                                       ├─ database.py (SQLite: songs.db)
                                       └─ database_supabase.py (Supabase: ユーザー)
```

### デュアルデータベース設計
- **SQLite** (`backend/songs.db`, コミット済み): 約5000曲、約850アーティスト。実行時は読み取り専用。再構築: `rm -f songs.db && python scraper.py`。
- **Supabase** (クラウド PostgreSQL): 認証、ユーザープロファイル、分析履歴、お気に入り。スキーマは `backend/supabase_migration.sql`。

### 音声解析パイプライン (バックエンド)
1. WAV 変換 (`audio_converter.py`) → 16kHz モノラル（マイク）or 44.1kHz ステレオ（カラオケ）
2. カラオケモードのみ: Demucs ボーカル分離 (`vocal_separator.py`, htdemucs_6s)
3. CREPE ピッチ検出（複数閾値の信頼度フォールバック: 0.5 → 0.01）
4. ML 声区分類 (`register_classifier.py`): scikit-learn モデル + ルールベースフォールバック
5. 統計的外れ値除去、オクターブ補正、持続音バリデーション
6. Hz 範囲マッチングによる楽曲推薦 (`recommender.py`)

解析エンドポイントは2つ: `POST /analyze`（アカペラ/マイク、Demucs なし）と `POST /analyze-karaoke`（Demucs 分離あり）。

### フロントエンドパターン
- **ルートラッパー** (`routeWrappers/`): React Context とページコンポーネントを橋渡しし、ページを Context 非依存に保つ。
- **遅延読み込み**: 全ルートが `React.lazy()` + `Layout.tsx` 内の `<Suspense>` を使用。
- **状態管理**: 純粋な React Context。`AppContext` は `userRange` を `localStorage` に永続化。
- **認証**: Supabase JS クライアントが OAuth を処理。axios インターセプターが JWT を `Authorization: Bearer` ヘッダーに自動付与。
- **Nullable Supabase**: `supabaseClient.ts` は環境変数が未設定の場合 `null` を返す — 認証機能なしでもアプリが動作する。

## コーディング規約

### コードスタイル
- フロントエンドは**ダブルクォート**と**セミコロン**を使用（既存ファイルに合わせる）。
- 新規ルート: `routes.tsx` に追加 + `routeWrappers/` に既存パターンに従ったコンポーネントを作成。
- 音程表記のオクターブラベル: lowlow/low/mid1/mid2/hi/hihi/hihihi。

### ドキュメンテーション
- Python: 全関数・クラスに docstring。引数・返り値・例外の説明を含める。
- TypeScript: 全関数・コンポーネント・インターフェースに JSDoc。Props の各フィールドにも説明を付ける。
- 複雑なロジックにはインラインコメントで「なぜそうしているか」を説明する。

### エラーハンドリング
- フロントエンド: ユーザー操作に対する API 呼び出しには try-catch を書き、ユーザー向けエラー表示を行うこと。axios インターセプターだけに頼らない。
- バックエンド: エラーは `HTTPException` でステータスコードと日本語メッセージを返す。内部エラーは `print(f"[ERROR] ...")` でログ出力した上で適切な HTTP レスポンスを返す。

### ログ出力
- バックエンドのログ接頭辞: `[API]` エンドポイント処理 / `[STEP X/Y]` パイプライン進捗 / `[DEBUG]` 詳細情報 / `[INFO]` 要約 / `[WARN]` 警告 / `[ERROR]` エラー

### 型
- Python: 全関数の引数と返り値に型ヒントを付ける。Python 3.10+ の `X | None` 記法を使用。
- TypeScript: 適切な interface / type を定義する。API レスポンスには必ず型を付ける。

## プロジェクト規約

- 認証トークンは Axios インターセプターが Supabase セッションから `Authorization: Bearer ...` を自動付与する。
- 解析進捗 UI (`AnalysisContext`) はタイマー制御のステップを使用 — 解析フロー変更時はステップラベルも更新すること。
- 保護エンドポイント: `backend/auth.py` の `Depends(get_current_user)` を使用。任意認証: `Depends(get_optional_user)`。
- ブランチ・コミット: `main` ブランチをデフォルトとする。変更は新しいブランチで行い PR を作成する。

## セキュリティ

- CORS は現在 `backend/main.py` で `allow_origins=["*"]`。本番向け変更では必要最小オリジンに制限する。
- セキュリティ修正は影響範囲のテストを必須とする。重大な変更はユーザーにレビューを求める。

## ビルドとテスト

### フロントエンド (React 19 + TypeScript, Create React App)
```bash
cd frontend && npm install && npm start     # 開発サーバー localhost:3000
cd frontend && npm run build                # 本番ビルド → frontend/build/
cd frontend && npm test                     # Jest + React Testing Library
cd frontend && npm test -- --watchAll=false # テスト一括実行（CI モード）
```

### バックエンド (FastAPI + Python)
```bash
cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt  # 初回セットアップ
cd backend && source venv/bin/activate && uvicorn main:app --reload  # 開発サーバー localhost:8000
curl http://localhost:8000/health                                     # ヘルスチェック
```

**重要:** 必ず先に `source venv/bin/activate` すること。Homebrew のグローバル uvicorn と venv の依存関係が競合する。

システム依存: `ffmpeg`（音声変換に必要）。

SQLite 再構築: `rm -f songs.db && python scraper.py`

デプロイ・運用手順: `QUICKSTART.md` と `DEPLOYMENT.md` を参照。

## 連携ポイント

- **Supabase**: 認証、ユーザープロファイル、分析履歴、お気に入り（`backend/auth.py`、`backend/database_supabase.py`）。
- **SQLite**: 楽曲検索・アーティスト一覧（`backend/database.py`）。実行時は読み取り専用。
- **外部 ML/音声処理**: Demucs, torchcrepe, librosa, torchaudio（`backend/requirements.txt`）。
- **DB 更新スクリプト**: `backend/scraper.py`、`scraper_vocal_range.py`、`update_*.py`。

## 環境変数

### バックエンド (`backend/.env`)
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=<anon-key>
JWT_SECRET=<secret-key>     # 本番では強力な秘密鍵を設定
REGISTER_LOG_LEVEL=1        # 0=none, 1=summary, 2=decimated, 3=all
```

### フロントエンド (`frontend/.env`)
```
REACT_APP_SUPABASE_URL=https://xxx.supabase.co
REACT_APP_SUPABASE_ANON_KEY=<anon-key>
REACT_APP_API_URL=           # 省略可。開発時は localhost:8000、本番では /api がデフォルト
```
