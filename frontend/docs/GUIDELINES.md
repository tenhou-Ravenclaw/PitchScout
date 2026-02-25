# ピッチスカウト フロントエンド ガイドライン

> デザインルール、コンポーネント設計、型安全性、コーディング規約

---

## 1. デザインルール

### 1.1 カラーパレット (ダークテーマ)

| 用途            | カラー              | Tailwind クラス例                     |
| --------------- | ------------------- | ------------------------------------- |
| 背景 (ベース)   | Slate 900           | `bg-slate-900`                        |
| カード背景      | Slate 900/60 + blur | `bg-slate-900/60 backdrop-blur-md`    |
| ボーダー        | White 10%           | `border border-white/10`              |
| アクセント (主) | Cyan                | `text-cyan-400`, `border-cyan-500/30` |
| アクセント (副) | Pink / Rose         | `text-pink-500`, `text-rose-400`      |
| 成功 / 地声     | Indigo              | `bg-indigo-500`                       |
| 成功 / 裏声     | Emerald             | `bg-emerald-400`                      |
| スコア (高)     | Emerald             | `text-emerald-500`                    |
| スコア (中)     | Sky / Amber         | `text-sky-500`, `text-amber-500`      |
| スコア (低)     | Rose                | `text-rose-400`                       |

### 1.2 Glassmorphism カードパターン

標準的なカードスタイル:

```
bg-slate-900/60 backdrop-blur-md rounded-2xl shadow-xl border border-white/10
```

### 1.3 レスポンシブ方針

| ブレークポイント   | ナビゲーション                              |
| ------------------ | ------------------------------------------- |
| `md` 以上 (768px+) | `Header` を表示 (`hidden md:flex`)          |
| `md` 未満          | `BottomNav` を表示 (`md:hidden`)            |
| コンテンツ         | `pb-24 md:pb-0` で BottomNav 分の余白を確保 |

---

## 2. コンポーネント設計

### 2.1 ディレクトリ構造

`components/` は機能と責務別に3つのサブディレクトリに整理:

#### `layout/` — レイアウト・ナビゲーション (3 ファイル)

- `Header.tsx`: デスクトップヘッダー（検索バー + ナビゲーション + ログイン/ログアウト）
- `BottomNav.tsx`: モバイルボトムナビゲーション
- `Layout.tsx`: 全ページ共通レイアウト（Header/BottomNav + Outlet）

#### `ui/` — 再利用可能な UI 部品 (9 ファイル)

- **`cards/`**: 汎用カードコンポーネント (3)
  - `AnalysisCardShell.tsx`: 録音/アップロード画面の共通カード枠
  - `AuthRequiredCard.tsx`: 未ログイン時の共通カード
  - `CenteredCardShell.tsx`: 中央配置カードの共通ベース
- `ErrorBanner.tsx`: エラー表示バナー
- `LogoSplash.tsx`: ロゴシャドウアニメーション
- `Pagination.tsx`: ページネーション UI
- `SearchBar.tsx`: 楽曲検索バー
- `SyllableIndex.tsx`: 五十音インデックスナビゲーション
- `Toast.tsx`: トースト通知

#### `features/` — 機能固有コンポーネント (4 ファイル)

- `Recorder.tsx`: マイク録音 + 波形ビジュアライザー
- `Recorder.css`: Recorder 専用スタイル
- `KaraokeUploader.tsx`: カラオケ音源アップロード UI
- `ResultView.tsx`: 分析結果の詳細表示

### 2.2 責務分離の原則

| ディレクトリ                | 責務                             | Context 依存 | 例                               |
| --------------------------- | -------------------------------- | ------------ | -------------------------------- |
| `pages/`                    | 表示とユーザー操作のハンドリング | ❌ 禁止      | `HistoryPage.tsx`                |
| `components/ui/`            | 再利用可能な UI 部品             | ❌ 禁止      | `Toast.tsx`, `ErrorBanner.tsx`   |
| `components/features/`      | 機能固有の複雑なコンポーネント   | ⚠️ 最小限    | `Recorder.tsx`, `ResultView.tsx` |
| `components/layout/`        | レイアウト・ナビゲーション       | ✅ 許可      | `Header.tsx`, `BottomNav.tsx`    |
| `routes.tsx` (ラッパー関数) | Context とページの橋渡し         | ✅ 必須      | `HistoryRoute`, `AnalysisRoute`  |

### 2.3 Context 依存を避ける（ページコンポーネント）

`pages/` 配下のページコンポーネントは Context に直接依存せず、Props のみを受け取る:

```typescript
// ✅ ページコンポーネント（Context 非依存）
interface HistoryPageProps {
  isAuthenticated: boolean;
  onLoginClick: () => void;
  onSelectRecord: (record: AnalysisHistoryRecord) => void;
}

const HistoryPage: React.FC<HistoryPageProps> = ({
  isAuthenticated,
  onLoginClick,
  onSelectRecord
}) => {
  // Context を使わず、Props で制御
};

// ✅ ルートラッパー（routes.tsx 内で定義）
const HistoryRoute = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const { setResult, setIsFromHistory } = useAppContext();

  const handleSelectRecord = (record: AnalysisHistoryRecord) => {
    // Context 更新と遷移をラッパー側で処理
    setResult(record.result_json);
    setIsFromHistory(true);
    navigate("/result");
  };

  return (
    <HistoryPage
      isAuthenticated={isAuthenticated}
      onLoginClick={() => navigate("/login")}
      onSelectRecord={handleSelectRecord}
    />
  );
};
```

