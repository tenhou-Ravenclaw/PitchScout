/**
 * 【Layout.tsx】
 * 役割：アプリ全体の共通パーツ（ヘッダー、ナビ、背景）をまとめて管理する、外枠のコンポーネントです。
 * 特徴：画面遷移による中身（Outlet）の切り替えや、グローバル検索の処理を担当します。
 */

import React, { Suspense } from "react";
// ── ルーター関連のフックをインポート ──
import { Outlet, useLocation, useNavigate } from "react-router-dom";
// 各種共通部品を読み込み
import Header from "./Header";
import BottomNav from "./BottomNav";
import { useAppContext } from "../../contexts/AppContext";
import { useAuth } from "../../contexts/AuthContext";

/** ── ロード待ちの表示 (Fallback) ──
 * lazy で読み込んでいるページが表示されるまでの間、画面中央に出るアニメーションです。
 */
const LoadingFallback: React.FC = () => (
  <div className="flex items-center justify-center min-h-[60vh]">
    <div className="text-slate-500 text-lg animate-pulse">Loading...</div>
  </div>
);

const Layout: React.FC = () => {
  // ── グローバルなデータと機能の取得 ──
  const { searchQuery, setSearchQuery } = useAppContext();
  const { user, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const showHeader = true;
  const showGlobalBackground = location.pathname !== "/";

  /** ── 検索実行時の処理 ──
   * ヘッダーの検索窓で Enter を押した際、検索ワードをセットして検索ページへ移動させます。
   *
   * `/songs?q=...` の URL パラメータに検索クエリを乗せることで、
   * マウント時に確実にクエリを取得できる（React state の更新タイミングに依存しない）。
   * すでに /songs にいる場合は replace で履歴スタックを汚さない。
   */
  const handleSearch = (query: string) => {
    setSearchQuery(query);
    if (query) {
      // クエリあり: /songs?q=... へ遷移（すでに /songs なら replace で履歴を汚さない）
      navigate(`/songs?q=${encodeURIComponent(query)}`, {
        replace: location.pathname === "/songs",
      });
    } else if (location.pathname === "/songs") {
      // /songs 上でクリアした場合は URL パラメータを除去してアーティスト一覧へ
      navigate("/songs", { replace: true });
    }
    // 他ページでクリアした場合は遷移しない（context リセットのみ）
  };

  return (
    /** pb-24: スマホ版ナビバーが画面下部に重ならないように余白を作っています */
    <div className="pb-24 md:pb-0 min-h-[100dvh] relative bg-slate-900 overflow-hidden font-sans selection:bg-pink-500 selection:text-white text-slate-200">
      
      {/* ── 全画面共通の背景グラデーション装飾 ── */}
      {showGlobalBackground && (
        <div className="fixed inset-0 z-0 opacity-20 pointer-events-none">
          <div className="absolute top-[-10%] left-[-10%] w-[120%] h-[40%] bg-gradient-to-r from-red-600 to-transparent -skew-y-3 transform" />
          <div className="absolute bottom-[-10%] right-[-10%] w-[120%] h-[40%] bg-gradient-to-l from-cyan-600 to-transparent skew-y-3 transform" />
          <div className="absolute top-[20%] right-[-20%] w-[800px] h-[800px] border-[50px] border-white/5 rounded-full" />
        </div>
      )}

      <div className="relative z-10">
        {/* ── 共通ヘッダー (PC用) ── */}
        {showHeader && (
          <Header
            currentPath={location.pathname}
            searchQuery={searchQuery}
            onSearchChange={handleSearch}
            isAuthenticated={isAuthenticated}
            // ユーザー名がなければメールアドレスを表示するようにしています
            userName={user?.user_metadata?.full_name || user?.email || null}
          />
        )}

        {/* ── メインコンテンツ ──
           💡 URLに応じて Outlet の部分に各ページの内容が流し込まれます。
           isLoading 中はセッション確認が終わっていないため、ページを描画しない。
           これにより、再ログイン時に以前のページが一瞬映るフラッシュを防ぐ。
        */}
        <Suspense fallback={<LoadingFallback />}>
          {isLoading ? <LoadingFallback /> : <Outlet />}
        </Suspense>

        {/* ── 共通ボトムナビ (スマホ用) ── */}
        <BottomNav
          currentPath={location.pathname}
          isAuthenticated={isAuthenticated}
        />
      </div>
    </div>
  );
};

export default Layout;