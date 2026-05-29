import { useState, useEffect } from "react";
import { useCallback } from "react";
import { UserRange } from "../api";
import { Artist, Song } from "../api";
import { getArtistSongs } from "../api/songs";
import { toUserMessage } from "../api/error";
import { useArtistListPages } from "./useArtistListPages";
import { useSongSearchPages } from "./useSongSearchPages";
import { useIndexJump } from "./useIndexJump";

/**
 * useSongListData フックの入力パラメータ
 * @interface UseSongListDataParams
 */
export interface UseSongListDataParams {
  /** 初期検索クエリ */
  initialQuery: string;
  /** ユーザー音域 */
  userRange?: UserRange | null;
  /** 画面に通知するエラーメッセージ表示関数 */
  notifyError: (message: string) => void;
  /** 検索クエリ変更時コールバック（任意） */
  onSearchChange?: (query: string) => void;
}

/** ページ操作の種別 */
export type PageAction = "next" | "prev" | "jump";

/**
 * SongListPage で利用するデータ取得・選択・ページング処理を集約したフックです。
 */
export const useSongListData = ({
  initialQuery,
  userRange,
  notifyError,
  onSearchChange,
}: UseSongListDataParams) => {
  // ── 状態管理 (State) ──
  const [activeQuery, setActiveQuery] = useState(initialQuery);
  const [searchInput, setSearchInput] = useState(initialQuery);
  const [pageInput, setPageInput] = useState("1");
  const [searchPageInput, setSearchPageInput] = useState("1");
  const [selectedArtist, setSelectedArtist] = useState<Artist | null>(null);
  const [artistSongs, setArtistSongs] = useState<Song[]>([]);
  const [songsLoading, setSongsLoading] = useState(false);

  // 外部（グローバル検索バーなど）からのクエリ変更を同期する
  useEffect(() => {
    if (initialQuery !== activeQuery) {
      setActiveQuery(initialQuery);
      setSearchInput(initialQuery);
      if (initialQuery) {
        setSelectedArtist(null); // 検索が実行されたらアーティスト選択を解除して結果を表示
      }
    }
  }, [initialQuery, activeQuery]);

  // アーティスト一覧＋ページング
  const {
    artists,
    totalArtists,
    artistPage,
    setArtistPage,
    loading,
    error,
    totalPages,
    fetchArtists,
  } = useArtistListPages(activeQuery);

  // 楽曲検索＋ページング
  const {
    searchSongs,
    totalSearchSongs,
    searchPage,
    setSearchPage,
    loading: searchLoading,
    error: searchError,
    totalPages: totalSearchPages,
    fetchSearchSongs,
  } = useSongSearchPages(activeQuery, userRange ?? null);

  // 五十音インデックスジャンプ
  const { handleIndexJump } = useIndexJump(
    artists,
    totalArtists,
    totalPages,
    setArtistPage,
    notifyError
  );

  // アーティスト選択・楽曲取得
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

  // 検索フォーム送信
  const handleSearchSubmit = useCallback((query: string) => {
    setActiveQuery(query);
    setSelectedArtist(null); // アーティスト選択状態を解除して検索結果を表示
    if (onSearchChange) {
      onSearchChange(query);
    }
  }, [onSearchChange]);

  // ページネーション操作
  const handlePaginate = useCallback((action: PageAction) => {
    if (activeQuery) {
      // 楽曲検索のページネーション
      if (action === "next") {
        setSearchPage(searchPage + 1);
        setSearchPageInput((searchPage + 2).toString());
        return;
      }
      if (action === "prev") {
        setSearchPage(Math.max(searchPage - 1, 0));
        setSearchPageInput(Math.max(searchPage, 1).toString());
        return;
      }
      const pageNum = parseInt(searchPageInput, 10);
      if (!isNaN(pageNum) && pageNum >= 1 && pageNum <= totalSearchPages) {
        setSearchPage(pageNum - 1);
      }
    } else {
      // アーティスト一覧のページネーション
      if (action === "next") {
        setArtistPage(artistPage + 1);
        setPageInput((artistPage + 2).toString());
        return;
      }
      if (action === "prev") {
        setArtistPage(Math.max(artistPage - 1, 0));
        setPageInput(Math.max(artistPage, 1).toString());
        return;
      }
      const pageNum = parseInt(pageInput, 10);
      if (!isNaN(pageNum) && pageNum >= 1 && pageNum <= totalPages) {
        setArtistPage(pageNum - 1);
      }
    }
  }, [activeQuery, searchPage, searchPageInput, totalSearchPages, artistPage, pageInput, totalPages, setArtistPage, setSearchPage]);

  return {
    activeQuery,
    setActiveQuery,
    searchInput,
    setSearchInput,
    // アーティスト一覧＋ページング
    artists,
    totalArtists,
    artistPage,
    setArtistPage,
    loading,
    error,
    totalPages,
    fetchArtists,
    pageInput,
    setPageInput,
    // 楽曲検索＋ページング
    searchSongs,
    totalSearchSongs,
    searchPage,
    setSearchPage,
    searchLoading,
    searchError,
    totalSearchPages,
    fetchSearchSongs,
    searchPageInput,
    setSearchPageInput,
    // アーティスト選択・楽曲取得
    selectedArtist,
    artistSongs,
    songsLoading,
    handleSelectArtist,
    closeSelectedArtist,
    // 検索フォーム送信
    handleSearchSubmit,
    // ページネーション操作
    handlePaginate,
    // 五十音インデックスジャンプ
    handleIndexJump,
  };
};
