# frontend ディレクトリ構造・ワークフロー・役割・課題と改善案

専門用語の説明は文末の **[用語集（辞典）](#用語集辞典)** を参照してください。

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

---

## 用語集（辞典）

本文で使っている専門用語を、初心者向けに簡潔に説明します。五十音順です。

| 用語 | 説明 |
|------|------|
| **API** | アプリとサーバーがデータのやり取りをするための「窓口」や「約束ごと」。ここでは「このURLにこう送ると、こう返ってくる」という通信の仕様を指します。 |
| **アセット** | 画像・アイコン・フォント・音声など、コード以外の静的ファイルの総称。 |
| **エンドポイント** | API のうち「1本のURL」のこと。例：`/analyze`（分析する）、`/songs`（楽曲一覧を返す）。 |
| **エントリポイント** | アプリが起動するとき、最初に実行されるファイルや処理。ブラウザでは通常 `index.html` → `index.tsx` がエントリになります。 |
| **凝集度** | 「関係するものがどれだけ一箇所にまとまっているか」の度合い。凝集度が高い＝関連コードが近くにあり、変更しやすい状態。 |
| **ガード** | ルート（画面）に進む前の「条件チェック」。例：ログインしていないならログイン画面へ飛ばす。 |
| **カスタムフック** | React の「状態や処理を再利用する仕組み」を、自分で関数としてまとめたもの。`use〇〇` という名前で、複数コンポーネントで使い回せます。 |
| **Context（コンテキスト）** | React で「複数画面・コンポーネントで共有したい値」（例：ログイン中のユーザー、解析結果）をまとめて渡す仕組み。 |
| **コンポーネント** | 画面を構成する「部品」のこと。ボタン1つでも、ヘッダー全体でも、再利用できる一塊のUIをコンポーネントと呼びます。 |
| **サードパーティ** | 自分たちのコードではなく、外部のライブラリ・サービス（例：Supabase、axios）のこと。 |
| **スモークテスト** | 「起動して、最低限の表示や動作ができるか」を確認する軽いテスト。細かい仕様より「壊れていないか」を見ます。 |
| **責務** | そのファイルやフォルダが「何を担当するか」。責務がはっきりしていると、修正する場所を探しやすくなります。 |
| **ディレクトリ** | フォルダのこと。プロジェクト内の「どこに何を置くか」を整理する単位です。 |
| **ドメイン** | ここでは「機能のまとまり」の意味。例：認証ドメイン（ログイン周り）、録音ドメイン（録音・アップロード周り）。 |
| **トランスパイル** | 新しい書き方のJavaScript（TypeScript 含む）を、ブラウザが理解できる形のJavaScriptに変換すること。 |
| **バリデーション** | 入力内容が正しいかチェックすること。例：メール形式か、必須項目が空でないか。 |
| **ファビコン** | ブラウザのタブやブックマークに表示される小さなアイコン。 |
| **Provider（プロバイダー）** | Context の「値を渡す側」のコンポーネント。`AuthProvider` なら「認証情報を子に渡す」役割。 |
| **props** | 親コンポーネントから子コンポーネントへ渡す「引数」のようなデータ。 |
| **props drilling** | 親→子→孫…と、中間のコンポーネントを経由して props を渡し続けること。深くなると面倒なので、Context や状態管理で避けることが多い。 |
| **frontend（フロントエンド）** | ユーザーが触れる「画面側」のプログラム。ブラウザで動くReactアプリがフロントエンド。サーバー側はバックエンド。 |
| **マウント** | 画面にReactのコンポーネントを「表示し始める」こと。`root.render(<App />)` で App をマウントする、など。 |
| **manifest（マニフェスト）** | PWA 用の設定ファイル。アプリ名・アイコン・テーマ色などをまとめて書きます。 |
| **モジュール** | ここでは「1つの機能や役割にまとまったファイル・フォルダの塊」の意味。`features/karaoke/` が1モジュール、など。 |
| **モノリス** | 本来は分けた方がよい処理が、1つの大きなファイルに全部入っている状態。修正や分担がしづらくなります。 |
| **ラップ（ラッパー）** | 既存のもの（コンポーネントや関数）を包んで、別の渡し方・条件付けをする層。routeWrapper は「ルート用のラッパー」です。 |
| **ルート（route）** | 「このURLのとき、この画面を表示する」という対応。`/songs` → 楽曲一覧、のように。 |
| **ルーティング** | URLに応じて表示する画面を切り替える仕組み。React Router がその役割を担います。 |
| **lazy 読み込み** | その画面が必要になったタイミングで、その画面のコードを読み込む方式。初回表示を軽くするために使います。 |
| **レイアウト** | ヘッダー・フッター・余白など、複数画面で共通する「骨組み」。中身（本文）だけ差し替えて使い回します。 |
| **保守性** | バグ修正や機能追加をしやすさ。コードの場所が分かりやすく、変更の影響範囲が限られていると保守性が高いと言います。 |
| **拡張性** | 新機能を足していきやすさ。構造が整理されていると拡張性が高くなります。 |
| **可読性** | コードやフォルダ構成が「読んで分かりやすい」度合い。 |

### ツール・技術名

| 用語 | 説明 |
|------|------|
| **CRA** | Create React App。React プロジェクトを一括で用意してくれる公式のツール。 |
| **ESLint** | コードの書き方の「おかしなところ」や「統一されていないところ」を指摘するツール。 |
| **Jest** | JavaScript/React のテストを実行するフレームワーク。`npm test` で動かします。 |
| **PostCSS** | CSS を変換・加工するツール。Tailwind や Autoprefixer は PostCSS のプラグインとして動きます。 |
| **React** | UI をコンポーネント単位で組み立てる JavaScript のライブラリ。 |
| **React Router** | URL と画面の対応（ルーティング）を React で扱うライブラリ。 |
| **Supabase** | 認証・データベースなどを提供するバックエンドサービス。ここでは主にログイン（認証）に利用。 |
| **Tailwind CSS** | クラス名でスタイルを指定する CSS フレームワーク。`className="text-blue-500"` のように書きます。 |
| **TypeScript** | JavaScript に「型」を付けた言語。ミスを減らし、エディタの補完が効きやすくなります。 |
| **Web Vitals** | 表示の速さ・操作の滑らかさなど、体感品質を測る指標。CLS・FID・FCP・LCP・TTFB など。 |
| **axios** | HTTP 通信（API 呼び出し）をするためのライブラリ。 |
| **PWA** | Progressive Web App。スマホのホーム画面に追加してアプリのように使えるWebアプリの仕様。 |
| **robots.txt** | 検索エンジンのクローラー（巡回ロボット）に「このページを読んでよいか」を伝えるファイル。 |
