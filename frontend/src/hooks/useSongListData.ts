import { useState } from "react";
import { useCallback } from "react";
import { UserRange } from "../api";
import { Artist, Song } from "../api";
import { getArtistSongs } from "../api/songs";
import { toUserMessage } from "../api/error";
import { useArtistListPagination } from "./useArtistListPagination";
import { useSongSearchPagination } from "./useSongSearchPagination";
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
  } = useArtistListPagination(activeQuery);

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
  } = useSongSearchPagination(activeQuery, userRange ?? null);

  // 五十音インデックスジャンプ
  const { handleIndexJump } = useIndexJump(
    artists,
    totalArtists,
    totalPages,
    setArtistPage,
    notifyError
  );

  // サブhookで管理しきれない値・ロジックを追加
  const [pageInput, setPageInput] = useState("1");
  const [searchPageInput, setSearchPageInput] = useState("1");
  const [selectedArtist, setSelectedArtist] = useState<Artist | null>(null);
  const [artistSongs, setArtistSongs] = useState<Song[]>([]);
  const [songsLoading, setSongsLoading] = useState(false);

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
    if (onSearchChange) {
      onSearchChange(query);
    }
  }, [onSearchChange]);

  // ページネーション操作
  const handlePaginate = useCallback((action: PaginationAction) => {
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
    // jump
    const pageNum = parseInt(pageInput, 10);
    if (!isNaN(pageNum) && pageNum >= 1 && pageNum <= totalPages) {
      setArtistPage(pageNum - 1);
    }
  }, [artistPage, pageInput, totalPages]);

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

