/**
 * 【FavoritesPage.tsx】
 * 役割：ユーザーがお気に入り登録した楽曲を一覧表示するページです。
 * 特徴：ログイン状態のチェック、データの読み込み待ち、0件時の表示などを細かく管理しています。
 */

import React, { useEffect, useState } from 'react';
import { FavoriteSong, toUserMessage } from '../api';
import { collectionApi } from '../api/collectionApi';
import { useFavoriteSongs } from '../hooks/useFavoriteSongs';
import { HeartIcon as HeartIconSolid } from '@heroicons/react/24/solid';
import { useToast } from '../hooks/useToast';
import ErrorBanner from '../components/ui/ErrorBanner';
import LoadingState from '../components/ui/LoadingState';
import PageStateContainer from '../components/ui/PageStateContainer';
import Toast from '../components/ui/Toast';
import AuthRequiredCard from '../components/ui/cards/AuthRequiredCard';

/** FavoritesPage が受け取るプロパティ */
interface FavoritesPageProps {
    /** ログイン中かどうか */
    isAuthenticated: boolean;
    /** ログインボタンが押された時の動き */
    onLoginClick: () => void;
}

const FavoritesPage: React.FC<FavoritesPageProps> = ({ isAuthenticated, onLoginClick }) => {
    
    // ── 状態管理 (State) ──
    const [favorites, setFavorites] = useState<FavoriteSong[]>([]); // お気に入り曲のリスト
    const [loading, setLoading] = useState(true);                   // 読み込み中フラグ
    // 削除処理中の曲ID管理はhookに統一
    const [error, setError] = useState<string | null>(null);        // エラーメッセージ（ErrorBanner用）
    const { toastMessage, hideToast } = useToast();

    /**
     * ── データの取得 (Effect) ──
     * ログインしている場合、サーバーからお気に入りリスト（最大500件）を取得します。
     */
    useEffect(() => {
        if (!isAuthenticated) {
            setLoading(false);
            return;
        }
        setLoading(true);
        setError(null);
        collectionApi.favoriteSong.get()
            .then(setFavorites)
            .catch(err => setError(toUserMessage(err, "お気に入りを取得できませんでした")))
            .finally(() => setLoading(false));
    }, [isAuthenticated]);

    // useFavoriteSongs hookでお気に入り削除・オプティミスティック更新を管理
    const { toggleFavoriteSong, isFavoriteSong, isToggling, isLoading: isCollLoading } = useFavoriteSongs(onLoginClick);

    // フィルタリング後のリスト（削除済みのものを除外）
    const visibleFavorites = favorites.filter(fav => isFavoriteSong(fav.song_id));

    /** ── 表示判定：未ログインの場合 ── */
    if (!isAuthenticated) {
        return (
            <AuthRequiredCard
                title="お気に入り"
                message="ログインするとお気に入りの楽曲を保存できます"
                icon={<HeartIconSolid className="w-12 h-12 text-rose-500/50" />}
                onLoginClick={onLoginClick}
            />
        );
    }

    /** ── 表示判定：読み込み中の場合 ── */
    if (loading || isCollLoading) {
        return (
            <PageStateContainer>
                <LoadingState className="text-slate-500" />
            </PageStateContainer>
        );
    }

    /** ── 表示判定：エラー発生時 ── */
    if (error) {
        return (
            <PageStateContainer>
                <ErrorBanner message={error} />
            </PageStateContainer>
        );
    }

    /** ── 表示判定：0件の場合 ── */
    if (visibleFavorites.length === 0) {
        return (
            <PageStateContainer>
                <div className="text-center">
                    <HeartIconSolid className="w-12 h-12 text-slate-700 mx-auto mb-4" />
                    <h2 className="text-xl font-bold text-white mb-2">お気に入りはまだありません</h2>
                    <p className="text-slate-400 text-sm">
                        楽曲一覧でハートをタップして追加しましょう
                    </p>
                </div>
            </PageStateContainer>
        );
    }

    /** ── 表示判定：お気に入り一覧のテーブル表示 ── */
    return (
        <div className="flex flex-col items-center min-h-[calc(100vh-80px)] bg-transparent p-4 sm:p-8">
            <h1 className="text-2xl sm:text-3xl font-bold text-white mb-2 drop-shadow-md">お気に入り</h1>
            <p className="text-sm text-slate-400 mb-6">{visibleFavorites.length}曲</p>

            <div className="table-container">
                <table className="w-full text-left">
                    <thead>
                        <tr className="table-header">
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
                        {visibleFavorites.map((fav, i) => (
                            <tr key={fav.favorite_id} className="table-row group">
                                <td className="py-3 px-5 text-slate-500 text-xs">{i + 1}</td>
                                <td className="py-3 px-4 text-slate-200 font-medium group-hover:text-white transition-colors">{fav.title}</td>
                                <td className="py-3 px-4 text-slate-400">{fav.artist || '-'}</td>
                                <td className="py-3 px-4 text-slate-400 whitespace-nowrap hidden sm:table-cell">{fav.lowest_note || '-'}</td>
                                <td className="py-3 px-4 text-slate-400 whitespace-nowrap hidden sm:table-cell">{fav.highest_note || '-'}</td>
                                <td className="py-3 px-4 text-slate-400 whitespace-nowrap hidden sm:table-cell">{fav.falsetto_note || '-'}</td>
                                <td className="py-3 px-2 text-center">
                                    {/* お気に入り解除ボタン（ハート） */}
                                    <button
                                        onClick={() => toggleFavoriteSong(fav.song_id)}
                                        disabled={isToggling(fav.song_id)}
                                        className="p-1 rounded-full hover:bg-white/10 transition-colors disabled:opacity-50"
                                    >
                                        <HeartIconSolid className="w-5 h-5 text-rose-500" />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Toast通知 */}
            {toastMessage && (
                <Toast message={toastMessage} onClose={hideToast} />
            )}
        </div>
    );
};

export default FavoritesPage;