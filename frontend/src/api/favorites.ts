import { API } from "./client";
import type { FavoriteArtist, FavoriteSong } from "./types";

/**
 * お気に入り登録済みアーティスト一覧を取得します。
 *
 * @returns お気に入りアーティスト配列
 */
export const getFavoriteArtists = async (): Promise<FavoriteArtist[]> => {
  const res = await API.get<FavoriteArtist[]>("/favorite-artists");
  return res.data;
};

/**
 * 指定アーティストをお気に入りに追加します。
 *
 * @param artistId - アーティストID
 * @param artistName - アーティスト名
 * @returns 追加されたお気に入りアーティスト情報
 */
export const addFavoriteArtist = async (
  artistId: number,
  artistName: string,
): Promise<FavoriteArtist> => {
  const res = await API.post<FavoriteArtist>("/favorite-artists", {
    artist_id: artistId,
    artist_name: artistName,
  });
  return res.data;
};

/**
 * 指定アーティストをお気に入りから削除します。
 *
 * @param artistId - アーティストID
 * @returns APIの削除結果メッセージ
 */
export const removeFavoriteArtist = async (
  artistId: number,
): Promise<{ message: string }> => {
  const res = await API.delete<{ message: string }>(
    `/favorite-artists/${artistId}`,
  );
  return res.data;
};

/**
 * お気に入り楽曲一覧を取得します。
 *
 * @param limit - 取得上限件数
 * @returns お気に入り楽曲配列
 */
export const getFavorites = async (limit = 100): Promise<FavoriteSong[]> => {
  const res = await API.get("/favorites", { params: { limit } });
  return res.data;
};

/**
 * 指定楽曲をお気に入りへ追加します。
 *
 * @param songId - 楽曲ID
 * @returns APIレスポンス
 */
export const addFavorite = async (songId: number) => {
  const res = await API.post("/favorites", { song_id: songId });
  return res.data;
};

/**
 * 指定楽曲をお気に入りから削除します。
 *
 * @param songId - 楽曲ID
 */
export const removeFavorite = async (songId: number) => {
  await API.delete(`/favorites/${songId}`);
};

/**
 * 指定楽曲がお気に入り済みかを確認します。
 *
 * @param songId - 楽曲ID
 * @returns お気に入り済みの場合は true
 */
export const checkFavorite = async (songId: number): Promise<boolean> => {
  const res = await API.get(`/favorites/check/${songId}`);
  return res.data.is_favorite;
};
