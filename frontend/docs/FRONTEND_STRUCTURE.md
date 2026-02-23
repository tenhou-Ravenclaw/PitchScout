# frontend ディレクトリ構造・ワークフロー・役割・課題と改善案

## 現在のディレクトリ構造

```
frontend/
├── package.json              # 依存パッケージ・npm スクリプト・Jest/ESLint 設定
├── postcss.config.js         # PostCSS 設定（TailwindCSS・Autoprefixer）
├── README.md                 # プロジェクト説明
├── tailwind.config.js        # Tailwind CSS 設定・カスタムアニメーション
├── tsconfig.json             # TypeScript コンパイラ設定
├── docs/
│   ├── FRONTEND_STRUCTURE.md  # 本ドキュメント（frontend 構造・ワークフロー・改善案）
│   └── FILE_MAPPING.md        # 現状ファイル対応表（役割・移行先）
│                              # ※ リポジトリルートの docs/ARCHITECTURE.md は別
├── public/
│   ├── favicon.ico           # ファビコン
│   ├── index.html            # アプリの HTML エントリ（root div・meta・manifest 参照）
│   ├── logo.png              # 汎用ロゴ（index.html の icon 等）
│   ├── logo192.png           # PWA 用アイコン 192px
│   ├── logo512.png           # PWA 用アイコン 512px
│   ├── manifest.json         # PWA 用メタデータ（アイコン・テーマ色・ショートカット名）
│   └── robots.txt            # 検索エンジン向けクロール制御
├── src/
│   ├── AnalysisResultPage.tsx   # 分析結果の詳細表示（レーダーチャート・おすすめ楽曲・類似アーティスト）
│   ├── api.ts                  # API 通信・型定義の集約（分析・楽曲・お気に入り・履歴・アーティスト等）
│   ├── App.test.tsx            # App のテスト（ランディング表示のスモークテスト）
│   ├── App.tsx                 # ルートコンポーネント（BrowserRouter・各 Provider・LogoSplash・AppRoutes）
│   ├── FavoritesPage.tsx       # お気に入り楽曲一覧画面（取得・削除・キーおすすめ表示）
│   ├── GuidePage.tsx           # 使い方ガイド画面（録音→解析→楽曲検索のステップ説明）
│   ├── HistoryPage.tsx         # 分析履歴一覧画面（スワイプ削除・履歴選択で詳細へ）
│   ├── Home.tsx                # メニュー画面（マイク録音・カラオケ録音・アップロード・履歴への導線）
│   ├── HomePage.css            # ランディング・メニュー用スタイル（neon 風デザイン・セクション分割）
│   ├── index.css               # グローバルスタイル（Tailwind base/components/utilities・body など）
│   ├── index.tsx               # エントリポイント（ReactDOM マウント・reportWebVitals）
│   ├── Landing.tsx             # トップ画面（NEW RECORD・HISTORY の 2 セクション）
│   ├── LoginPage.tsx           # ログイン画面（Google 認証ボタン）
│   ├── react-app-env.d.ts      # React スクリプト用型参照（CRA デフォルト）
│   ├── reportWebVitals.ts      # Web Vitals 計測（CLS・FID・FCP・LCP・TTFB）
│   ├── routes.tsx              # ルート定義（Layout 配下の path と lazy 読み込みコンポーネント）
│   ├── setupTests.ts           # Jest セットアップ（jest-dom マッチャー導入）
│   ├── SongListPage.tsx        # 楽曲一覧画面（あ行検索・アーティスト・検索エイリアス・お気に入り）
│   ├── supabaseClient.ts       # Supabase クライアント初期化（認証用）
│   ├── logo.svg                # CRA デフォルトロゴ（未使用の場合は削除候補）
│   ├── assets/                 # 静的アセット
│   │   ├── logo.png            # ヘッダー等で使用
│   │   ├── new-logo-histogram.png
│   │   ├── new-logo-wave.png
│   │   └── old-logo.png        # 旧ロゴ（未使用の場合は削除候補）
│   ├── components/
│   │   ├── BottomNav.tsx       # 下部ナビ（楽曲・録音・お気に入り・履歴・プロフィール）
│   │   ├── Header.tsx          # 上部ヘッダー（ロゴ・検索バー・ナビリンク・ログアウト）
│   │   ├── KaraokeUploader.tsx # カラオケ音源アップロード UI（ドラッグ&ドロップ・ファイル選択）
│   │   ├── Layout.tsx          # 共通レイアウト（Header・BottomNav・Outlet・スクロールトップ）
│   │   ├── LogoSplash.tsx      # 起動時のロゴスプラッシュアニメーション
│   │   ├── Recorder.css        # Recorder コンポーネント用スタイル（波形ビジュアライザ等）
│   │   ├── Recorder.tsx        # 録音 UI（マイク/カラオケ録音・波形表示・分析進捗）
│   │   ├── ResultView.tsx      # 分析結果の簡易表示（音域・スコア・おすすめ楽曲カード）
│   │   └── SongTable.tsx       # 楽曲テーブル（キー・お気に入りボタン・userRange 考慮）
│   ├── constants/
│   │   └── searchAliases.ts    # アーティスト検索エイリアス（略称・よみ → 正式名のマッピング）
│   ├── contexts/
│   │   ├── AnalysisContext.tsx  # 分析中状態（進捗・ステップラベル・タイマー）
│   │   ├── AppContext.tsx       # アプリ全局状態（解析結果・userRange・検索クエリ・履歴由来フラグ）
│   │   └── AuthContext.tsx     # 認証状態（user・ログイン/ログアウト）
│   ├── pages/
│   │   ├── RecorderPage.tsx    # 録音画面（Recorder を /record・/karaoke で表示）
│   │   ├── ResultPage.tsx      # 結果表示画面（ResultView・履歴/メニューへの戻る導線）
│   │   └── UploaderPage.tsx    # アップロード画面（KaraokeUploader を表示）
│   ├── routeWrappers/
│   │   ├── AnalysisRoute.tsx   # /analysis 用（AppContext の result を AnalysisResultPage に渡す）
│   │   ├── FavoritesRoute.tsx  # /favorites 用（userRange・onLoginClick を FavoritesPage に渡す）
│   │   ├── HistoryRoute.tsx    # /history 用（履歴選択時の setResult・navigate を HistoryPage に渡す）
│   │   ├── HomeRoute.tsx       # /menu 用（各録音方法への navigate を Home に渡す）
│   │   ├── LandingRoute.tsx    # / 用（メニュー・履歴への navigate を Landing に渡す）
│   │   └── SongListRoute.tsx   # /songs 用（searchQuery・userRange・onLoginClick を SongListPage に渡す）
│   └── styles/
│       └── LogoSplash.css      # LogoSplash 用スタイル（オーバーレイ・アニメーション）
```

