# PitchScout 全体まとめ（Backend + Frontend）

このドキュメントは、プロジェクト全体をざっくり把握するためのメモ。
詳細仕様ではなく、構成・処理フロー・主要ロジックの要点をまとめる。

## 1. プロジェクト全体像

- 目的: 音声から声域を推定し、歌いやすい楽曲を推薦する
- フロントエンド: React + TypeScript
- バックエンド: FastAPI + Python
- データ:
	- 楽曲カタログ: SQLite (`backend/songs.db`)
	- ユーザー情報/履歴/お気に入り: Supabase

## 2. Frontend の役割

主に次の4つを担当する。

1. 音声入力 UI
- マイク録音
- カラオケ音源アップロード

2. 解析リクエスト送信
- Axios クライアントを通して API 呼び出し
- 認証時は JWT を自動付与

3. 結果表示
- 地声/裏声の音域
- 推薦楽曲
- 履歴表示

4. 認証とユーザー機能
- Supabase OAuth（Google）
- お気に入り・履歴・プロフィール

### 2.1 主な構造

- `App.tsx`: Router + Provider 初期化
- `routes.tsx`: ルート定義
- `contexts/`
	- `AuthContext.tsx`: ログイン状態管理
	- `AnalysisContext.tsx`: 解析進捗管理
	- `AppContext.tsx`: 画面共有状態
- `api/`
	- `client.ts`: Axios インスタンス
	- `analysis.ts`, `songs.ts`, `listApi.ts` など API 群
- `pages/`: 各画面コンポーネント
- `components/`: UI 共通部品

### 2.2 認証フロー（Frontend）

1. `loginWithGoogle()` で Supabase OAuth を開始
2. 戻ってきたセッションを `AuthContext` が取得
3. `api/client.ts` の interceptor が JWT を `Authorization` に自動設定
4. 401 時は refresh を試み、失敗時は sign out

## 3. Backend の役割

主に次の5つを担当する。

1. API 提供
- 解析 API
- 楽曲検索 API
- 認証/ユーザー API

2. 音声前処理
- WAV 変換
- Demucs 分離（カラオケモード）
- ノイズ除去

3. 声域解析
- CREPE で f0 推定
- 地声/裏声分類
- 外れ値除去、補正、最高音確定

4. 推薦
- 推定音域と楽曲音域のマッチング

5. 永続化
- 履歴保存
- お気に入り管理

### 3.1 主な構造

- `main.py`: FastAPI 起動、CORS、router 登録
- `routers/`: エンドポイント定義
	- `analysis.py`, `songs.py`, `users.py`, `auth.py`
- `analysis/`: 解析コア
	- `pipeline.py`: 解析メインフロー
	- `classifier.py`: 地声/裏声判定
	- `features.py`, `scoring.py`
- `audio/`: 変換・分離・ノイズ処理
- `db/`: SQLite / Supabase アクセス
- `config.py`: 解析定数を一元管理

## 4. 音声解析パイプライン（要点）

`pipeline.py` 内でおおむね次の順序で処理する。

1. WAV 読み込み
2. 正規化 + 16kHz へ変換
3. CREPE で f0/conf を取得
4. 信頼度フィルタ（段階閾値、最終 0.01 までフォールバック）
5. 人声音域フィルタ
6. 異常値レンジ除去 + オクターブ補正 + 中央値推定
7. フレームごとに地声/裏声分類
8. 裏声ノイズフィルタ
	- 連続フレーム
	- RMS
	- VAD（Demucs 後のみ）
9. 統計外れ値除去
10. 最小比率フィルタ
11. 最高音付近の混在解消
12. ラベル化して結果返却

## 5. `classifier.py` の現在方針

現在の設計意図は次の通り。

- 「ML 全依存」ではなく「音楽ルール主軸」
- ML は地声補助帯域に限定（計算量を抑える）
- 最終品質は `pipeline.py` 側フィルタと組み合わせて担保

`classify_register()` の判断順:

1. ノイズゲート/無効値チェック
2. 低音を地声確定
3. ML 対象帯域なら ML 判定
4. それ以外はルール判定

## 6. データフロー（簡略）

1. Frontend が音声をアップロード
2. Backend が解析して JSON 返却
3. Frontend が結果画面へ反映
4. ログイン中なら Supabase に履歴保存
5. 推薦 API と組み合わせて曲提案

## 7. 設定・運用上の注意

- 解析しきい値は `config.py` に集約（他ファイルにハードコードしない）
- A4 は 442Hz 基準
- 認証は `supabaseClient.ts` / `db/users.py` の有効性に依存
- 重い処理（Demucs + 長尺解析）は API 応答時間が長くなりやすい

## 8. いまの課題感（大まか）

- 長尺カラオケ音源で解析時間が長い
- 裏声の最終残存率が閾値条件に影響されやすい
- ノイズ除去を強くすると本物裏声まで落ちるトレードオフがある

## 9. どこを見れば良いか（用途別）

- 解析結果が不自然: `backend/analysis/pipeline.py`, `backend/analysis/classifier.py`, `backend/config.py`
- ログイン不具合: `frontend/src/contexts/AuthContext.tsx`, `frontend/src/supabaseClient.ts`, `backend/auth.py`
- API 通信不具合: `frontend/src/api/client.ts`, `backend/routers/*.py`
- 推薦の精度/件数: `backend/recommender.py`, `backend/db/songs.py`

---

必要なら次の版で、

- 「解析モード別（マイク/カラオケ）」の分岐図
- 「リクエスト1回分の時系列ログ読み方」

を追加する。