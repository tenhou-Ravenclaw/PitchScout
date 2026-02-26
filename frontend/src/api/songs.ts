import { API } from "./client";
import type { SongsResponse, Song, UserRange, ArtistsResponse } from "./types";

/** 楽曲検索APIのクエリパラメータです。 */
type SongQueryParams = {
  /** 取得上限件数 */
  limit?: number;
  /** 取得開始オフセット */
  offset?: number;
  /** 検索クエリ */
  q?: string;
  /** 地声最低Hz */
  chest_min_hz?: number;
  /** 地声最高Hz */
  chest_max_hz?: number;
  /** 裏声最高Hz */
  falsetto_max_hz?: number;
};

/**
 * 楽曲一覧（または検索結果）を取得します。
 *
 * @param limit - 取得上限件数
 * @param offset - 取得開始オフセット
 * @param query - 曲名・アーティスト名検索クエリ
 * @param userRange - ユーザー音域（指定時はおすすめキー算出に利用）
 * @returns 楽曲一覧と総件数
 */
export const getSongs = async (
  limit: number = 20,
  offset: number = 0,
  query: string = "",
  userRange?: UserRange | null,
): Promise<SongsResponse> => {
  const params: SongQueryParams = { limit, offset };
  if (query) params.q = query;
  if (userRange) {
    params.chest_min_hz = userRange.chest_min_hz;
    params.chest_max_hz = userRange.chest_max_hz;
    if (userRange.falsetto_max_hz) {
      params.falsetto_max_hz = userRange.falsetto_max_hz;
    }
  }
  const res = await API.get<SongsResponse>("/songs", { params });
  return res.data;
};

/**
 * アーティスト一覧を取得します。
 *
 * @param limit - 取得上限件数
 * @param offset - 取得開始オフセット
 * @param query - アーティスト検索クエリ
 * @returns アーティスト一覧と総件数
 */
export const getArtists = async (
  limit: number = 10,
  offset: number = 0,
  query: string = "",
): Promise<ArtistsResponse> => {
  const params: SongQueryParams = { limit, offset };
  if (query) params.q = query;
  const res = await API.get<ArtistsResponse>("/artists", { params });
  return res.data;
};

/**
 * 指定アーティストの楽曲一覧を取得します。
 *
 * @param artistId - アーティストID
 * @param userRange - ユーザー音域（指定時はおすすめキー算出に利用）
 * @returns 楽曲配列
 */
export const getArtistSongs = async (
  artistId: number,
  userRange?: UserRange | null,
): Promise<Song[]> => {
  const params: SongQueryParams = {};
  if (userRange) {
    params.chest_min_hz = userRange.chest_min_hz;
    params.chest_max_hz = userRange.chest_max_hz;
    if (userRange.falsetto_max_hz) {
      params.falsetto_max_hz = userRange.falsetto_max_hz;
    }
  }
  const res = await API.get<Song[]>(`/artists/${artistId}/songs`, { params });
  return res.data;
};