**現状ファイルと役割・移行先の対応表** → [FILE_MAPPING.md](./FILE_MAPPING.md)

## ワークフロー

1. **開発**: `src/`配下でReactコンポーネントやページ、ロジックを実装。
2. **スタイリング**: `styles/`や`public/`、`tailwind.config.js`などでデザインを調整。
3. **ビルド/テスト**: `App.test.tsx`や`setupTests.ts`でテスト、`package.json`のスクリプトでビルド。
4. **デプロイ**: ビルド成果物を`public/`や外部にデプロイ。

## 各ディレクトリ・ファイルの役割（現状）

- `public/` : 静的ファイル（HTML, manifest, robots.txt等）
- `src/` : アプリ本体
  - `components/` : 再利用可能なUI部品
  - `pages/` : 画面単位のコンポーネント
  - `routeWrappers/` : ルーティングやガード等のラッパー
  - `contexts/` : React Contextによる状態管理
  - `constants/` : 定数や設定値
  - `assets/` : 画像やフォント等のアセット
  - `styles/` : CSSファイル
  - その他直下: 主要ページやエントリーポイント、API通信、テスト等
- `docs/` : ドキュメント
- `package.json` : 依存管理・スクリプト
- `tailwind.config.js`, `postcss.config.js` : スタイリング設定
- `tsconfig.json` : TypeScript設定

