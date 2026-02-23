# frontend ディレクトリ構造・ワークフロー・役割・課題と改善案

## 現在のディレクトリ構造

```
frontend/
├── package.json
├── postcss.config.js
├── README.md
├── tailwind.config.js
├── tsconfig.json
├── docs/
│   └── ARCHITECTURE.md
├── public/
│   ├── index.html
│   ├── manifest.json
│   └── robots.txt
├── src/
│   ├── AnalysisResultPage.tsx
│   ├── api.ts
│   ├── App.test.tsx
│   ├── App.tsx
│   ├── FavoritesPage.tsx
│   ├── GuidePage.tsx
│   ├── HistoryPage.tsx
│   ├── Home.tsx
│   ├── HomePage.css
│   ├── index.css
│   ├── index.tsx
│   ├── Landing.tsx
│   ├── LoginPage.tsx
│   ├── react-app-env.d.ts
│   ├── reportWebVitals.ts
│   ├── routes.tsx
│   ├── setupTests.ts
│   ├── SongListPage.tsx
│   ├── supabaseClient.ts
│   ├── assets/
│   ├── components/
│   │   ├── BottomNav.tsx
│   │   ├── Header.tsx
│   │   ├── KaraokeUploader.tsx
│   │   ├── Layout.tsx
│   │   ├── LogoSplash.tsx
│   │   ├── Recorder.css
│   │   ├── Recorder.tsx
│   │   ├── ResultView.tsx
│   │   └── SongTable.tsx
│   ├── constants/
│   │   └── searchAliases.ts
│   ├── contexts/
│   │   ├── AnalysisContext.tsx
│   │   ├── AppContext.tsx
│   │   └── AuthContext.tsx
│   ├── pages/
│   │   ├── RecorderPage.tsx
│   │   ├── ResultPage.tsx
│   │   └── UploaderPage.tsx
│   ├── routeWrappers/
│   │   ├── AnalysisRoute.tsx
│   │   ├── FavoritesRoute.tsx
│   │   ├── HistoryRoute.tsx
│   │   ├── HomeRoute.tsx
│   │   ├── LandingRoute.tsx
│   │   └── SongListRoute.tsx
│   └── styles/
│       └── LogoSplash.css
```

## ワークフロー

1. **開発**: `src/`配下でReactコンポーネントやページ、ロジックを実装。
2. **スタイリング**: `styles/`や`public/`、`tailwind.config.js`などでデザインを調整。
3. **ビルド/テスト**: `App.test.tsx`や`setupTests.ts`でテスト、`package.json`のスクリプトでビルド。
4. **デプロイ**: ビルド成果物を`public/`や外部にデプロイ。

## 各ディレクトリ・ファイルの役割

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

## 構造の問題点

- `src/`直下にページやロジックが混在し、肥大化しやすい
- `pages/`と`src/`直下のページコンポーネントの役割が曖昧
- `routeWrappers/`の責務が不明瞭になりやすい
- `assets/`や`styles/`が用途別に整理されていない可能性
- テストファイルが`src/`直下にあり、規模拡大時に管理しづらい

## 改善案

1. **ディレクトリの整理**
   - `src/pages/`に全ページコンポーネントを集約し、`src/`直下から移動
   - `src/hooks/`や`src/utils/`など、ロジックや共通処理を分離
   - テストは`__tests__/`や各ディレクトリ内に配置
2. **責務の明確化**
   - `routeWrappers/`はルーティングや認証ガード専用に限定
   - `components/`はUI部品のみ、ロジックは`hooks/`や`utils/`へ
3. **アセット・スタイルの整理**
   - `assets/`を画像・フォント・アイコン等でサブディレクトリ化
   - `styles/`もグローバル・モジュール・テーマ等で分割
4. **ドキュメントの充実**
   - ディレクトリごとにREADMEを設置し、役割を明記

---

この改善により、可読性・保守性・拡張性が向上し、チーム開発や将来的な機能追加にも柔軟に対応できます。

## React開発のベストプラクティスに沿ったディレクトリ構造例

以下は、近年のReactプロジェクトで推奨される構造例です。

```
src/
   assets/           # 画像・フォント・静的アセット
   components/       # 再利用可能なUI部品
   hooks/            # カスタムフック
   layouts/          # 複数ページで使うレイアウト
   pages/
      Home/
         index.tsx     # Homeページ本体
         HomeHeader.tsx
         HomeContent.tsx
         Home.module.css
         Home.test.tsx
      Login/
         index.tsx
         LoginForm.tsx
         Login.module.css
         Login.test.tsx
      ...
   providers/        # ContextやProvider系
   routes/           # ルーティング定義
   utils/            # 汎用関数・ロジック
   constants/        # 定数
   styles/           # グローバルCSSやテーマ
   main.tsx          # エントリーポイント
```

