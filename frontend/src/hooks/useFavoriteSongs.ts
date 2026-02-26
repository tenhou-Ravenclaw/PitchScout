import { useState, useCallback } from "react";
import { getFavorites, addFavorite, removeFavorite } from "../api";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "./useToast";
import { useErrorNotifier } from "./useErrorNotifier";
import { useAuthActionGuard } from "./useAuthActionGuard";
import { useSyncedFavoriteSet } from "./useSyncedFavoriteSet";
import { addToSet, removeFromSet, toggleInSet } from "../utils/setUtils";
import { runFavoriteMutation } from "../utils/favoriteMutation";
import { FAVORITE_SONG_MESSAGES } from "../constants/favoriteMessages";

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
export const useFavoriteSongs = (onLoginRequired?: () => void) => {
  const { isAuthenticated } = useAuth();
  const [favoriteSongIds, setFavoriteSongIds] = useState<Set<number>>(new Set());
  const [togglingIds, setTogglingIds] = useState<Set<number>>(new Set());
  const { showApiErrorToast } = useToast();
  const { notifyError } = useErrorNotifier({ showApiErrorToast });
  const { ensureAuthenticated } = useAuthActionGuard({
    isAuthenticated,
    onUnauthorized: () => {
      onLoginRequired?.();
    },
  });

  const fetchFavoriteSongIds = useCallback(async (): Promise<number[]> => {
    const favorites = await getFavorites(500); // 最大500件取得
    return favorites.map(favorite => favorite.song_id);
  }, []);

  const handleSyncError = useCallback((error: unknown) => {
    notifyError(
      FAVORITE_SONG_MESSAGES.syncErrorLabel,
      error,
      FAVORITE_SONG_MESSAGES.syncErrorUserMessage,
    );
  }, [notifyError]);

  useSyncedFavoriteSet({
    isAuthenticated,
    setIdSet: setFavoriteSongIds,
    fetchIds: fetchFavoriteSongIds,
    onSyncError: handleSyncError,
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
    if (!ensureAuthenticated()) {
      return;
    }

    // オプティミスティック更新: サーバー通信前に先に状態を変更
    let wasFavorite = false;
    setFavoriteSongIds(prev => {
      wasFavorite = prev.has(songId);
      return toggleInSet(prev, songId);
    });

    // 処理中フラグをON（連打防止）
    setTogglingIds(prev => addToSet(prev, songId));

    try {
      await runFavoriteMutation(
        wasFavorite,
        () => addFavorite(songId),
        () => removeFavorite(songId),
      );
    } catch (err) {
      notifyError(
        FAVORITE_SONG_MESSAGES.toggleErrorLabel,
        err,
        FAVORITE_SONG_MESSAGES.toggleErrorUserMessage,
      );
      
      // ロールバック: 失敗時は元の状態に戻す
      setFavoriteSongIds(prev => {
        return wasFavorite ? addToSet(prev, songId) : removeFromSet(prev, songId);
      });
    } finally {
      // 処理中フラグをOFF
      setTogglingIds(prev => removeFromSet(prev, songId));
    }
  }, [ensureAuthenticated, notifyError]);

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
    isToggling
  };
};
