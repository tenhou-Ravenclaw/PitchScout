import { useState, useCallback } from "react";
import { getFavorites, addFavorite, removeFavorite } from "../api";
import { useAuth } from "../contexts/AuthContext";
import { useErrorToastNotifier } from "./useErrorToastNotifier";
import { useAuthActionGuard } from "./useAuthActionGuard";
import { useSyncedFavoriteIds } from "./useSyncedFavoriteIds";
import { addToSet, removeFromSet, toggleInSet } from "../utils/setUtils";
import {
  createFavoriteMutationErrorConfig,
  executeFavoriteMutation,
} from "../utils/favoriteMutation";
import { FAVORITE_SONG_MESSAGES } from "../constants/userFeatureConstants";

/** useFavoriteSongs の返り値型です。 */
interface UseFavoriteSongsResult {
  /** お気に入り追加/削除を切り替えます。 */
  toggleFavoriteSong: (songId: number) => Promise<void>;
  /** 指定楽曲がお気に入りか判定します。 */
  isFavoriteSong: (songId: number) => boolean;
  /** 指定楽曲が更新中か判定します。 */
  isToggling: (songId: number) => boolean;
}

/**
 * **useFavoriteSongs カスタムフック**
 * 
 * お気に入り曲の管理を共通化するカスタムフックです。
 * 楽曲のお気に入り追加/削除、オプティミスティック更新、ロールバック処理を提供します。
 * 
 * @param onLoginRequired - 未ログイン時に呼ばれるコールバック（ログイン画面への遷移など）
 * @returns {{
 *   toggleFavoriteSong: (songId: number) => Promise<void>,  // お気に入り追加/削除の切り替え
 *   isFavoriteSong: (songId: number) => boolean,  // 指定曲がお気に入りか判定
 *   isToggling: (songId: number) => boolean  // 指定曲が処理中か判定
 * }}
 * 
 * @example
 * ```tsx
 * const { toggleFavoriteSong, isFavoriteSong, isToggling } = useFavoriteSongs(onLoginClick);
 * 
 * // お気に入り状態の確認
 * const isFavorite = isFavoriteSong(123);
 * 
 * // お気に入りの追加/削除
 * await toggleFavoriteSong(123);
 * 
 * // ハートアイコンの表示制御
 * {isFavoriteSong(song.id) ? <HeartIconSolid /> : <HeartIcon />}
 * 
 * // 連打防止チェック
 * {isToggling(song.id) && <Spinner />}
 * ```
 */
export const useFavoriteSongs = (onLoginRequired?: () => void): UseFavoriteSongsResult => {
  const { isAuthenticated } = useAuth();
  const [favoriteSongIds, setFavoriteSongIds] = useState<Set<number>>(new Set());
  const [togglingIds, setTogglingIds] = useState<Set<number>>(new Set());
  const { notifyError } = useErrorToastNotifier();
  const { guardAction } = useAuthActionGuard({
    isAuthenticated,
    onUnauthorized: () => {
      onLoginRequired?.();
    },
  });

  useSyncedFavoriteIds({
    isAuthenticated,
    setIdSet: setFavoriteSongIds,
    fetchItems: () => getFavorites(500),
    selectId: (favorite) => favorite.song_id,
    notifyError,
    syncErrorLabel: FAVORITE_SONG_MESSAGES.syncErrorLabel,
    syncErrorUserMessage: FAVORITE_SONG_MESSAGES.syncErrorUserMessage,
  });

  /**
   * ── お気に入り曲の追加/削除を切り替え ──
   * 
   * オプティミスティック更新を採用し、サーバー通信前に画面を即座に更新します。
   * API通信に失敗した場合は、自動的に元の状態にロールバックします。
   * 
   * @param songId - 楽曲ID
  * @note 未ログイン時は onLoginRequired コールバックを実行し、処理を中断します
   */
  const toggleFavoriteSong = useCallback(async (songId: number) => {
    await guardAction(async () => {
      let wasFavorite = false;
      setFavoriteSongIds(prev => {
        wasFavorite = prev.has(songId);
        return toggleInSet(prev, songId);
      });

      setTogglingIds(prev => addToSet(prev, songId));

      await executeFavoriteMutation({
        isFavorite: wasFavorite,
        onAdd: () => addFavorite(songId),
        onRemove: () => removeFavorite(songId),
        errorConfig: createFavoriteMutationErrorConfig(notifyError, {
          errorLabel: FAVORITE_SONG_MESSAGES.toggleErrorLabel,
          errorUserMessage: FAVORITE_SONG_MESSAGES.toggleErrorUserMessage,
        }),
        onError: () => {
          setFavoriteSongIds((prev) => {
            return wasFavorite ? addToSet(prev, songId) : removeFromSet(prev, songId);
          });
        },
        onFinally: () => {
          setTogglingIds((prev) => removeFromSet(prev, songId));
        },
      });
    });
  }, [guardAction, notifyError]);

  /**
   * ── 指定曲がお気に入りか判定 ──
   * 
   * @param songId - 判定対象の曲ID
   * @returns true: お気に入り登録済み / false: 未登録
   */
  const isFavoriteSong = useCallback((songId: number) => {
    return favoriteSongIds.has(songId);
  }, [favoriteSongIds]);

  /**
   * ── 指定曲が処理中か判定 ──
   * 
   * 連打防止やローディング表示に使用します。
   * 
   * @param songId - 判定対象の曲ID
   * @returns true: API通信中 / false: 待機中
   */
  const isToggling = useCallback((songId: number) => {
    return togglingIds.has(songId);
  }, [togglingIds]);

  return {
    toggleFavoriteSong,
    isFavoriteSong,
    isToggling,
  };
};
