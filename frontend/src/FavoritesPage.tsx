/**
 * 【FavoritesPage.tsx】
 * 役割：ユーザーがお気に入り登録した曲を一覧表示し、解除（削除）操作を行う画面です。
 * 💡 設計図（FRONTEND_STRUCTURE.md）に基づく移動案：
 * 1. 移動先: src/features/songs/pages/FavoritesPage.tsx
 * 2. 改善点：楽曲を表示するテーブル部分を「SongTable.tsx」として共通化すると、
 * 楽曲一覧画面（SongListPage）と同じ見た目を保ちつつ、コードを短くできます。
 */

import React, { useEffect, useState, useCallback } from 'react';
// API通信用の関数や型をインポート
import { getFavorites, removeFavorite, FavoriteSong, UserRange } from './api';
import { HeartIcon as HeartIconSolid } from '@heroicons/react/24/solid';
import { useAuth } from './contexts/AuthContext';

/** * 画面が受け取るデータ（Props）の定義
 */
interface FavoritesPageProps {
    userRange?: UserRange | null; // キーおすすめ用のユーザー音域
    onLoginClick?: () => void;    // ログインを促すための関数
}

const FavoritesPage: React.FC<FavoritesPageProps> = ({ onLoginClick }) => {
    const { isAuthenticated } = useAuth();
    
    // ── 状態管理 (State) ──
    const [favorites, setFavorites] = useState<FavoriteSong[]>([]); // お気に入り曲のリスト本体
    const [loading, setLoading] = useState(true); // 読み込み中フラグ
    // 現在削除処理中の曲IDを管理（二重クリック防止用）
    const [removingIds, setRemovingIds] = useState<Set<number>>(new Set());

    /**
     * 画面を開いた時にお気に入りデータを取得
     */
    useEffect(() => {
        // ログインしていなければ処理しない
        if (!isAuthenticated) {
            setLoading(false);
            return;
        }
        setLoading(true);
        // 最大500件まで取得を試みる
        getFavorites(500)
            .then(setFavorites)
            .catch(err => console.error("お気に入り取得失敗:", err))
            .finally(() => setLoading(false));
    }, [isAuthenticated]);

    /**
     * お気に入り解除（削除）の処理
     * 💡 「オプティミスティック更新」を行っています。
     */
    const handleRemove = useCallback(async (songId: number) => {
        // すでに削除処理中なら何もしない
        if (removingIds.has(songId)) return;

        // 削除前のリストを一時保存（失敗した時のバックアップ）
        const removed = favorites.find(f => f.song_id === songId);
        
        // ── オプティミスティック更新 ──
        // サーバーからの返事を待たずに、まず画面上のリストから消す
        setFavorites(prev => prev.filter(f => f.song_id !== songId));
        // 処理中フラグを立てる
        setRemovingIds(prev => new Set(prev).add(songId));

        try {
            // サーバーに削除を依頼
            await removeFavorite(songId);
        } catch (err) {
            console.error("お気に入り削除失敗:", err);
            // 💡 失敗した場合は、バックアップからリストを元に戻す
            if (removed) {
                setFavorites(prev => [...prev, removed].sort((a, b) => a.title.localeCompare(b.title, "ja")));
            }
        } finally {
            // 処理中フラグを下ろす
            setRemovingIds(prev => {
                const next = new Set(prev);
                next.delete(songId);
                return next;
            });
        }
    }, [favorites, removingIds]);

    // ── 条件付きレンダリング：未ログイン ──
    if (!isAuthenticated) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[calc(100vh-80px)] bg-transparent p-8">
                <div className="w-full max-w-sm bg-slate-900/60 backdrop-blur-md rounded-2xl shadow-xl border border-white/10 p-8 text-center">
                    <HeartIconSolid className="w-12 h-12 text-rose-500/50 mx-auto mb-4" />
                    <h2 className="text-xl font-bold text-white mb-2">お気に入り</h2>
                    <p className="text-slate-400 text-sm mb-6">ログインするとお気に入りの楽曲を保存できます</p>
                    <button
                        onClick={onLoginClick}
                        className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-medium rounded-xl px-6 py-3 text-sm transition-colors shadow-lg shadow-cyan-500/20"
                    >
                        ログインする
                    </button>
                </div>
            </div>
        );
    }

    // ── 条件付きレンダリング：読み込み中 ──
    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[calc(100vh-80px)] bg-transparent p-8">
                <p className="text-slate-500">読み込み中...</p>
            </div>
        );
    }

    // ── 条件付きレンダリング：データ0件 ──
    if (favorites.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[calc(100vh-80px)] bg-transparent p-8">
                <div className="text-center">
                    <HeartIconSolid className="w-12 h-12 text-slate-700 mx-auto mb-4" />
                    <h2 className="text-xl font-bold text-white mb-2">お気に入りはまだありません</h2>
                    <p className="text-slate-400 text-sm">楽曲一覧でハートをタップして追加しましょう</p>
                </div>
            </div>
        );
    }

    // ── メイン表示：お気に入りテーブル ──
    return (
        <div className="flex flex-col items-center min-h-[calc(100vh-80px)] bg-transparent p-4 sm:p-8">
            <h1 className="text-2xl sm:text-3xl font-bold text-white mb-2 drop-shadow-md">お気に入り</h1>
            <p className="text-sm text-slate-400 mb-6">{favorites.length}曲</p>

            <div className="w-full max-w-5xl bg-slate-900/60 backdrop-blur-md shadow-xl rounded-xl overflow-hidden border border-white/10">
                <table className="w-full text-left">
                    <thead>
                        <tr className="bg-slate-800/50 text-xs text-slate-400 uppercase border-b border-white/5">
                            <th className="py-3 px-5 font-medium">#</th>
                            <th className="py-3 px-4 font-medium">Title</th>
                            <th className="py-3 px-4 font-medium">Artist</th>
                            <th className="py-3 px-4 font-medium hidden sm:table-cell">Lowest</th>
                            <th className="py-3 px-4 font-medium hidden sm:table-cell">Highest</th>
                            <th className="py-3 px-4 font-medium hidden sm:table-cell">Falsetto</th>
                            <th className="py-3 px-2 font-medium w-10"></th>
                        </tr>
                    </thead>
                    <tbody>
                        {favorites.map((fav, i) => (
                            <tr key={fav.favorite_id} className="border-b border-white/5 hover:bg-white/5 transition-colors text-sm group">
                                <td className="py-3 px-5 text-slate-500 text-xs">{i + 1}</td>
                                <td className="py-3 px-4 text-slate-200 font-medium group-hover:text-white transition-colors">{fav.title}</td>
                                <td className="py-3 px-4 text-slate-400">{fav.artist || '-'}</td>
                                <td className="py-3 px-4 text-slate-400 whitespace-nowrap hidden sm:table-cell">{fav.lowest_note || '-'}</td>
                                <td className="py-3 px-4 text-slate-400 whitespace-nowrap hidden sm:table-cell">{fav.highest_note || '-'}</td>
                                <td className="py-3 px-4 text-slate-400 whitespace-nowrap hidden sm:table-cell">{fav.falsetto_note || '-'}</td>
                                <td className="py-3 px-2 text-center">
                                    <button
                                        onClick={() => handleRemove(fav.song_id)}
                                        disabled={removingIds.has(fav.song_id)}
                                        className="p-1 rounded-full hover:bg-white/10 transition-colors disabled:opacity-50"
                                    >
                                        {/* お気に入り中なので、常に塗られたハートを表示 */}
                                        <HeartIconSolid className="w-5 h-5 text-rose-500" />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default FavoritesPage;