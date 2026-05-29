import { API } from "./client";
import type { SongsResponse, Song, UserRange, ArtistsResponse, ArtistIndexPageResponse } from "./types";

type SongQueryParams = {
  limit?: number;
  offset?: number;
  q?: string;
  chest_min_hz?: number;
  chest_max_hz?: number;
  falsetto_max_hz?: number;
};

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

export const getArtistIndexPage = async (
  char: string,
  limit: number = 10,
): Promise<ArtistIndexPageResponse> => {
  const res = await API.get<ArtistIndexPageResponse>("/artists/index-page", {
    params: { char, limit },
  });
  return res.data;
};

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
