/**
 * 【LoginPage.tsx】
 * 役割：Google認証を使ってアプリにログインするための入り口となる画面です。
 * 💡 このファイル自体には「ログインの仕組み」は書かれておらず、
 * AuthContext にある機能を呼び出すことで実際の処理（Googleの窓を開くなど）を行います。
 */

import React from "react";
// 認証機能（ログイン処理など）を管理するカスタムフックを読み込みます
import { useAuth } from "./contexts/AuthContext";

const LoginPage: React.FC = () => {
  /**
   * ── 認証機能の取り出し ──
   * useAuth() を通じて、Googleログインを実行するための関数（loginWithGoogle）を借ります。
   */
  const { loginWithGoogle } = useAuth();

  return (
    /**
     * ── レイアウト構成 ──
     * flex-col と items-center を使って、ログインカードを画面の真ん中に配置しています。
     */
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-80px)] bg-transparent p-8">
      
      {/* ログインカードの枠組み（半透明のサイバーなデザイン） */}
      <div className="w-full max-w-sm bg-slate-900/60 backdrop-blur-md rounded-2xl shadow-xl border border-white/10 p-8 text-center">
        
        {/* アプリ名と説明 */}
        <h1 className="text-2xl font-bold text-white mb-2">
          
        </h1>
        <p className="text-slate-400 text-sm mb-8">
          ログインして声域分析の履歴やお気に入りを保存しよう
        </p>

        {/* ── Googleログインボタン ──
           💡 ボタンをクリックすると、AuthContext 内の loginWithGoogle が実行されます。
        */}
        <button
          onClick={loginWithGoogle}
          className="w-full flex items-center justify-center gap-3 bg-slate-800 border-2 border-slate-700 rounded-xl px-6 py-3 text-sm font-medium text-slate-200 hover:bg-slate-700 hover:border-slate-600 transition-all"
        >
          {/* Googleのロゴ（SVG形式） */}
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
              fill="#4285F4"
            />
            <path
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              fill="#34A853"
            />
            <path
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              fill="#FBBC05"
            />
            <path
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              fill="#EA4335"
            />
          </svg>
          Google でログイン
        </button>

        {/* 補足メッセージ */}
        <p className="text-xs text-slate-400 mt-6">
          ログインなしでも録音・分析・楽曲検索は利用できます
        </p>
      </div>
    </div>
  );
};

/**
 * 💡 React.memo で囲むことで、ログイン画面の不要な再描画を防ぎ、
 * 表示を軽く保つように工夫されています。
 */
export default React.memo(LoginPage);