**メリット:**

- ページコンポーネントの再利用性向上
- テストが容易（Context のモックが不要）
- 依存関係の明示化（Props を見れば必要なデータが分かる）

---

## 3. 型安全性とコーディング規約

### 3.1 TypeScript 型安全性の原則

**絶対禁止事項:**

- **`any` 型の使用を禁止** — 全ての関数・変数・Props に明示的な型を付ける
- 外部ライブラリの型が不明な場合も `any` を使わず、`unknown` や型推論を活用する

**推奨パターン:**

#### エラーハンドリングには `unknown` を使用

```typescript
// ❌ 悪い例
try {
  await someApiCall();
} catch (err: any) {
  console.error(err.message); // any による型安全性の喪失
}

// ✅ 良い例
try {
  await someApiCall();
} catch (err: unknown) {
  const message =
    err instanceof Error ? err.message : "不明なエラーが発生しました";
  console.error(message);
}
```

#### 外部ライブラリの型は `Parameters<>` を活用

Web Audio API など、TypeScript の lib 定義が環境により異なる場合:

```typescript
// ❌ 手動で型を推測（環境依存で失敗しやすい）
const dataArray: Uint8Array<ArrayBuffer> = new Uint8Array(bufferLength);

// ✅ Parameters<> で API から型を抽出
type AnalyzerFrequencyData = Parameters<
  AnalyserNode["getByteFrequencyData"]
>[0];
const dataArrayRef = useRef<AnalyzerFrequencyData | null>(null);

// 使用時
dataArrayRef.current = new Uint8Array(
  new ArrayBuffer(analyserRef.current.frequencyBinCount),
) as AnalyzerFrequencyData;
analyserRef.current.getByteFrequencyData(dataArrayRef.current);
```

**理由:** 手動で型を指定すると TypeScript のバージョンやlib定義の違いでエラーが発生する。`Parameters<>` を使えば API の実際のシグネチャから型を取得できる。

#### API パラメータには具体的な型を定義

```typescript
// ❌ 汎用的すぎる型
function getSongs(params: Record<string, any>) { ... }

// ✅ 明示的な型定義
type SongQueryParams = {
  limit?: number;
  offset?: number;
  q?: string;
  chest_min_hz?: number;
  chest_max_hz?: number;
  falsetto_max_hz?: number;
};

function getSongs(params: SongQueryParams) { ... }
```

#### Type Guard でランタイム安全性を確保

```typescript
// ❌ 型アサーションで安全性を失う
if (!displayData || (displayData as any).error) { ... }

// ✅ Type Guard で型安全にチェック
const hasAnalysisError = (
  data: AnalysisResult | IntegratedVocalRange | null,
): data is AnalysisResult & { error: string } => {
  return !!data && "error" in data && typeof data.error === "string" && data.error.length > 0;
};

if (!displayData || hasAnalysisError(displayData)) { ... }
```

### 3.2 ドキュメンテーション規約

**全てのファイルに日本語のドキュメンテーションコメントを含める:**

```typescript
/**
 * 【HistoryPage.tsx】
 * 役割：過去の音声解析結果を一覧で表示し、管理（閲覧・削除）するためのページです。
 * 特徴：スマホでの「スワイプ削除」と、PCでの「削除ボタン」の両方に対応した高度なUIを備えています。
 */

/**
 * 分析履歴レコードを選択したときのハンドラ
 * @param record - 選択された履歴レコード
 */
const handleSelectRecord = (record: AnalysisHistoryRecord) => {
  // ...
};
```

- **ファイル冒頭**: ファイルの役割と特徴を説明
- **関数・コンポーネント**: JSDoc で引数・返り値・用途を説明
- **複雑なロジック**: インラインコメントで「なぜそうしているか」を説明

### 3.3 よくある間違いと解決策

| 問題                 | 悪い例                               | 良い例                              |
| -------------------- | ------------------------------------ | ----------------------------------- |
| 暗黙的な any         | `onSubmit={(query) => ...}`          | `onSubmit={(query: string) => ...}` |
| 型アサーションの乱用 | `(data as any).error`                | Type Guard 関数を定義               |
| 不明確なエラー型     | `catch (err: any)`                   | `catch (err: unknown)`              |
| 汎用的すぎる型       | `Record<string, any>`                | 具体的な interface/type を定義      |
| Context の過剰な使用 | ページコンポーネント内で `useAuth()` | ルートラッパーで Props として渡す   |

---

## 関連ドキュメント

- [ARCHITECTURE.md](./ARCHITECTURE.md) - システム構造とアーキテクチャ
- [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) - 実装詳細ガイド
