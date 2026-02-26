# ピッチスカウト フロントエンド 実装ガイド

> Result/Analysis 責務分離、エラーUX、API/Context 不変条件、検証項目

---

## 1. `/result` と `/analysis` の責務分離仕様

### 1.1 責務比較表

| 項目       | `/result`                                    | `/analysis`                                           |
| ---------- | -------------------------------------------- | ----------------------------------------------------- |
| 目的       | 録音/アップロード直後の確認                  | 詳細分析と継続利用のハブ                              |
| 主な入口   | `/record`, `/karaoke`, `/upload`, `/history` | Header/BottomNav、直接アクセス                        |
| 主データ源 | `AppContext.result`                          | `AppContext.result` + （ログイン時）`integratedRange` |
| 表示責務   | 直近結果の要約、次アクション導線             | 統合音域、詳細スコア、比較的な閲覧                    |
| 非責務     | 履歴統合計算、重い比較表示                   | 録音直後の短導線最適化                                |
| 期待滞在   | 短時間（次の画面へ遷移）                     | 中長時間（参照・比較）                                |

### 1.2 遷移ルール

- 録音/アップロード完了後は必ず `/result` に遷移する。
- `/result` は「録音導線の一部」とし、詳細閲覧が必要な場合のみ `/analysis` へ遷移する。
- `/analysis` は独立ページとして直接アクセス可能にする。
- 履歴選択からの遷移は `/result` を経由し、`isFromHistory` で戻り先を制御する。
- `Header` / `BottomNav` の「声域分析」は `/analysis` を正とする。

### 1.3 コンポーネント境界

| コンポーネント       | 受け取る入力                                        | 主な出力/副作用                                              | 責務                                         | 非責務                                       |
| -------------------- | --------------------------------------------------- | ------------------------------------------------------------ | -------------------------------------------- | -------------------------------------------- |
| `ResultPage`         | `result`, `isFromHistory`, `onBack`                 | 戻る遷移（`/menu` or `/history`）                            | 中間結果ページの導線制御                     | 統合音域計算、詳細比較表示                   |
| `ResultView`         | `result: AnalysisResult`                            | なし（表示専用）                                             | 単発結果の要約表示（音域・スコア・おすすめ） | ルーティング、履歴統合取得、認証依存ロジック |
| `AnalysisRoute`      | `AppContext.result`, `AuthContext.isAuthenticated`  | `AnalysisResultPage` へ受け渡し                              | Context とページの橋渡し                     | 描画ロジック本体                             |
| `AnalysisResultPage` | `result: AnalysisResult \| null`, `isAuthenticated` | `getIntegratedVocalRange(20)` 取得、お気に入り操作           | 詳細分析表示と統合音域表示の切替             | 録音直後導線の戻り制御                       |
| `HistoryRoute`       | `AnalysisHistoryRecord` 選択イベント                | `setResult`, `setIsFromHistory(true)`, `navigate("/result")` | 履歴データを結果表示に接続                   | 詳細分析ページ直接遷移の強制                 |

### 1.4 実装契約

- `ResultView` は **表示専用コンポーネント** とし、API 呼び出しや `navigate` を持たない。
- `ResultPage` は **導線制御コンテナ** とし、表示本体を `ResultView` に委譲する。
- `AnalysisResultPage` は **詳細分析コンテナ** とし、ログイン時のみ統合音域 API を呼ぶ。
- 履歴選択時は `HistoryRoute` が `AppContext` を更新して `/result` へ遷移し、戻り先判定を `isFromHistory` で一元化する。
- `/analysis` は独立アクセス可能とし、`result` が空の場合は「分析データがありません」表示を返す。

### 1.5 データ受け渡しフロー

```
RecorderRoute/UploaderRoute
  └─ setResult(data), setIsFromHistory(false), navigate("/result")
       └─ ResultRoute
           └─ ResultPage(result, isFromHistory, onBack)

HistoryRoute
  └─ setResult(record.result_json or fallback), setIsFromHistory(true), navigate("/result")

AnalysisRoute
  └─ AnalysisResultPage(result, isAuthenticated)
       └─ (isAuthenticated) getIntegratedVocalRange(20)
```

---

## 2. エラー UX 統一方針

### 2.1 現状（2026-02 時点）

- インライン表示（`setError`）と `alert` と `console.error` の3系統が混在している。
- `alert` は録音開始失敗・履歴削除失敗・お気に入り操作失敗で使われている。
- API 失敗でもユーザー通知がなく、ログ出力のみで終わる導線が存在する。

### 2.2 統一ルール

| エラー種別                       | 表示手段                           | 例                               | 備考                                     |
| -------------------------------- | ---------------------------------- | -------------------------------- | ---------------------------------------- |
| ブロッキング（操作が継続不能）   | インラインエラーバナー（画面上部） | 解析失敗、履歴取得失敗           | 再試行導線を併設                         |
| アクション失敗（画面は継続可能） | 画面内トースト（非モーダル）       | お気に入り追加/削除失敗          | 現在の状態は維持し、必要ならロールバック |
| 入力バリデーション               | フィールド近傍のインライン表示     | 非対応ファイル形式、必須入力不足 | どこを直せば良いかを明示                 |
| 開発者向け詳細                   | `console.error`                    | 例外オブジェクト、stack          | ユーザー向け表示と必ず併用               |

