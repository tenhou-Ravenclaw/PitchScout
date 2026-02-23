/**
 * 【Layout.tsx】
 * 役割：アプリ全体の「骨組み」です。
 * ヘッダー、フッター、背景、トップに戻るボタンなど、全画面で共通して出したいものを管理します。
 * 💡 設計図（FRONTEND_STRUCTURE.md）に基づく移動案：
 * 1. 移動先: src/components/layouts/Layout.tsx
 */

import React, { Suspense, useEffect, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { ChevronUpIcon } from "@heroicons/react/24/solid";
// 共通の部品をインポート
import Header from "./Header";
import BottomNav from "./BottomNav";
import { useAppContext } from "../contexts/AppContext";
import { useAuth } from "../contexts/AuthContext";

/**
 * ── 読み込み中の表示 (Loading Fallback) ──
 * 画面（ページ）の読み込みが遅れている時に一時的に出す表示です。
 */
const LoadingFallback: React.FC = () => (
  <div className="flex items-center justify-center min-h-[60vh]">
    <div className="text-slate-500 text-lg animate-pulse">Loading...</div>
  </div>
);

const Layout: React.FC = () => {
  // アプリ全体の共有状態（検索ワードなど）を取得
  const { searchQuery, setSearchQuery } = useAppContext();
  // ユーザーの認証状態を取得
  const { user, isAuthenticated } = useAuth();
  
  const navigate = useNavigate();
  const location = useLocation(); // 現在どのURLにいるかを取得

  // ── トップに戻るボタンの制御 ──
  const [showScrollTop, setShowScrollTop] = useState(false);

  useEffect(() => {
    // 300px以上スクロールしたらボタンを出す
    const onScroll = () => setShowScrollTop(window.scrollY > 300);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  /**
   * ── 検索実行時の処理 ──
   * ヘッダーの検索バーに入力があった時、自動で「楽曲一覧（/songs）」へ移動します。
   */
  const handleSearch = (query: string) => {
    setSearchQuery(query);
    if (query && location.pathname !== "/songs") {
      navigate("/songs");
    }
  };

  return (
    <div className="pb-24 md:pb-0 min-h-[100dvh] relative bg-slate-900 overflow-hidden font-sans selection:bg-pink-500 selection:text-white text-slate-200">
      
      {/* ── 全画面共通の背景演出 (Global Background) ──
          どの画面にいても、後ろ側にサイバーな光の線や円を表示し続けます。
      */}
      <div className="fixed inset-0 z-0 opacity-20 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[120%] h-[40%] bg-gradient-to-r from-red-600 to-transparent -skew-y-3 transform" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[120%] h-[40%] bg-gradient-to-l from-cyan-600 to-transparent skew-y-3 transform" />
        <div className="absolute top-[20%] right-[-20%] w-[800px] h-[800px] border-[50px] border-white/5 rounded-full" />
      </div>

      <div className="relative z-10">
        {/* ── 共通ヘッダー ── */}
        <Header
          currentPath={location.pathname}
          searchQuery={searchQuery}
          onSearchChange={handleSearch}
          isAuthenticated={isAuthenticated}
          // ユーザー名があれば表示、なければメールアドレスなどを出す
          userName={user?.user_metadata?.full_name || user?.email || null}
        />

        {/* ── メインコンテンツの差し込み口 (Outlet) ──
            ここで routes.tsx で定義した各ページ（Home, SongList など）が入れ替わりで表示されます。
            Suspense を使うことで、ページの読み込み待ちを処理します。
        */}
        <Suspense fallback={<LoadingFallback />}>
          <Outlet />
        </Suspense>

        {/* ── トップに戻るボタン (Scroll Top) ── */}
        {showScrollTop && (
          <button
            onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
            className="fixed bottom-20 right-4 md:bottom-8 z-50 w-10 h-10
              bg-slate-900/80 backdrop-blur border border-cyan-500/40 rounded-full
              flex items-center justify-center text-cyan-400
              shadow-[0_0_12px_rgba(34,211,238,0.4)]
              active:scale-90 transition-all"
            aria-label="ページ先頭に戻る"
          >
            <ChevronUpIcon className="w-5 h-5" />
          </button>
        )}

        {/* ── モバイル用：共通ボトムナビ ── */}
        <BottomNav
          currentPath={location.pathname}
          isAuthenticated={isAuthenticated}
        />
      </div>
    </div>
  );
};

export default Layout;