---

## 機能別（Feature-based）ディレクトリ構造案

この構造の最大の目的は**「関連するものを1箇所にまとめる（凝集度を高める）」**ことです。これにより、例えば「録音機能を修正したい」時に、複数の深いディレクトリを行ったり来たりする手間が省けます。

```
src/
├── index.tsx               # ★必須: Reactアプリのエントリポイント（createRoot, Appマウント）
│                            # 例:
│                            # import React from 'react';
│                            # import { createRoot } from 'react-dom/client';
│                            # import App from './app/App';
│                            # const root = createRoot(document.getElementById('root')!);
│                            # root.render(<App />);
│
├── app/                    # アプリケーション全体の初期化・設定
│   ├── App.tsx             # (旧: src/App.tsx)
│   ├── routes.tsx          # (旧: src/routes.tsx, routeWrappers/*)
│   └── providers.tsx       # (旧: src/contexts/AppContext, AuthContext等を束ねる)
│
├── features/               # ★ 開発の主戦場：機能（ドメイン）ごとのモジュール
│   │
│   ├── auth/               # 【認証ドメイン】
│   │   ├── components/     # (旧: src/LoginPage.tsx)
│   │   └── hooks/          # useAuth など
│   │
│   ├── karaoke/            # 【録音・アップロードドメイン】
│   │   ├── components/     # (旧: Recorder.tsx, KaraokeUploader.tsx)
│   │   ├── pages/          # (旧: RecorderPage.tsx, UploaderPage.tsx)
│   │   ├── hooks/          # 録音ロジックやアップロード処理
│   │   └── api/            # 録音データ送信用のAPI
│   │
│   ├── analysis/           # 【分析ドメイン】
│   │   ├── components/     # (旧: ResultView.tsx)
│   │   ├── pages/          # (旧: AnalysisResultPage.tsx, ResultPage.tsx)
│   │   └── api/            # 分析結果取得API
│   │
│   └── songs/              # 【楽曲・履歴・お気に入りドメイン】
│       ├── components/     # (旧: SongTable.tsx)
│       ├── pages/          # (旧: SongListPage.tsx, FavoritesPage.tsx, HistoryPage.tsx)
│       └── api/            # 楽曲検索、履歴取得、お気に入り登録API
│
├── components/             # アプリ全域で使う「共通UI部品」（ドメイン知識を持たない）
│   ├── layouts/            # (旧: Layout.tsx)
│   ├── navigations/        # (旧: Header.tsx, BottomNav.tsx)
│   └── ui/                 # ボタン、ローディングスピナー、エラーメッセージなど
│
├── lib/                    # サードパーティライブラリの設定・ラップ
│   ├── supabase.ts         # (旧: supabaseClient.ts)
│   └── axios.ts            # (旧: api.tsの共通設定部分)
│
├── hooks/                  # アプリ全域で使う汎用Hooks
│   └── useAppNavigation.ts # ルーティング共通化など
│
├── utils/                  # 汎用ロジック（日付フォーマット、計算処理など）
│
└── assets/                 # 静的ファイル
    ├── images/
    ├── styles/             # (旧: src/index.css, HomePage.css など)
    └── constants/          # (旧: searchAliases.ts など)
```

---

## 既存コードとの「差分」と移行のポイント

現状のディレクトリ構造と上記の理想形を見比べると、以下のような差分（課題）が浮かび上がってきます。

### 1. src/ 直下の肥大化

**現状**: AnalysisResultPage.tsx や LoginPage.tsx など、ページコンポーネントとロジックが直下に散乱している。

**移行方針**: これらを features/ 配下の各ドメイン（analysis, auth など）の pages/ ディレクトリに移動させます。