### 2.3 禁止/推奨

**禁止:**

- ユーザー操作に対する失敗を `console.error` のみで終える実装
- 新規実装での `alert` 追加（現行は `window.confirm` のみ残存）

**推奨:**

- API 失敗時は「短い日本語メッセージ + 再試行アクション」を標準化する
- ネットワークエラー / タイムアウト / 認証エラーをメッセージレベルで分類する

### 2.4 導線別の適用優先度

| 優先度 | 対象画面                       | 現状                                                 | 方針                                                       |
| ------ | ------------------------------ | ---------------------------------------------------- | ---------------------------------------------------------- |
| 高     | `Recorder` / `KaraokeUploader` | timeout・network は一部整備済み、`alert` は未使用    | インライン表示とトーストの運用ルールを固定                |
| 高     | `HistoryPage`                  | 取得は `setError`、削除前確認に `window.confirm` を使用 | 削除失敗通知はトースト継続、確認UIの将来的な統一を検討     |
| 高     | `SongListPage`                 | `setError` + トースト + ログの併用                    | 一覧取得失敗はインライン、お気に入り系はトーストで維持     |
| 中     | `AnalysisResultPage`           | トースト + ログ                                      | 統合音域失敗はページ内通知またはトーストに統一             |
| 中     | `FavoritesPage`                | `setError` + トースト                                | 取得失敗はインライン、削除失敗はトーストの方針を維持       |

### 2.5 実装メモ

- 共通 UI として `ErrorBanner` / `Toast` を用意し、ページ個別実装を減らす。
- API エラーの変換関数（例: `toUserMessage(error)`）を `api/` 近傍に集約する。
- 10分タイムアウト方針は現行のまま維持し、メッセージのみ統一する。

---

## 3. API / Context 不変条件

### 3.1 API 層の不変条件

| 対象                | 不変条件                                          | 理由                                        |
| ------------------- | ------------------------------------------------- | ------------------------------------------- |
| `api/client.ts`     | `TIMEOUT_MS = 600000`（10分）を維持する           | Demucs を含む長時間解析に必要               |
| `api/client.ts`     | API 通信は `API` インスタンス経由に統一する       | 認証ヘッダー・timeout・baseURL の一貫性確保 |
| `api/client.ts`     | JWT 自動付与インターセプターを維持する            | 手動ヘッダー付与漏れを防ぐ                  |
| `supabaseClient.ts` | `supabase: SupabaseClient \| null` を維持する     | 環境変数未設定時でも認証以外を動作させる    |
| `api.ts`            | `src/api/` の再エクスポート互換レイヤーを維持する | 既存 import 破壊を防ぐ段階移行のため        |

### 3.2 Context 層の不変条件

| Context           | 不変条件                                                                       | 理由                                       |
| ----------------- | ------------------------------------------------------------------------------ | ------------------------------------------ |
| `AuthContext`     | `supabase === null` 時は `isLoading` を解放し、認証なしモードで動作する        | ローカル/検証環境での可用性確保            |
| `AuthContext`     | `onAuthStateChange` 監視を維持する                                             | OAuth リダイレクト後のセッション復元に必要 |
| `AppContext`      | `result` を唯一の「最新解析結果ソース」とする                                  | Result/Analysis の整合性確保               |
| `AppContext`      | `isFromHistory` で `/result` の戻り先を判定する仕様を維持する                  | 履歴導線の UX 一貫性                       |
| `AppContext`      | `voiceRange` 永続化キーを維持する                                              | 楽曲キー提案の継続性                       |
| `AnalysisContext` | 解析ステップの進捗管理（`isAnalyzing/progress/stepLabel`）を単一責務で保持する | 進捗UIの同期を崩さないため                 |

### 3.3 変更時のガードレール

- 新規 API 呼び出しを追加する場合、`fetch`/生 axios 直呼びではなく `api/` モジュールに関数追加する。
- Context 追加時は「どのデータをどこが唯一の更新責務として持つか」を先に定義する。
- `result` 由来の表示（`/result`, `/analysis`）で別 state を二重管理しない。
- 認証依存機能は必ず `supabase === null` パスを考慮する。

---

## 4. 検証項目と移行順

### 4.1 受け入れ検証チェックリスト

| 区分         | チェック項目         | 合格条件                                                             |
| ------------ | -------------------- | -------------------------------------------------------------------- |
| ルーティング | 録音導線             | `/record` / `/karaoke` / `/upload` 完了後に必ず `/result` へ遷移する |
| ルーティング | 分析導線             | `Header` / `BottomNav` の「声域分析」で `/analysis` に遷移する       |
| ルーティング | 履歴導線             | 履歴選択後 `/result` 表示、戻る操作で `/history` に戻る              |
| 表示責務     | Result/Analysis 分離 | `/result` は中間結果、`/analysis` は統合音域/詳細表示を担当          |
| エラーUX     | ユーザー通知         | API 失敗が `console.error` のみで終わらない                          |
| エラーUX     | alert置換            | 新規 `alert` 追加がない（既存は段階的置換）                          |
| API 契約     | 10分タイムアウト     | `TIMEOUT_MS = 600000` が維持される                                   |
| API 契約     | 認証ヘッダー         | ログイン時に `Authorization: Bearer` が自動付与される                |
| Null安全     | Supabase未設定       | `supabase === null` でも非認証機能が動作する                         |
| Context 契約 | 単一ソース           | `result` は `AppContext` を唯一のソースとして参照される              |

