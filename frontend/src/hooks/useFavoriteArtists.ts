import { useState, useEffect, useCallback } from "react";
import { getFavoriteArtists, addFavoriteArtist, removeFavoriteArtist, toUserMessage } from "../api";
import { useToast } from "./useToast";

/**
 * **useFavoriteArtists カスタムフック**
 * 
 * お気に入りアーティストの管理を共通化するカスタムフックです。
 * 複数のコンポーネントで重複していたお気に入りアーティストの状態管理と
 * API通信ロジックを一元管理します。
 * 
 * @returns {{
 *   favoriteIds: number[],  // お気に入り登録済みのアーティストIDリスト
 *   toggleFavorite: (artistId: number, artistName: string) => Promise<void>,  // お気に入り追加/削除の切り替え
 *   isFavorite: (artistId: number) => boolean  // 指定アーティストがお気に入りか判定
 * }}
 * 
 * @example
 * ```tsx
 * const { favoriteIds, toggleFavorite, isFavorite } = useFavoriteArtists();
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
export const useFavoriteArtists = () => {
  const [favoriteIds, setFavoriteIds] = useState<number[]>([]);
  const { showToast } = useToast();

  /**
   * ── 初回マウント時: サーバーからお気に入り情報を同期 ──
   * コンポーネントがマウントされたタイミングで一度だけ実行され、
   * ユーザーのお気に入りアーティスト情報を取得します。
   */
  useEffect(() => {
    const syncFavorites = async () => {
      try {
        const favs = await getFavoriteArtists();
        setFavoriteIds(favs.map(f => f.artist_id));
      } catch (e) {
        console.error("お気に入り同期失敗", e);
        showToast(toUserMessage(e, "お気に入り情報の同期に失敗しました"));
      }
    };
    syncFavorites();
  }, [showToast]);

  /**
   * ── お気に入りの追加/削除を切り替え ──
   * 
   * 既にお気に入りに登録済みの場合は削除し、未登録の場合は追加します。
   * サーバーへのAPI通信完了後、ローカルの状態も自動的に更新されます。
   * 
   * @param artistId - アーティストID
   * @param artistName - アーティスト名（追加時にサーバーに送信）
   * @throws API通信エラー時にはToastでエラーメッセージを表示し、例外を再スローします
   */
  const toggleFavorite = useCallback(async (artistId: number, artistName: string) => {
    try {
      if (favoriteIds.includes(artistId)) {
        // 削除処理
        await removeFavoriteArtist(artistId);
        setFavoriteIds(prev => prev.filter(id => id !== artistId));
      } else {
        // 追加処理
        await addFavoriteArtist(artistId, artistName);
        setFavoriteIds(prev => [...prev, artistId]);
      }
    } catch (err) {
      showToast(toUserMessage(err, "お気に入り操作に失敗しました"));
      throw err; // 呼び出し側で追加のエラーハンドリングが必要な場合のため再スロー
    }
  }, [favoriteIds, showToast]);

  /**
   * ── 指定アーティストがお気に入りか判定 ──
   * 
   * @param artistId - 判定対象のアーティストID
   * @returns true: お気に入り登録済み / false: 未登録
   */
  const isFavorite = useCallback((artistId: number) => {
    return favoriteIds.includes(artistId);
  }, [favoriteIds]);

  return {
    favoriteIds,
    toggleFavorite,
    isFavorite
  };
};