### 2. api.ts のモノリス（巨大化）化

**現状**: 全てのAPI通信ロジックが1つの api.ts に集中している可能性が高い。

**移行方針**: 共通の通信クライアント設定（URLやヘッダーの付与）のみを lib/axios.ts 等に残し、具体的なエンドポイントごとの処理は features/karaoke/api/ や features/songs/api/ に分割します。

### 3. components/ の責務混在

**現状**: Header.tsx のような共通UIと、KaraokeUploader.tsx のような特定の機能に強く依存したUIが同列に置かれている。

**移行方針**: Header.tsx や BottomNav.tsx はルートの components/ に残し、機能特化型のUIは features/karaoke/components/ のようにドメイン配下へ隠蔽します。

---

## 構造の問題点（まとめ）

- `src/`直下にページやロジックが混在し、肥大化しやすい
- `pages/`と`src/`直下のページコンポーネントの役割が曖昧
- `routeWrappers/`の責務が不明瞭になりやすい
- `assets/`や`styles/`が用途別に整理されていない可能性
- テストファイルが`src/`直下にあり、規模拡大時に管理しづらい
- `api.ts`が単一ファイルに集中しており、機能追加時に肥大化しやすい
- `components/`に共通UIと機能特化UIが混在している

---

## 共通化の提案

1. **React RouterのuseNavigate, useLocationの共通化**
   - 多くのページやラッパーで `useNavigate`, `useLocation` を個別に呼び出しているため、ルーティング操作や画面遷移の共通ロジック（例：`useAppNavigation` カスタムフック）としてまとめると保守性向上。
2. **Contextの利用パターンの共通化**
   - `useAppContext`, `useAuth`, `useAnalysis` などContextの呼び出しが多い。Contextの値取得や更新ロジックをカスタムフックやProviderで整理し、props drillingを減らす。
3. **API通信・型定義の共通化**
   - 共通の通信クライアントは `lib/` に、エンドポイントごとの処理は各 features/ の api/ に配置。UI側はhooks経由でデータ取得・更新する形に統一するとテスト・再利用性が高まる。
4. **UI部品の共通化**
   - ヘッダー・ナビゲーション・ローディング・エラーメッセージなど、複数ページで使うUIは `components/` に集約。例：`<Header />`, `<BottomNav />`, `<LoadingSpinner />`, `<ErrorMessage />` など
5. **フォーム・バリデーションの共通化**
   - 入力フォームやバリデーション処理が複数箇所で発生する場合、共通のカスタムフック（例：`useForm`, `useInput`）やユーティリティ関数として切り出すと良い。
6. **スタイル・クラス名の共通化**
   - ボタンや入力欄などのスタイルが重複している場合、共通CSSモジュールやTailwindのカスタムクラスで一元管理。

これらの共通化を進めることで、重複コードの削減・保守性向上・バグの減少が期待できます。

---

## アクションアイテム

以下は、上記の構造改善・移行・共通化を進めるための具体的なタスクです。随時追記・完了チェックしてください。

- [ ] **ディレクトリ移行**: `src/` 直下のページを features 配下へ移動（例: LoginPage → features/auth/, AnalysisResultPage → features/analysis/pages/）
- [ ] **API 分割**: `api.ts` の共通設定を `lib/axios.ts` に切り出し、エンドポイント別に features/*/api/ へ分割
- [ ] **components 整理**: 機能特化UI（Recorder, KaraokeUploader, ResultView, SongTable）を features 配下の components/ へ移動
- [ ] **app/ の整備**: App.tsx・routes.tsx・Provider 集約を `src/app/` にまとめる（任意）
- [ ] **useAppNavigation**: ルーティング共通化用のカスタムフックを `hooks/useAppNavigation.ts` に作成
- [ ] **テスト配置**: 規模に応じて `__tests__/` または機能別ディレクトリ内にテストを整理

---

この改善により、可読性・保守性・拡張性が向上し、チーム開発や将来的な機能追加にも柔軟に対応できます。
