import { useState, useCallback } from "react";
import { getFavoriteArtists, addFavoriteArtist, removeFavoriteArtist } from "../api";
import { useAuth } from "../contexts/AuthContext";
import { useErrorToastNotifier } from "./useErrorToastNotifier";
import { useAuthActionGuard } from "./useAuthActionGuard";
import { useSyncedFavoriteIds } from "./useSyncedFavoriteIds";
import { toggleInSet } from "../utils/setUtils";
import {
  createFavoriteMutationErrorConfig,
  executeFavoriteMutation,
} from "../utils/favoriteMutation";
import {
  FAVORITE_ARTIST_MESSAGES,
  FAVORITE_LOGIN_REQUIRED_MESSAGE,
} from "../constants/userFeatureConstants";

/** useFavoriteArtists の返り値型です。 */
interface UseFavoriteArtistsResult {
  /** お気に入り追加/削除を切り替えます。 */
  toggleFavorite: (artistId: number, artistName: string) => Promise<void>;
  /** 指定アーティストがお気に入りか判定します。 */
  isFavorite: (artistId: number) => boolean;
}

/**
 * **useFavoriteArtists カスタムフック**
 * 
 * お気に入りアーティストの管理を共通化するカスタムフックです。
 * 複数のコンポーネントで重複していたお気に入りアーティストの状態管理と
 * API通信ロジックを一元管理します。
 * 
 * @returns {{
 *   toggleFavorite: (artistId: number, artistName: string) => Promise<void>,  // お気に入り追加/削除の切り替え
 *   isFavorite: (artistId: number) => boolean  // 指定アーティストがお気に入りか判定
 * }}
 * 
 * @example
 * ```tsx
 * const { toggleFavorite, isFavorite } = useFavoriteArtists();
 * 
 * // お気に入り状態の確認
 * const isArtistFavorite = isFavorite(123);
 * 
 * // お気に入りの追加/削除
 * await toggleFavorite(123, "アーティスト名");
 * 
 * // お気に入りアイコンの表示制御
 * {isFavorite(artist.id) ? <StarSolid /> : <StarOutline />}
 * ```
 */
export const useFavoriteArtists = (): UseFavoriteArtistsResult => {
  const [favoriteIdSet, setFavoriteIdSet] = useState<Set<number>>(new Set());
  const { showToast, notifyError } = useErrorToastNotifier();
  const { isAuthenticated } = useAuth();
  const { guardAction } = useAuthActionGuard({
    isAuthenticated,
    onUnauthorized: () => {
      showToast(FAVORITE_LOGIN_REQUIRED_MESSAGE);
    },
  });

  useSyncedFavoriteIds({
    isAuthenticated,
    setIdSet: setFavoriteIdSet,
    fetchItems: getFavoriteArtists,
    selectId: (favorite) => favorite.artist_id,
    notifyError,
    syncErrorLabel: FAVORITE_ARTIST_MESSAGES.syncErrorLabel,
    syncErrorUserMessage: FAVORITE_ARTIST_MESSAGES.syncErrorUserMessage,
  });

  /**
   * ── お気に入りの追加/削除を切り替え ──
   * 
   * 既にお気に入りに登録済みの場合は削除し、未登録の場合は追加します。
   * サーバーへのAPI通信完了後、ローカルの状態も自動的に更新されます。
   * 
   * @param artistId - アーティストID
   * @param artistName - アーティスト名（追加時にサーバーに送信）
  * @note API通信エラー時はToastでエラーメッセージを表示し、処理を終了します
   */
  const toggleFavorite = useCallback(async (artistId: number, artistName: string) => {
    await guardAction(async () => {
      const wasFavorite = favoriteIdSet.has(artistId);
      await executeFavoriteMutation({
        isFavorite: wasFavorite,
        onAdd: () => addFavoriteArtist(artistId, artistName),
        onRemove: () => removeFavoriteArtist(artistId),
        onSuccess: () => {
          setFavoriteIdSet((prev) => toggleInSet(prev, artistId));
        },
        errorConfig: createFavoriteMutationErrorConfig(notifyError, {
          errorLabel: FAVORITE_ARTIST_MESSAGES.toggleErrorLabel,
          errorUserMessage: FAVORITE_ARTIST_MESSAGES.toggleErrorUserMessage,
        }),
      });
    });
  }, [favoriteIdSet, guardAction, notifyError]);

  /**
   * ── 指定アーティストがお気に入りか判定 ──
   * 
   * @param artistId - 判定対象のアーティストID
   * @returns true: お気に入り登録済み / false: 未登録
   */
  const isFavorite = useCallback((artistId: number) => {
    return favoriteIdSet.has(artistId);
  }, [favoriteIdSet]);

  return {
    toggleFavorite,
    isFavorite,
  };
};
