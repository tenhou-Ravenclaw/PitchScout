import { useEffect, useState, useCallback } from "react";
import { getArtists, getArtistSongs, Artist, UserRange, Song, getSongs, toUserMessage } from "../api";
import { INDEX_KANA, getConsonantRow, SEARCH_ALIASES, ARTISTS_PER_PAGE, SONGS_PER_PAGE } from "../constants/songListConstants";

/**
 * useSongListData フックの入力パラメータ
 */
interface UseSongListDataParams {
  /** 初期検索クエリ */
  initialQuery: string;
  /** ユーザー音域 */
  userRange?: UserRange | null;
  /** 画面に通知するエラーメッセージ表示関数 */
  notifyError: (message: string) => void;
  /** 検索クエリ確定時に外部へ通知する関数 */
  onSearchChange?: (query: string) => void;
}

/** ページング操作の種別 */
export type PaginationAction = "next" | "prev" | "jump";

/**
 * SongListPage で利用するデータ取得・選択・ページング処理を集約したフックです。
 */
export const useSongListData = ({
  initialQuery,
  userRange,
  notifyError,
  onSearchChange,
}: UseSongListDataParams) => {
  const [activeQuery, setActiveQuery] = useState(initialQuery);
  const [searchInput, setSearchInput] = useState(initialQuery);

  const [artists, setArtists] = useState<Artist[]>([]);
  const [totalArtists, setTotalArtists] = useState(0);
  const [artistPage, setArtistPage] = useState(0);
  const [pageInput, setPageInput] = useState("1");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchSongs, setSearchSongs] = useState<Song[]>([]);
  const [totalSearchSongs, setTotalSearchSongs] = useState(0);
  const [searchPage, setSearchPage] = useState(0);
  const [searchPageInput, setSearchPageInput] = useState("1");
  const [searchLoading, setSearchLoading] = useState(false);

  const [selectedArtist, setSelectedArtist] = useState<Artist | null>(null);
  const [artistSongs, setArtistSongs] = useState<Song[]>([]);
  const [songsLoading, setSongsLoading] = useState(false);

  const totalPages = Math.ceil(totalArtists / ARTISTS_PER_PAGE);
  const totalSearchPages = Math.ceil(totalSearchSongs / SONGS_PER_PAGE);

  useEffect(() => {
    setActiveQuery(initialQuery);
    setSearchInput(initialQuery);
  }, [initialQuery]);

  const fetchArtists = useCallback(async (page: number) => {
    setLoading(true);
    try {
      const effectiveQuery = SEARCH_ALIASES[activeQuery] || activeQuery;
      const data = await getArtists(ARTISTS_PER_PAGE, page * ARTISTS_PER_PAGE, effectiveQuery);
      setArtists(data.artists);
      setTotalArtists(data.total);
      setError(null);
    } catch (err: unknown) {
      setError("楽曲の取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, [activeQuery]);

  const fetchSearchSongs = useCallback(async (page: number) => {
    if (!activeQuery) {
      setSearchSongs([]);
      setTotalSearchSongs(0);
      return;
    }
    setSearchLoading(true);
    try {
      const data = await getSongs(SONGS_PER_PAGE, page * SONGS_PER_PAGE, activeQuery, userRange);
      setSearchSongs(data.songs);
      setTotalSearchSongs(data.total);
      setError(null);
    } catch (err: unknown) {
      setError("楽曲検索に失敗しました");
      setSearchSongs([]);
      setTotalSearchSongs(0);
    } finally {
      setSearchLoading(false);
    }
  }, [activeQuery, userRange]);

  useEffect(() => {
    if (activeQuery) {
      setSearchPage(0);
      setSearchPageInput("1");
    } else {
      setArtistPage(0);
      setPageInput("1");
      setSelectedArtist(null);
    }
  }, [activeQuery]);

  useEffect(() => {
    if (!activeQuery) {
      fetchArtists(artistPage);
      setPageInput((artistPage + 1).toString());
    }
  }, [artistPage, activeQuery, fetchArtists]);

  useEffect(() => {
    if (activeQuery) {
      fetchSearchSongs(searchPage);
      setSearchPageInput((searchPage + 1).toString());
    }
  }, [searchPage, activeQuery, fetchSearchSongs]);

  const handleSelectArtist = useCallback(async (artist: Artist) => {
    setSelectedArtist(artist);
    setSongsLoading(true);
    try {
      const songs = await getArtistSongs(artist.id, userRange);
      setArtistSongs(songs);
    } catch (err) {
      setArtistSongs([]);
      notifyError(toUserMessage(err, "アーティストの楽曲取得に失敗しました。"));
    } finally {
      setSongsLoading(false);
    }
  }, [notifyError, userRange]);

  const closeSelectedArtist = useCallback(() => {
    setSelectedArtist(null);
  }, []);

  const handleSearchSubmit = useCallback((query: string) => {
    setActiveQuery(query);
    if (onSearchChange) {
      onSearchChange(query);
    }
  }, [onSearchChange]);

  type PaginationMode = "search" | "artist";

  const setPageByMode = useCallback((mode: PaginationMode, nextPage: number) => {
    if (mode === "search") {
      setSearchPage(nextPage);
      setSearchPageInput((nextPage + 1).toString());
      return;
    }
    setArtistPage(nextPage);
    setPageInput((nextPage + 1).toString());
  }, []);

  const getPaginationState = useCallback(() => {
    if (activeQuery) {
      return {
        mode: "search" as const,
        currentPage: searchPage,
        totalPages: totalSearchPages,
        input: searchPageInput,
      };
    }
    return {
      mode: "artist" as const,
      currentPage: artistPage,
      totalPages,
      input: pageInput,
    };
  }, [activeQuery, searchPage, totalSearchPages, searchPageInput, artistPage, totalPages, pageInput]);

  const scrollTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const handleNext = useCallback(() => {
    const state = getPaginationState();
    if (state.currentPage + 1 < state.totalPages) {
      setPageByMode(state.mode, state.currentPage + 1);
    }
    scrollTop();
  }, [getPaginationState, setPageByMode, scrollTop]);

  const handlePrev = useCallback(() => {
    const state = getPaginationState();
    if (state.currentPage > 0) {
      setPageByMode(state.mode, state.currentPage - 1);
    }
    scrollTop();
  }, [getPaginationState, setPageByMode, scrollTop]);

  const handlePageJump = useCallback(() => {
    const state = getPaginationState();
    if (state.totalPages < 1) {
      return;
    }

    let pageNumber = parseInt(state.input, 10);
    if (isNaN(pageNumber)) {
      setPageByMode(state.mode, state.currentPage);
      return;
    }

    if (pageNumber < 1) pageNumber = 1;
    if (pageNumber > state.totalPages) pageNumber = state.totalPages;

    setPageByMode(state.mode, pageNumber - 1);
    scrollTop();
  }, [getPaginationState, setPageByMode, scrollTop]);

  const isCurrentPageMatchedByRow = useCallback((targetRow: number): boolean => {
    const indexInPage = artists.findIndex((artist) => getConsonantRow(artist.reading || "") >= targetRow);
    return indexInPage !== -1 && getConsonantRow(artists[indexInPage].reading || "") === targetRow;
  }, [artists]);

  const findFirstPageByConsonantRow = useCallback(async (targetRow: number): Promise<number> => {
    let low = 0;
    let high = Math.max(totalPages - 1, 0);
    let found = 0;

    while (low <= high) {
      const mid = Math.floor((low + high) / 2);
      const offset = mid * ARTISTS_PER_PAGE;
      const { artists: page } = await getArtists(ARTISTS_PER_PAGE, offset);
      if (!page.length) break;

      const firstRow = getConsonantRow(page[0].reading || "");
      const lastRow = getConsonantRow(page[page.length - 1].reading || "");

      if (targetRow < firstRow) {
        high = mid - 1;
        continue;
      }
      if (targetRow > lastRow) {
        low = mid + 1;
        continue;
      }

      found = mid;
      high = mid - 1;
    }

    return found;
  }, [totalPages]);

  const handleIndexJump = useCallback(async (char: string) => {
    const targetRow = INDEX_KANA.indexOf(char);
    if (targetRow === -1 || totalArtists === 0) {
      return;
    }

    if (isCurrentPageMatchedByRow(targetRow)) {
      scrollTop();
      return;
    }

    setLoading(true);
    try {
      const found = await findFirstPageByConsonantRow(targetRow);

      setArtistPage(found);
      setPageInput((found + 1).toString());
      scrollTop();
    } catch (err) {
      notifyError(toUserMessage(err, "インデックス移動に失敗しました。"));
    } finally {
      setLoading(false);
    }
  }, [totalArtists, isCurrentPageMatchedByRow, findFirstPageByConsonantRow, scrollTop, notifyError]);

  const handlePaginate = useCallback((action: PaginationAction) => {
    if (action === "next") {
      handleNext();
      return;
    }
    if (action === "prev") {
      handlePrev();
      return;
    }
    handlePageJump();
  }, [handleNext, handlePrev, handlePageJump]);

  return {
    activeQuery,
    setActiveQuery,
    searchInput,
    setSearchInput,

    artists,
    totalArtists,
    artistPage,
    pageInput,
    setPageInput,
    loading,
    error,

    searchSongs,
    totalSearchSongs,
    searchPage,
    searchPageInput,
    setSearchPageInput,
    searchLoading,

    selectedArtist,
    artistSongs,
    songsLoading,

    totalPages,
    totalSearchPages,

    handleSelectArtist,
    closeSelectedArtist,
    handleSearchSubmit,
    handleNext,
    handlePrev,
    handlePageJump,
    handlePaginate,
    handleIndexJump,
  };
};
