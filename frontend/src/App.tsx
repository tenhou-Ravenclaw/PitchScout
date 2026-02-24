/**
 * 【App.tsx】
 * 役割：アプリ全体の「骨組み」と「設定」をまとめる最重要ファイルです。
 * ルーティング（画面遷移）やデータ共有（Provider）の設定を行います。
 */

import { BrowserRouter, useRoutes } from "react-router-dom";
import { useState } from "react";
import { AuthProvider } from "./contexts/AuthContext";
import { AnalysisProvider } from "./contexts/AnalysisContext";
import { AppProvider } from "./contexts/AppContext";
import { routes } from "./routes"; // 画面遷移のルールを読み込み
import { LogoSplash } from "./components/ui/LogoSplash";

/** ── ルーティング（画面の切り替え）の実行 ── */
function AppRoutes() {
  return useRoutes(routes);
}

export default function App() {
  // アプリ起動時のアニメーション（スプラッシュ）を表示するかどうかの状態
  const [showSplash, setShowSplash] = useState(true);

  // アニメーションが終わったら非表示にする関数
  const handleSplashEnd = () => {
    setShowSplash(false);
  };

  return (
    /** BrowserRouter: URLによる画面切り替えを可能にします */
    <BrowserRouter>
      {/* ── 各種データ共有（Context）の囲い込み ── */}
      <AuthProvider>      {/* ログイン情報を共有 */}
        <AnalysisProvider> {/* 解析の状態を共有 */}
          <AppProvider>      {/* アプリ全体のデータを共有 */}
            
            {/* 起動時アニメーションの表示 */}
            {showSplash && <LogoSplash onAnimationEnd={handleSplashEnd} />}
            
            {/* 現在のURLに合わせた画面（ページ）の表示 */}
            <AppRoutes />

          </AppProvider>
        </AnalysisProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}