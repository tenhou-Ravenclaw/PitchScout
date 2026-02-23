/**
 * 【App.tsx】
 * 役割：アプリの「ルート（根っこ）」となるコンポーネントです。
 * 全体のルーティング（画面遷移）の設定や、アプリ全体で共有するデータ（Context）を定義します。
 * 💡 設計図（FRONTEND_STRUCTURE.md）に基づく移動案：
 * 1. 移動先: src/app/App.tsx
 * 2. 理由：App.tsx は「アプリ全体の設定」に関するファイルなので、
 * 画面（pages）や部品（components）とは別に「app」フォルダにまとめると整理しやすくなります。
 */

import { BrowserRouter, useRoutes } from "react-router-dom";
import { useState } from "react";
// アプリ全体でデータを共有するための「Provider（提供者）」たち
import { AuthProvider } from "./contexts/AuthContext";
import { AnalysisProvider } from "./contexts/AnalysisContext";
import { AppProvider } from "./contexts/AppContext";
// 画面遷移の地図（ルート定義）
import { routes } from "./routes";
// 起動時のロゴアニメーション部品
import { LogoSplash } from "./components/LogoSplash";

/**
 * ── ルーティングの実行 ──
 * routes.tsx で定義した「URLと画面のペア」を、実際に有効化します。
 */
function AppRoutes() {
  // useRoutes は、現在のURLに合ったコンポーネントを返してくれるReact Routerの機能です
  return useRoutes(routes);
}

/**
 * ── アプリ本体（メインエントリ） ──
 */
export default function App() {
  // ── 状態管理 (State) ──
  // 起動時のロゴスプラッシュを表示するかどうかのフラグ
  // true: 表示する, false: 非表示
  const [showSplash, setShowSplash] = useState(true);

  /**
   * ロゴアニメーションが終わった時に呼ばれる関数
   */
  const handleSplashEnd = () => {
    // スプラッシュ画面を非表示にする
    setShowSplash(false);
  };

  return (
    /**
     * BrowserRouter: アプリに「URLによる画面遷移機能」を持たせます
     */
    <BrowserRouter>
      {/**
       * ── 各種 Provider（データの入れ物） ──
       * 下にあるコンポーネントほど、上の Provider が持っているデータにアクセスできます。
       * 1. AuthProvider: ログインユーザーの情報
       * 2. AnalysisProvider: 現在の音声解析の状態
       * 3. AppProvider: アプリ全体の共通設定や検索クエリなど
       */}
      <AuthProvider>
        <AnalysisProvider>
          <AppProvider>
            
            {/* ── 演出：ロゴスプラッシュ ──
                showSplash が true の間だけ表示されます。
                アニメーション完了時に handleSplashEnd を呼び出します。
            */}
            {showSplash && <LogoSplash onAnimationEnd={handleSplashEnd} />}

            {/* ── メインコンテンツ ──
                URLに応じた画面（Home, SongList, Historyなど）がここに表示されます。
            */}
            <AppRoutes />

          </AppProvider>
        </AnalysisProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}