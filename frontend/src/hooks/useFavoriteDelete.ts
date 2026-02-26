import { Dispatch, SetStateAction, useCallback } from "react";
import { FavoriteSong, removeFavorite } from "../api";
import { FAVORITE_SONG_MESSAGES } from "../constants/favoriteMessages";
import { ErrorNotifier } from "./useErrorNotifier";
import { executeDeleteAction } from "../utils/deleteAction";
import { addToSet, removeFromSet } from "../utils/setUtils";

/** お気に入り削除フックの設定 */
interface UseFavoriteDeleteParams {
  /** 現在のお気に入り一覧 */
  favorites: FavoriteSong[];
  /** 現在削除処理中のID集合 */
  removingIds: Set<number>;
  /** お気に入り一覧の更新関数 */
  setFavorites: Dispatch<SetStateAction<FavoriteSong[]>>;
  /** 削除処理中ID集合の更新関数 */
  setRemovingIds: Dispatch<SetStateAction<Set<number>>>;
  /** エラー通知関数 */
  notifyError: ErrorNotifier;
}

/**
 * お気に入り楽曲の削除処理（楽観更新 + ロールバック）を提供するフックです。
 *
 * @param params - 削除処理に必要な設定
 * @returns {{ handleRemove: (songId: number) => Promise<void> }}
 */
export const useFavoriteDelete = ({
  favorites,
  removingIds,
  setFavorites,
  setRemovingIds,
  notifyError,
}: UseFavoriteDeleteParams): {
  handleRemove: (songId: number) => Promise<void>;
} => {
  /**
   * 指定楽曲をお気に入りから削除します。
   *
   * @param songId - 削除対象の楽曲ID
   */
  const handleRemove = useCallback(async (songId: number): Promise<void> => {
    if (removingIds.has(songId)) {
      return;
    }

    const removed = favorites.find((favorite) => favorite.song_id === songId);

    await executeDeleteAction<number>({
      targetId: songId,
      runDelete: removeFavorite,
      onBefore: () => {
        setFavorites((prev) => prev.filter((favorite) => favorite.song_id !== songId));
        setRemovingIds((prev) => addToSet(prev, songId));
      },
      onError: (error: unknown) => {
        notifyError(
          FAVORITE_SONG_MESSAGES.deleteErrorLabel,
          error,
          FAVORITE_SONG_MESSAGES.deleteErrorUserMessage,
        );

        if (removed) {
          setFavorites((prev) => [...prev, removed].sort((left, right) => left.title.localeCompare(right.title, "ja")));
        }
      },
      onFinally: () => {
        setRemovingIds((prev) => removeFromSet(prev, songId));
      },
    });
  }, [favorites, notifyError, removingIds, setFavorites, setRemovingIds]);

  return {
    handleRemove,
  };
};
