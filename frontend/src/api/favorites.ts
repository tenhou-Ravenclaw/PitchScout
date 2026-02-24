import { API } from "./client";
import type { FavoriteArtist, FavoriteSong } from "./types";

export const getFavoriteArtists = async (): Promise<FavoriteArtist[]> => {
  const res = await API.get<FavoriteArtist[]>("/favorite-artists");
  return res.data;
};

export const addFavoriteArtist = async (artistId: number, artistName: string): Promise<FavoriteArtist> => {
  const res = await API.post<FavoriteArtist>("/favorite-artists", {
    artist_id: artistId,
    artist_name: artistName,
  });
  return res.data;
};

export const removeFavoriteArtist = async (artistId: number): Promise<{ message: string }> => {
  const res = await API.delete<{ message: string }>(`/favorite-artists/${artistId}`);
  return res.data;
};

export const getFavorites = async (limit = 100): Promise<FavoriteSong[]> => {
  const res = await API.get("/favorites", { params: { limit } });
  return res.data;
};

export const addFavorite = async (songId: number) => {
  const res = await API.post("/favorites", { song_id: songId });
  return res.data;
};

export const removeFavorite = async (songId: number) => {
  await API.delete(`/favorites/${songId}`);
};

export const checkFavorite = async (songId: number): Promise<boolean> => {
  const res = await API.get(`/favorites/check/${songId}`);
  return res.data.is_favorite;
};
