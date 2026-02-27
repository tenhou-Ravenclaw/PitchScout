import { useItemCollection } from "./useItemCollection";

/**
 * **useFavoriteSongs カスタムフック**
 *
 * お気に入り曲の管理を提供するカスタムフックです。
 * useItemCollection("favoriteSong") の薄いラッパーで、
 * オプティミスティック更新・ロールバック・連打防止を内包します。
 *
 * @param onLoginRequired - 未ログイン時に呼ばれるコールバック（ログイン画面への遷移など）
 * @returns {{
 *   toggleFavoriteSong: (songId: number) => Promise<void>,  // お気に入り追加/削除の切り替え
 *   isFavoriteSong: (songId: number) => boolean,  // 指定曲がお気に入りか判定
 *   isToggling: (songId: number) => boolean  // 指定曲が処理中か判定（連打防止用）
 * }}
 *
 * @example
 * ```tsx
 * const { toggleFavoriteSong, isFavoriteSong, isToggling } = useFavoriteSongs(onLoginClick);
 *
 * // ハートアイコンの表示制御
 * {isFavoriteSong(song.id) ? <HeartIconSolid /> : <HeartIcon />}
 *
 * // 連打防止チェック
 * <button disabled={isToggling(song.id)} onClick={() => toggleFavoriteSong(song.id)} />
 * ```
 */
export const useFavoriteSongs = (onLoginRequired?: () => void) => {
  const { toggle, isIncluded, isToggling, loading } = useItemCollection("favoriteSong", onLoginRequired);
  return {
    toggleFavoriteSong: toggle,
    isFavoriteSong: isIncluded,
    isToggling,
    isLoading: loading,
  };
};
