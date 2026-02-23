# 現状ファイル対応表

frontend 配下の現状ファイル一覧と、役割・機能別構造案での移行先の対応表です。  
移行作業時の参照用にしてください。

- **現状のパス**: `frontend/` からの相対パス
- **種別**: ページ / コンポーネント / API・lib / コンテキスト / ルート / スタイル / 設定 / アセット / その他
- **移行先（案）**: [FRONTEND_STRUCTURE.md](./FRONTEND_STRUCTURE.md) の機能別構造案に沿った場合の配置先（`src/` 基準）

---

## プロジェクト直下・設定

| 現状のパス | 種別 | 役割・備考 | 移行先（案） |
|-----------|------|------------|--------------|
| `package.json` | 設定 | 依存・スクリプト・Jest/ESLint | 変更なし |
| `package-lock.json` | 設定 | ロックファイル | 変更なし |
| `tsconfig.json` | 設定 | TypeScript 設定 | 変更なし |
| `tailwind.config.js` | 設定 | Tailwind・カスタムアニメーション | 変更なし |
| `postcss.config.js` | 設定 | PostCSS（Tailwind, Autoprefixer） | 変更なし |
| `README.md` | その他 | プロジェクト説明 | 変更なし |
| `.vscode/settings.json` | 設定 | エディタ設定 | 変更なし |

---

## docs/

| 現状のパス | 種別 | 役割・備考 | 移行先（案） |
|-----------|------|------------|--------------|
| `docs/FRONTEND_STRUCTURE.md` | その他 | 本構造・改善案ドキュメント | 変更なし |
| `docs/FILE_MAPPING.md` | その他 | 本対応表 | 変更なし |

---

## public/

| 現状のパス | 種別 | 役割・備考 | 移行先（案） |
|-----------|------|------------|--------------|
| `public/index.html` | その他 | HTML エントリ・root・meta | 変更なし |
| `public/manifest.json` | その他 | PWA メタデータ | 変更なし |
| `public/robots.txt` | その他 | クロール制御 | 変更なし |
| `public/favicon.ico` | アセット | ファビコン | 変更なし |
| `public/logo.png` | アセット | 汎用ロゴ（HTML icon 等） | 変更なし |
| `public/logo192.png` | アセット | PWA アイコン 192px | 変更なし |
| `public/logo512.png` | アセット | PWA アイコン 512px | 変更なし |

---

## src/ 直下

| 現状のパス | 種別 | 役割・備考 | 移行先（案） |
|-----------|------|------------|--------------|
| `src/index.tsx` | その他 | エントリ（createRoot, App マウント） | 変更なし（必須） |
| `src/index.css` | スタイル | グローバル・Tailwind | `src/assets/styles/` 等 |
| `src/App.tsx` | その他 | ルート（Router, Provider, Routes） | `src/app/App.tsx` |
| `src/App.test.tsx` | その他 | App スモークテスト | `src/app/` または `__tests__/` |
| `src/routes.tsx` | ルート | ルート定義・lazy 読み込み | `src/app/routes.tsx` |
| `src/reportWebVitals.ts` | その他 | Web Vitals 計測 | 変更なし or `src/utils/` |
| `src/setupTests.ts` | 設定 | Jest セットアップ | 変更なし |
| `src/react-app-env.d.ts` | 設定 | CRA 型参照 | 変更なし |
| `src/supabaseClient.ts` | API・lib | Supabase クライアント | `src/lib/supabase.ts` |
| `src/api.ts` | API・lib | API・型定義の集約 | 分割 → `lib/axios.ts` + `features/*/api/` |
| `src/logo.svg` | アセット | CRA デフォルト（未使用なら削除候補） | 削除 or `src/assets/` |
| `src/Landing.tsx` | ページ | トップ（NEW RECORD / HISTORY） | `features/` または `app/` に近い場所 |
| `src/Home.tsx` | ページ | メニュー（録音・アップロード・履歴） | 同上 |
| `src/HomePage.css` | スタイル | ランディング・メニュー用 | `src/assets/styles/` 等 |
| `src/LoginPage.tsx` | ページ | ログイン（Google 認証） | `src/features/auth/components/` 等 |
| `src/GuidePage.tsx` | ページ | 使い方ガイド | 共通 or `features/` 配下の pages |
| `src/AnalysisResultPage.tsx` | ページ | 分析結果詳細（レーダー・おすすめ楽曲） | `src/features/analysis/pages/` |
| `src/FavoritesPage.tsx` | ページ | お気に入り楽曲一覧 | `src/features/songs/pages/` |
| `src/HistoryPage.tsx` | ページ | 分析履歴一覧 | `src/features/songs/pages/` |
| `src/SongListPage.tsx` | ページ | 楽曲一覧（あ行・アーティスト・検索） | `src/features/songs/pages/` |

