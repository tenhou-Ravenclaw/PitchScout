/**
 * 【Header.tsx】
 * 役割：PCなどの大きな画面で、上部に固定表示されるナビゲーションヘッダーです。
 * 特徴：検索バー、各ページへのリンク、ログイン/ログアウトボタンを統合しています。
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
// 認証情報の管理やログアウト処理を取得
import { useAuth } from '../../contexts/AuthContext';
import logo from '../../assets/logo.png';

/** ヘッダーが受け取るプロパティの定義 */
interface HeaderProps {
    currentPath: string;           // 現在開いているページのURL
    searchQuery?: string;          // 検索ワード
    onSearchChange?: (query: string) => void; // 検索実行時の関数
    isAuthenticated?: boolean;     // ログインしているか
    userName?: string | null;      // 表示するユーザー名
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
    // 検索入力フィールドの値を内部状態で管理します
    const [inputValue, setInputValue] = useState(searchQuery);

    /** ── 同期 (Effect) ──
     * 外部からsearchQueryがリセットされた際などに、入力欄の中身を合わせます。
     */
    React.useEffect(() => {
        setInputValue(searchQuery);
    }, [searchQuery]);

    /** 指定したURLリストのいずれかに現在地が含まれているか判定します */
    const isActive = (paths: string[]) => paths.some(p => currentPath === p || currentPath.startsWith(p + "/"));

    /** ── デザイン判定 ──
     * アクティブなメニュー項目にだけ明るい色と光を付けます。
     */
    const navClass = (active: boolean) =>
        `${active ? 'text-cyan-400 font-bold drop-shadow-[0_0_5px_rgba(34,211,238,0.8)]' : 'hover:text-cyan-400 text-slate-400'} transition-all bg-transparent border-0 cursor-pointer`;

    return (
        /** hidden md:flex: スマホでは非表示、PCサイズで表示します */
        <header className="hidden md:flex items-center justify-between px-8 py-4 bg-slate-900/80 backdrop-blur-md border-b border-cyan-500/30 shadow-[0_0_15px_rgba(6,182,212,0.15)] sticky top-0 z-50">
            
            {/* ── 左端：ロゴエリア ── */}
            <div className="flex items-center gap-4 cursor-pointer group" onClick={() => navigate("/")}>
                <img src={logo} alt="App Logo" className="w-10 h-10 rounded-lg shadow-lg object-cover ring-2 ring-cyan-500/50 group-hover:ring-cyan-400 transition-all" />
                <h1 className="text-xl font-bold tracking-tight text-white group-hover:text-cyan-400 transition-colors drop-shadow-sm">PitchScout</h1>
            </div>

            {/* ── 中央：ナビゲーションメニュー ── */}
            <nav className="hidden md:flex gap-8 text-sm font-medium text-slate-400">
                <button type="button" onClick={() => navigate("/guide")} className={navClass(isActive(["/guide"]))}>
                    使い方ガイド
                </button>
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

            {/* ── 右端：検索・ユーザーエリア ── */}
            <div className="flex items-center gap-6">
                
                {/* 検索バー（大きな画面でのみ表示） */}
                <div className="relative hidden lg:block" role="search">
                    <input
                        type="text"
                        placeholder="サイト内楽曲検索"
                        aria-label="サイト内楽曲検索"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                                onSearchChange?.(inputValue); // Enterキーで検索を実行
                            }
                        }}
                        className="bg-slate-800/80 text-sm rounded-full px-5 py-2.5 pr-9 w-64 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:bg-slate-800 transition-all placeholder-slate-500 text-slate-200 border border-slate-700 hover:border-slate-600"
                    />
                    {/* クリアボタン：入力がある時だけ表示されます */}
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

                {/* ── ユーザープロフィール / ログイン ── */}
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
                        className="btn-primary-cyan rounded-full px-5 py-2 text-sm"
                    >
                        ログイン
                    </button>
                )}
            </div>
        </header>
    );
};

export default React.memo(Header);