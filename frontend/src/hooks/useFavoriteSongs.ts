import { useState, useEffect, useCallback } from "react";
import { getFavorites, addFavorite, removeFavorite, toUserMessage } from "../api";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "./useToast";

/**
 * **useFavoriteSongs カスタムフック**
 * 
 * お気に入り曲の管理を共通化するカスタムフックです。
 * 楽曲のお気に入り追加/削除、オプティミスティック更新、ロールバック処理を提供します。
 * 
 * @param onLoginRequired - 未ログイン時に呼ばれるコールバック（ログイン画面への遷移など）
 * @returns {{
 *   favoriteSongIds: Set<number>,  // お気に入り登録済みの曲IDセット
 *   toggleFavoriteSong: (songId: number) => Promise<void>,  // お気に入り追加/削除の切り替え
 *   isFavoriteSong: (songId: number) => boolean,  // 指定曲がお気に入りか判定
 *   isToggling: (songId: number) => boolean  // 指定曲が処理中か判定
 * }}
 * 
 * @example
 * ```tsx
 * const { favoriteSongIds, toggleFavoriteSong, isFavoriteSong, isToggling } = useFavoriteSongs(onLoginClick);
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
  const { showToast } = useToast();

  /**
   * ── 初回マウント時: サーバーからお気に入り曲情報を同期 ──
   * ログイン状態に応じて、ユーザーのお気に入り曲IDを取得します。
   * 未ログイン時は空のSetにリセットされます。
   */
  useEffect(() => {
    if (!isAuthenticated) {
      setFavoriteSongIds(new Set());
      return;
    }

    const syncFavorites = async () => {
      try {
        const favs = await getFavorites(500); // 最大500件取得
        setFavoriteSongIds(new Set(favs.map(f => f.song_id)));
      } catch (err) {
        console.error("お気に入り曲取得失敗:", err);
        showToast(toUserMessage(err, "お気に入り曲の取得に失敗しました。"));
      }
    };
    syncFavorites();
  }, [isAuthenticated, showToast]);

  /**
   * ── お気に入り曲の追加/削除を切り替え ──
   * 
   * オプティミスティック更新を採用し、サーバー通信前に画面を即座に更新します。
   * API通信に失敗した場合は、自動的に元の状態にロールバックします。
   * 
   * @param songId - 楽曲ID
   * @throws 未ログイン時は onLoginRequired コールバックを実行し、処理を中断
   */
  const toggleFavoriteSong = useCallback(async (songId: number) => {
    // 未認証の場合はログイン画面へ誘導
    if (!isAuthenticated) {
      onLoginRequired?.();
      return;
    }

    // オプティミスティック更新: サーバー通信前に先に状態を変更
    let wasFavorite = false;
    setFavoriteSongIds(prev => {
      wasFavorite = prev.has(songId);
      const next = new Set(prev);
      wasFavorite ? next.delete(songId) : next.add(songId);
      return next;
    });

    // 処理中フラグをON（連打防止）
    setTogglingIds(prev => new Set(prev).add(songId));

    try {
      // サーバーへのAPI通信
      if (wasFavorite) {
        await removeFavorite(songId);
      } else {
        await addFavorite(songId);
      }
    } catch (err) {
      console.error("お気に入り曲更新失敗:", err);
      showToast(toUserMessage(err, "お気に入り曲の更新に失敗しました。"));
      
      // ロールバック: 失敗時は元の状態に戻す
      setFavoriteSongIds(prev => {
        const next = new Set(prev);
        wasFavorite ? next.add(songId) : next.delete(songId);
        return next;
      });
    } finally {
      // 処理中フラグをOFF
      setTogglingIds(prev => {
        const next = new Set(prev);
        next.delete(songId);
        return next;
      });
    }
  }, [isAuthenticated, onLoginRequired, showToast]);

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
    favoriteSongIds,
    toggleFavoriteSong,
    isFavoriteSong,
    isToggling
  };
};
