import { useItemList } from "./useItemList";

/**
 * **useFavoriteArtists カスタムフック**
 *
 * お気に入りアーティストの管理を提供するカスタムフックです。
 * useItemCollection("favoriteArtist") の薄いラッパーで、
 * oオプティミスティック更新・ロールバック・連打防止を内包します。
 *
 * @returns {{
 *   favoriteIds: number[],  // お気に入り登録済みのアーティストIDリスト
 *   toggleFavorite: (artistId: number, artistName: string) => Promise<void>,  // お気に入り追加/削除の切り替え
 *   isFavorite: (artistId: number) => boolean  // 指定アーティストがお気に入りか判定
 * }}
 *
 * @example
 * ```tsx
 * const { toggleFavorite, isFavorite } = useFavoriteArtists();
 *
 * // お気に入りアイコンの表示制御
 * {isFavorite(artist.id) ? <StarSolid /> : <StarOutline />}
 *
 * // お気に入りの追加/削除
 * await toggleFavorite(artist.id, artist.name);
 * ```
 */
export const useFavoriteArtists = () => {
  const { ids, toggle, isIncluded } = useItemList("favoriteArtist");
  return {
    favoriteIds: ids,
    toggleFavorite: (artistId: number, artistName: string) => toggle(artistId, artistName),
    isFavorite: isIncluded,
  };
};
