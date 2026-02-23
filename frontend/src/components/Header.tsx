import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import logo from '../assets/logo.png';

interface HeaderProps {
    currentPath: string;
    searchQuery?: string;
    onSearchChange?: (query: string) => void;
    isAuthenticated?: boolean;
    userName?: string | null;
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
    const [inputValue, setInputValue] = useState(searchQuery);

    // 外部からsearchQueryが更新された時(クリアボタン等)、inputValueを同期
    React.useEffect(() => {
        setInputValue(searchQuery);
    }, [searchQuery]);

    const isActive = (paths: string[]) => paths.some(p => currentPath === p || currentPath.startsWith(p + "/"));

    const navClass = (active: boolean) =>
        `${active ? 'text-cyan-400 font-bold drop-shadow-[0_0_5px_rgba(34,211,238,0.8)]' : 'hover:text-cyan-400 text-slate-400'} transition-all bg-transparent border-0 cursor-pointer`;

    return (
        <header className="hidden md:flex items-center justify-between px-8 py-4 bg-slate-900/80 backdrop-blur-md border-b border-cyan-500/30 shadow-[0_0_15px_rgba(6,182,212,0.15)] sticky top-0 z-50">
            <div className="flex items-center gap-4 cursor-pointer group" onClick={() => navigate("/")}>
                <img src={logo} alt="App Logo" className="w-10 h-10 rounded-lg shadow-lg object-cover ring-2 ring-cyan-500/50 group-hover:ring-cyan-400 transition-all" />
                <h1 className="text-xl font-bold tracking-tight text-white group-hover:text-cyan-400 transition-colors drop-shadow-sm">PitchScout</h1>
            </div>

            {/* Navigation */}
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

            <div className="flex items-center gap-6">
                {/* Search Bar */}
                <div className="relative hidden lg:block" role="search">
                    <input
                        type="text"
                        placeholder="サイト内楽曲検索"
                        aria-label="サイト内楽曲検索"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                                onSearchChange?.(inputValue);
                            }
                        }}
                        className="bg-slate-800/80 text-sm rounded-full px-5 py-2.5 pr-9 w-64 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:bg-slate-800 transition-all placeholder-slate-500 text-slate-200 border border-slate-700 hover:border-slate-600"
                    />
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

                {/* User Profile / Login */}
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

export default React.memo(Header);
