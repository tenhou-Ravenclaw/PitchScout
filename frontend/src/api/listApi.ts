import { API } from "./client";
import type { FavoriteArtist, FavoriteSong, AnalysisHistoryRecord } from "./types";

/**
 * 汎用リストAPIラッパー
 * お気に入り楽曲・アーティスト・履歴などのCRUDを共通化
 */
export type ListType = "favoriteSong" | "favoriteArtist" | "analysisHistory";

/**
 * リストAPIの型定義
 */
export interface ListApiMap {
  favoriteSong: {
    get: () => Promise<FavoriteSong[]>;
    add: (songId: number) => Promise<{ favorite_id: string }>;
    remove: (songId: number) => Promise<{ message: string }>;
  };
  favoriteArtist: {
    get: () => Promise<FavoriteArtist[]>;
    add: (artistId: number, artistName: string) => Promise<FavoriteArtist>;
    remove: (artistId: number) => Promise<{ message: string }>;
  };
  analysisHistory: {
    get: (limit?: number) => Promise<AnalysisHistoryRecord[]>;
    remove: (recordId: string) => Promise<{ message: string }>;
    update: (recordId: string, data: { file_name: string }) => Promise<AnalysisHistoryRecord>;
  };
}

// 個別exportは廃止。listApi.favoriteSong.*等で統一。

export const listApi: ListApiMap = {
  favoriteSong: {
    /** お気に入り楽曲一覧取得 */
    get: async (): Promise<FavoriteSong[]> => {
      const res = await API.get<FavoriteSong[]>("/favorites");
      return res.data;
    },
    /** お気に入り楽曲追加 */
    add: async (songId: number): Promise<{ favorite_id: string }> => {
      const res = await API.post<{ favorite_id: string }>("/favorites", { song_id: songId });
      return res.data;
    },
    /** お気に入り楽曲削除 */
    remove: async (songId: number): Promise<{ message: string }> => {
      const res = await API.delete<{ message: string }>(`/favorites/${songId}`);
      return res.data;
    },
  },
  favoriteArtist: {
    /** お気に入りアーティスト一覧取得 */
    get: async (): Promise<FavoriteArtist[]> => {
      const res = await API.get<FavoriteArtist[]>("/favorite-artists");
      return res.data;
    },
    /** お気に入りアーティスト追加 */
    add: async (artistId: number, artistName: string): Promise<FavoriteArtist> => {
      const res = await API.post<FavoriteArtist>("/favorite-artists", { artist_id: artistId, artist_name: artistName });
      return res.data;
    },
    /** お気に入りアーティスト削除 */
    remove: async (artistId: number): Promise<{ message: string }> => {
      const res = await API.delete<{ message: string }>(`/favorite-artists/${artistId}`);
      return res.data;
    },
  },
  analysisHistory: {
    get: async (limit = 50): Promise<AnalysisHistoryRecord[]> => {
      const res = await API.get<AnalysisHistoryRecord[]>("/analysis/history", { params: { limit } });
      return res.data;
    },
    remove: async (recordId: string): Promise<{ message: string }> => {
      const res = await API.delete<{ message: string }>(`/analysis/history/${recordId}`);
      return res.data;
    },
    update: async (recordId: string, data: { file_name: string }): Promise<AnalysisHistoryRecord> => {
      const res = await API.patch<AnalysisHistoryRecord>(`/analysis/history/${recordId}`, data);
      return res.data;
    },
  },
};
