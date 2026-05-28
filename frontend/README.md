# Frontend

PitchScout の React / TypeScript フロントエンドです。録音、アップロード、分析結果表示、楽曲検索、履歴、お気に入り、ログイン画面を提供します。

## セットアップ

```bash
cd frontend
npm install
npm start
```

開発サーバーは `http://localhost:3000` で起動します。

## 環境変数

`frontend/.env`:

```env
REACT_APP_API_URL=http://127.0.0.1:8000
REACT_APP_SUPABASE_URL=https://your-project-ref.supabase.co
REACT_APP_SUPABASE_ANON_KEY=your-anon-key-here
```

`REACT_APP_API_URL` が未設定の場合、開発環境では `http://127.0.0.1:8000`、本番環境では `/api` を使います。Supabase の値が未設定でも、認証なしで使える画面は動作します。

## スクリプト

| コマンド | 内容 |
|----------|------|
| `npm start` | 開発サーバーを起動 |
| `npm run build` | production build を `build/` に生成 |
| `npm test` | Jest / React Testing Library のテストを実行 |
| `npm run eject` | CRA 設定を展開 |

## 主な構成

```text
src/
  api/             Axios クライアントと API ラッパー
  assets/          ロゴなどの静的アセット
  components/      UI・レイアウト・機能別コンポーネント
  contexts/        Auth / App / Analysis Context
  hooks/           検索、一覧、Toast、お気に入り関連の hooks
  pages/           画面コンポーネント
  routeWrappers/   Context と page をつなぐルート単位のラッパー
  routes.tsx       ルート定義
  supabaseClient.ts
```

## API 連携

`src/api/client.ts` の Axios インスタンスが、Supabase セッションから JWT を取得して `Authorization: Bearer <token>` を自動付与します。401 の場合は Supabase セッションの refresh を一度試みます。

主に利用するバックエンド API:

- `POST /analyze`
- `POST /analyze-karaoke`
- `GET /songs`
- `GET /artists`
- `GET /recommend`
- `GET /recommend/challenge`
- `GET /similar-artists`
- `GET /analysis/history`
- `GET/POST /favorites`
- `GET/POST /favorite-artists`
