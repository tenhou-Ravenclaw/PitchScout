import { useState, useEffect, useCallback } from "react";
import { getSongs, Song, UserRange } from "../api";
import { SONGS_PER_PAGE, SEARCH_ALIASES } from "../constants/songListConstants";

/**
 * 楽曲検索＋ページング管理フック
 * @param query 検索クエリ
 * @param userRange ユーザー音域
 * @returns 楽曲リスト・ページ状態・操作関数
 */
export const useSongSearchPages = (
  query: string,
  userRange: UserRange | null,
) => {
  const [searchSongs, setSearchSongs] = useState<Song[]>([]);
  const [totalSearchSongs, setTotalSearchSongs] = useState(0);
  const [searchPage, setSearchPage] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totalPages = Math.ceil(totalSearchSongs / SONGS_PER_PAGE);

  const fetchSearchSongs = useCallback(async (page: number) => {
    setLoading(true);
    try {
      const effectiveQuery = SEARCH_ALIASES[query] || query;
      const data = await getSongs(SONGS_PER_PAGE, page * SONGS_PER_PAGE, effectiveQuery, userRange);
      setSearchSongs(data.songs);
      setTotalSearchSongs(data.total);
      setError(null);
    } catch (err: unknown) {
      setError("楽曲検索に失敗しました");
      setSearchSongs([]);
      setTotalSearchSongs(0);
    } finally {
      setLoading(false);
    }
  }, [query, userRange]);

  useEffect(() => {
    fetchSearchSongs(searchPage);
  }, [searchPage, query, userRange, fetchSearchSongs]);

  return {
    searchSongs,
    totalSearchSongs,
    searchPage,
    setSearchPage,
    loading,
    error,
    totalPages,
    fetchSearchSongs,
  };
};