### 特徴・ポイント

- **ページ単位でディレクトリ分割**: `pages/`配下に各ページごとのディレクトリを作り、関連するUI・ロジック・スタイル・テストを集約
- **UI部品とロジックの分離**: `components/`は再利用可能なUIのみ、ロジックは`hooks/`や`utils/`へ
- **ContextやProviderの集約**: `providers/`で状態管理を一元化
- **レイアウトの共通化**: `layouts/`で複数ページ共通のレイアウトを管理
- **ルーティングの明確化**: `routes/`でルート定義やガードを管理
- **アセット・スタイルの細分化**: `assets/`や`styles/`で用途別に整理

### 参考: Next.jsやモダンReactの潮流

- Next.jsなどのフレームワークでも「ページ単位のディレクトリ分割」「UI/ロジック/スタイルの分離」が主流
- プロジェクト規模やチーム人数が増えても保守しやすい

---
このような構造にリファクタすることで、可読性・保守性・拡張性が大幅に向上します。

## 共通化の提案（現状コード分析より）

### 1. React RouterのuseNavigate, useLocationの共通化

- 多くのページやラッパーで `useNavigate`, `useLocation` を個別に呼び出しているため、
  - ルーティング操作や画面遷移の共通ロジック（例：`useAppNavigation` カスタムフック）としてまとめると保守性向上。

### 2. Contextの利用パターンの共通化

- `useAppContext`, `useAuth`, `useAnalysis` などContextの呼び出しが多い。
  - Contextの値取得や更新ロジックをカスタムフックやProviderで整理し、props drillingを減らす。

### 3. API通信・型定義の共通化

- `api.ts`でAPI通信・型定義が集中しているが、
  - APIごとにhooks（例：`useFavorites`, `useAnalysisResult`）を作成し、UI側はhooks経由でデータ取得・更新する形に統一するとテスト・再利用性が高まる。

### 4. UI部品の共通化

- ヘッダー・ナビゲーション・ローディング・エラーメッセージなど、複数ページで使うUIは `components/` に集約。
  - 例：`<Header />`, `<BottomNav />`, `<LoadingSpinner />`, `<ErrorMessage />` など

### 5. フォーム・バリデーションの共通化

- 入力フォームやバリデーション処理が複数箇所で発生する場合、
  - 共通のカスタムフック（例：`useForm`, `useInput`）やユーティリティ関数として切り出すと良い。

### 6. スタイル・クラス名の共通化

- ボタンや入力欄などのスタイルが重複している場合、
  - 共通CSSモジュールやTailwindのカスタムクラスで一元管理。

---
これらの共通化を進めることで、重複コードの削減・保守性向上・バグの減少が期待できます。
具体的な共通化案や実装例が必要な場合は、個別にご相談ください。

## 共通化を進めた場合の推奨ディレクトリ構造例

```
src/
   api/                # API通信・型定義・API hooks
      index.ts          # APIクライアントのエントリーポイント
      favorites.ts      # お気に入り関連API
      analysis.ts       # 分析関連API
      ...
   components/         # 再利用可能なUI部品
      Header/
      BottomNav/
      LoadingSpinner/
      ErrorMessage/
      ...
   hooks/              # カスタムフック（useAppNavigation, useFavorites, useFormなど）
   contexts/           # Context/Provider
   pages/              # ページ単位のディレクトリ
      Home/
      Login/
      ...
   forms/              # フォーム部品・バリデーション共通化
      useForm.ts
      useInput.ts
      ...
   layouts/            # 共通レイアウト
   routes/             # ルーティング定義
   styles/             # グローバル・共通スタイル
      variables.css
      button.module.css
      ...
   utils/              # 汎用関数・ユーティリティ
   assets/             # 画像・フォント等
   constants/          # 定数
   main.tsx            # エントリーポイント
```

### ポイント

- API通信・型定義は `api/` に集約し、hooks化してUIから直接呼ばない
- 共通UI部品は `components/`、フォーム系は `forms/` に分離
- hooks/ でロジックの共通化、utils/ で汎用関数を管理
- ページ単位のディレクトリで自己完結性を高める

このような構造にすることで、共通化の恩恵を最大限に活かしつつ、保守性・拡張性・可読性を高めることができます。