---

## src/components/

| 現状のパス | 種別 | 役割・備考 | 移行先（案） |
|-----------|------|------------|--------------|
| `src/components/Layout.tsx` | コンポーネント | 共通レイアウト（Header, BottomNav, Outlet） | `src/components/layouts/` |
| `src/components/Header.tsx` | コンポーネント | 上部ヘッダー・検索・ナビ | `src/components/navigations/` |
| `src/components/BottomNav.tsx` | コンポーネント | 下部ナビ | `src/components/navigations/` |
| `src/components/LogoSplash.tsx` | コンポーネント | 起動スプラッシュ | `src/components/ui/` 等 |
| `src/components/Recorder.tsx` | コンポーネント | 録音 UI（マイク/カラオケ） | `src/features/karaoke/components/` |
| `src/components/Recorder.css` | スタイル | Recorder 用 | 同上 |
| `src/components/KaraokeUploader.tsx` | コンポーネント | カラオケアップロード UI | `src/features/karaoke/components/` |
| `src/components/ResultView.tsx` | コンポーネント | 分析結果簡易表示 | `src/features/analysis/components/` |
| `src/components/SongTable.tsx` | コンポーネント | 楽曲テーブル | `src/features/songs/components/` |

---

## src/contexts/

| 現状のパス | 種別 | 役割・備考 | 移行先（案） |
|-----------|------|------------|--------------|
| `src/contexts/AppContext.tsx` | コンテキスト | 解析結果・userRange・検索・履歴フラグ | `src/app/providers.tsx` に集約 or 維持 |
| `src/contexts/AuthContext.tsx` | コンテキスト | 認証（user, login, logout） | `src/app/providers.tsx` に集約 or `features/auth/` |
| `src/contexts/AnalysisContext.tsx` | コンテキスト | 分析中状態・進捗・タイマー | `src/app/providers.tsx` に集約 or `features/karaoke/` |

---

## src/pages/

| 現状のパス | 種別 | 役割・備考 | 移行先（案） |
|-----------|------|------------|--------------|
| `src/pages/RecorderPage.tsx` | ページ | 録音画面（/record, /karaoke） | `src/features/karaoke/pages/` |
| `src/pages/UploaderPage.tsx` | ページ | アップロード画面 | `src/features/karaoke/pages/` |
| `src/pages/ResultPage.tsx` | ページ | 結果表示（ResultView） | `src/features/analysis/pages/` |

---

## src/routeWrappers/

| 現状のパス | 種別 | 役割・備考 | 移行先（案） |
|-----------|------|------------|--------------|
| `src/routeWrappers/LandingRoute.tsx` | ルート | / → Landing | `src/app/routes.tsx` に統合 |
| `src/routeWrappers/HomeRoute.tsx` | ルート | /menu → Home | 同上 |
| `src/routeWrappers/AnalysisRoute.tsx` | ルート | /analysis → AnalysisResultPage | 同上 |
| `src/routeWrappers/SongListRoute.tsx` | ルート | /songs → SongListPage | 同上 |
| `src/routeWrappers/FavoritesRoute.tsx` | ルート | /favorites → FavoritesPage | 同上 |
| `src/routeWrappers/HistoryRoute.tsx` | ルート | /history → HistoryPage | 同上 |

---

## src/constants/, src/styles/, src/assets/

| 現状のパス | 種別 | 役割・備考 | 移行先（案） |
|-----------|------|------------|--------------|
| `src/constants/searchAliases.ts` | その他 | アーティスト検索エイリアス | `src/features/songs/` または `src/assets/constants/` |
| `src/styles/LogoSplash.css` | スタイル | LogoSplash 用 | `src/assets/styles/` または components と同階層 |
| `src/assets/logo.png` | アセット | ヘッダー等で使用 | `src/assets/images/` 等 |
| `src/assets/new-logo-histogram.png` | アセット | スプラッシュ用 | 同上 |
| `src/assets/new-logo-wave.png` | アセット | スプラッシュ用 | 同上 |
| `src/assets/old-logo.png` | アセット | 旧ロゴ（未使用なら削除候補） | 削除 or 同上 |

---

## 凡例・注意

- **移行先（案）** は [FRONTEND_STRUCTURE.md](./FRONTEND_STRUCTURE.md) の「機能別ディレクトリ構造案」に基づく目安です。実装方針に合わせて調整してください。
- 設定ファイル（tsconfig, tailwind 等）や `public/` は通常そのままです。
- `routeWrappers/` はルート定義に統合するか、そのままラッパーとして残すかは方針次第です。