### 4.2 手動確認シナリオ（最小セット）

1. `menu` → `record` で録音し、`/result` 表示後に「トップへ戻る」で `/menu` へ戻る。
2. `menu` → `upload` で解析し、タイムアウト/通信断時のエラーメッセージを確認する。
3. `history` から履歴選択し、`/result` で「履歴に戻る」が機能することを確認する。
4. `/analysis` を直接開き、ログイン有無で表示（統合音域あり/なし）が破綻しないことを確認する。
5. `songs` / `favorites` / `history` で API 失敗時の通知が画面で確認できることを確認する。

### 4.3 自動確認（推奨）

- `frontend` で `npm test -- --watchAll=false` を実行し、回帰を確認する。
- 必要に応じて `npm run build` を実行し、型・ビルド整合性を確認する。

### 4.4 実装移行順（推奨）

| フェーズ | 目的                             | 主対象                                                       |
| -------- | -------------------------------- | ------------------------------------------------------------ |
| Phase 1  | エラーUX土台の統一               | `Recorder`, `KaraokeUploader`, `HistoryPage`, `SongListPage` |
| Phase 2  | `alert` 段階置換と通知統一       | `AnalysisResultPage`, `FavoritesPage`                        |
| Phase 3  | Result/Analysis 境界の実装最終化 | `ResultPage`, `ResultView`, `AnalysisRoute`, `HistoryRoute`  |
| Phase 4  | API 呼び出しの集約整理           | `src/api/*` と利用側 import 整理                             |
| Phase 5  | 回帰検証と最終調整               | 全導線の手動確認 + テスト/ビルド                             |

### 4.5 完了定義（Definition of Done）

- Result/Analysis の責務分離がコード上でも確認できる。
- API/Context の不変条件が崩れていない（timeout, nullable supabase, interceptor）。
- 主要導線でエラー通知の一貫性が担保されている。
- 本ガイドの内容が最新実装と矛盾しない。

---

## 5. コンポーネント Props 仕様

> **Note**: 各コンポーネントの詳細なドキュメントはソースコード内の JSDoc を参照してください。ここでは主要コンポーネントの概要のみ記載します。

### 5.1 Header

| Props             | 型                        | 説明                               |
| ----------------- | ------------------------- | ---------------------------------- |
| `currentPath`     | `string`                  | 現在の URL パス (アクティブ表示用) |
| `searchQuery`     | `string`                  | 検索バーの値                       |
| `onSearchChange`  | `(query: string) => void` | 検索入力ハンドラ                   |
| `isAuthenticated` | `boolean`                 | ログイン状態                       |
| `userName`        | `string \| null`          | 表示名                             |

※ 画面遷移とログイン/ログアウト処理はコンポーネント内で `navigate` / `useAuth` を利用して実行する。

### 5.2 BottomNav

| Props             | 型        | 説明                                   |
| ----------------- | --------- | -------------------------------------- |
| `currentPath`     | `string`  | 現在の URL パス                        |
| `isAuthenticated` | `boolean` | ログイン状態 (マイページ/ログイン切替) |

### 5.3 Recorder

| Props              | 型                               | 説明                            |
| ------------------ | -------------------------------- | ------------------------------- |
| `onResult`         | `(data: AnalysisResult) => void` | 分析結果コールバック            |
| `initialUseDemucs` | `boolean`                        | true: カラオケモード (BGM 除去) |

- Web Audio API で波形ビジュアライザー (Canvas) を描画
- MediaRecorder API でブラウザ録音

### 5.4 KaraokeUploader

| Props      | 型                               | 説明                 |
| ---------- | -------------------------------- | -------------------- |
| `onResult` | `(data: AnalysisResult) => void` | 分析結果コールバック |

- 対応フォーマット: WAV, MP3, M4A, AAC, MP4, OGG, FLAC, WMA, WebM
- 結果は `onResult` 経由で親ページに返し、`/result` へ遷移する

### 5.5 ResultView

| Props    | 型               | 説明                                   |
| -------- | ---------------- | -------------------------------------- |
| `result` | `AnalysisResult` | バックエンドからの分析結果オブジェクト |

表示セクション:

1. 声質タイプ + 全体音域
2. 地声/裏声バランスバー
3. 地声・裏声の詳細カード
4. 歌唱力スコア (総合・音域・安定性・表現力)
5. 声が似ているアーティスト
6. おすすめ曲リスト

---

## 関連ドキュメント

- [ARCHITECTURE.md](./ARCHITECTURE.md) - システム構造とアーキテクチャ
- [GUIDELINES.md](./GUIDELINES.md) - デザイン・コーディング規約
