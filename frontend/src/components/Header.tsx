/**
 * 【Header.tsx】
 * 役割：PC（デスクトップ）表示時の画面上部に表示されるナビゲーションバーです。
 * ロゴ、ページリンク、検索バー、ログイン/ログアウトボタンをまとめて管理します。
 * 💡 設計図（FRONTEND_STRUCTURE.md）に基づく移動案：
 * 1. 移動先: src/components/navigations/Header.tsx
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
// 認証状態の確認とログアウト機能を使用
import { useAuth } from '../contexts/AuthContext';
import logo from '../assets/logo.png';

/** * プロパティの定義 (Props)
 */
interface HeaderProps {
    currentPath: string;           // 現在どのページにいるか（URL）
    searchQuery?: string;          // 検索窓に入力されている文字
    onSearchChange?: (query: string) => void; // 検索を実行した時の関数
    isAuthenticated?: boolean;     // ログイン中かどうか
    userName?: string | null;      // ユーザーの名前（表示用）
}

const Header: React.FC<HeaderProps> = ({
    currentPath,
    searchQuery = "",
    onSearchChange,
    isAuthenticated = false,
    userName = null,
}) => {
    const navigate = useNavigate();
    const { logout } = useAuth();
    // 入力中の検索ワードを保持するローカルな状態
    const [inputValue, setInputValue] = useState(searchQuery);

    /**
     * 外部（クリアボタン等）から searchQuery が更新された場合、
     * 入力欄の表示を同期させます。
     */
    React.useEffect(() => {
        setInputValue(searchQuery);
    }, [searchQuery]);

    /**
     * 現在表示中のページがナビのリンク先と一致するか判定します。
     */
    const isActive = (paths: string[]) => paths.some(p => currentPath === p || currentPath.startsWith(p + "/"));

    /**
     * ナビゲーションリンクのスタイルを動的に変更します。
     * 現在のページなら青く光らせ、そうでなければグレーにします。
     */
    const navClass = (active: boolean) =>
        `${active ? 'text-cyan-400 font-bold drop-shadow-[0_0_5px_rgba(34,211,238,0.8)]' : 'hover:text-cyan-400 text-slate-400'} transition-all bg-transparent border-0 cursor-pointer`;

    return (
        /**
         * hidden md:flex により、スマホサイズでは非表示、
         * タブレット以上のサイズ（md）で表示されます。
         */
        <header className="hidden md:flex items-center justify-between px-8 py-4 bg-slate-900/80 backdrop-blur-md border-b border-cyan-500/30 shadow-[0_0_15px_rgba(6,182,212,0.15)] sticky top-0 z-50">
            
            {/* ── ロゴエリア ── */}
            <div className="flex items-center gap-4 cursor-pointer group" onClick={() => navigate("/")}>
                <img src={logo} alt="App Logo" className="w-10 h-10 rounded-lg shadow-lg object-cover ring-2 ring-cyan-500/50 group-hover:ring-cyan-400 transition-all" />
                <h1 className="text-2xl font-black italic text-white drop-shadow-[0_0_8px_rgba(255,255,255,0.2)] group-hover:drop-shadow-[0_0_12px_rgba(255,255,255,0.5)] group-hover:text-cyan-400 tracking-wider transition-all">
                    PitchScout
                </h1>
            </div>

            {/* ── ナビゲーションメニュー ── */}
            <nav className="hidden md:flex gap-8 text-sm font-medium text-slate-400">
                <button type="button" onClick={() => navigate("/guide")} className={navClass(isActive(["/guide"]))}>
                    使い方ガイド
                </button>
                {/* 録音に関連する複数のパスをまとめて「録音」として扱っています */}
                <button type="button" onClick={() => navigate("/menu")} className={navClass(isActive(["/menu", "/record", "/karaoke", "/upload"]))}>
                    録音
                </button>
                <button type="button" onClick={() => navigate("/analysis")} className={navClass(isActive(["/analysis", "/result"]))}>
                    声域分析
                </button>
                <button type="button" onClick={() => navigate("/songs")} className={navClass(isActive(["/songs"]))}>
                    アーティスト一覧
                </button>
                <button type="button" onClick={() => navigate("/favorites")} className={navClass(isActive(["/favorites"]))}>
                    お気に入り
                </button>
                <button type="button" onClick={() => navigate("/history")} className={navClass(isActive(["/history"]))}>
                    履歴
                </button>
            </nav>

            <div className="flex items-center gap-6">
                {/* ── 楽曲検索バー ── */}
                <div className="relative hidden lg:block" role="search">
                    <input
                        type="text"
                        placeholder="サイト内楽曲検索"
                        aria-label="サイト内楽曲検索"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        // エンターキーが押された時に検索を実行
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                                onSearchChange?.(inputValue);
                            }
                        }}
                        className="bg-slate-800/80 text-sm rounded-full px-5 py-2.5 pr-9 w-64 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:bg-slate-800 transition-all placeholder-slate-500 text-slate-200 border border-slate-700 hover:border-slate-600"
                    />
                    {/* 文字が入っている時だけ「✕」ボタンを表示 */}
                    {inputValue && (
                        <button
                            type="button"
                            onClick={() => {
                                setInputValue("");
                                onSearchChange?.("");
                            }}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 bg-transparent border-0 cursor-pointer p-0 leading-none"
                            aria-label="検索をクリア"
                        >
                            ✕
                        </button>
                    )}
                </div>

                {/* ── ユーザー設定（ログイン/ログアウト） ── */}
                {isAuthenticated ? (
                    <div className="flex items-center gap-3">
                        <span className="text-sm font-medium hidden sm:block text-slate-300">
                            {userName || "ユーザー"}
                        </span>
                        <button
                            type="button"
                            onClick={logout}
                            className="text-xs text-slate-400 hover:text-rose-400 transition-colors bg-transparent border-0 cursor-pointer"
                        >
                            ログアウト
                        </button>
                    </div>
                ) : (
                    <button
                        type="button"
                        onClick={() => navigate("/login")}
                        className="text-sm font-medium text-white bg-cyan-600 hover:bg-cyan-500 rounded-full px-5 py-2 transition-colors border-0 cursor-pointer shadow-lg shadow-cyan-500/20"
                    >
                        ログイン
                    </button>
                )}
            </div>
        </header>
    );
};

// 無駄な再描画を防いでパフォーマンスを最適化
export default React.memo(Header);