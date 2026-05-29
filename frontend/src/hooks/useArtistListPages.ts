import { useState, useEffect, useCallback, useRef } from "react";
import { getArtists, Artist } from "../api";
import { ARTISTS_PER_PAGE, SEARCH_ALIASES } from "../constants/songListConstants";

/**
 * アーティスト一覧＋ページング管理フック
 * @param query 検索クエリ
 * @returns アーティストリスト・ページ状態・操作関数
 */
export const useArtistListPages = (
  query: string,
) => {
  const [artists, setArtists] = useState<Artist[]>([]);
  const [totalArtists, setTotalArtists] = useState(0);
  const [artistPage, setArtistPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const lastFetchRef = useRef<{ page: number; query: string } | null>(null);

  const totalPages = Math.ceil(totalArtists / ARTISTS_PER_PAGE);

  const fetchArtists = useCallback(async (page: number) => {
    const effectiveQuery = SEARCH_ALIASES[query] || query;
    if (lastFetchRef.current?.page === page && lastFetchRef.current?.query === effectiveQuery) {
      return;
    }

    lastFetchRef.current = { page, query: effectiveQuery };
    setLoading(true);
    try {
      const data = await getArtists(ARTISTS_PER_PAGE, page * ARTISTS_PER_PAGE, effectiveQuery);
      setArtists(data.artists);
      setTotalArtists(data.total);
      setError(null);
    } catch (err: unknown) {
      setError("アーティスト取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, [query]);

  useEffect(() => {
    fetchArtists(artistPage);
  }, [artistPage, query, fetchArtists]);

  return {
    artists,
    totalArtists,
    artistPage,
    setArtistPage,
    loading,
    error,
    totalPages,
    fetchArtists,
  };
};
