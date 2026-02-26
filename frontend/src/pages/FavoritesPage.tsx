/**
 * 【FavoritesPage.tsx】
 * 役割：ユーザーがお気に入り登録した楽曲を一覧表示するページです。
 * 特徴：ログイン状態のチェック、データの読み込み待ち、0件時の表示などを細かく管理しています。
 */

import React, { useState } from 'react';
import { getFavorites, FavoriteSong, toUserMessage } from '../api';
import { HeartIcon as HeartIconSolid } from '@heroicons/react/24/solid';
import { useErrorToastNotifier } from '../hooks/useErrorToastNotifier';
import { useFavoriteDelete } from '../hooks/useFavoriteDelete';
import { useAuthenticatedDataLoader } from '../hooks/useAuthenticatedDataLoader';
import { FAVORITES_AUTH_REQUIRED_CONTENT } from '../constants/userFeatureConstants';
import FavoriteSongsTable from '../components/features/FavoriteSongsTable';
import EmptyState from '../components/ui/EmptyState';
import DataStateSwitch from '../components/ui/DataStateSwitch';
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
    const [removingIds, setRemovingIds] = useState<Set<number>>(new Set()); // 削除処理中の曲IDを管理
    const [error, setError] = useState<string | null>(null);        // エラーメッセージ（ErrorBanner用）
    const { toastMessage, hideToast, notifyError } = useErrorToastNotifier();
    const { handleRemove } = useFavoriteDelete({
        favorites,
        removingIds,
        setFavorites,
        setRemovingIds,
        notifyError,
    });

    useAuthenticatedDataLoader<FavoriteSong[]>({
        isAuthenticated,
        fetchData: () => getFavorites(500),
        onSuccess: setFavorites,
        onError: (err: unknown) => {
            setError(toUserMessage(err, "お気に入りを取得できませんでした"));
        },
        setLoading,
        onStart: () => {
            setError(null);
        },
    });

    /** ── 表示判定：未ログインの場合 ── */
    if (!isAuthenticated) {
        return (
            <AuthRequiredCard
                title={FAVORITES_AUTH_REQUIRED_CONTENT.title}
                message={FAVORITES_AUTH_REQUIRED_CONTENT.message}
                icon={FAVORITES_AUTH_REQUIRED_CONTENT.icon}
                onLoginClick={onLoginClick}
            />
        );
    }

    return (
        <DataStateSwitch
            loading={loading}
            error={error}
            isEmpty={favorites.length === 0}
            loadingClassName="text-slate-500"
            emptyContent={(
                <EmptyState
                    title="お気に入りはまだありません"
                    message="楽曲一覧でハートをタップして追加しましょう"
                    icon={<HeartIconSolid className="w-12 h-12 text-slate-700 mx-auto mb-4" />}
                />
            )}
        >
            <div className="flex flex-col items-center min-h-[calc(100vh-80px)] bg-transparent p-4 sm:p-8">
                <h1 className="text-2xl sm:text-3xl font-bold text-white mb-2 drop-shadow-md">お気に入り</h1>
                <p className="text-sm text-slate-400 mb-6">{favorites.length}曲</p>

                <FavoriteSongsTable
                    favorites={favorites}
                    removingIds={removingIds}
                    onRemove={handleRemove}
                />

                {/* Toast通知 */}
                {toastMessage && (
                    <Toast message={toastMessage} onClose={hideToast} />
                )}
            </div>
        </DataStateSwitch>
    );
};

export default FavoritesPage;