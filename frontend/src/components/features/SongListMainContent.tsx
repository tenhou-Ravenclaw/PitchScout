/**
 * 【SongListMainContent.tsx】
 * 役割：楽曲一覧ページのメイン表示（検索結果 / アーティスト一覧）を担当するビューコンポーネントです。
 * 特徴：ヘッダー、エラー表示、検索結果表示、一覧表示、ページネーションを集約します。
 */

import React from "react";
import { Artist, Song, UserRange } from "../../api";
import ErrorBanner from "../ui/ErrorBanner";
import LoadingState from "../ui/LoadingState";
import Pagination from "../ui/Pagination";
import SearchBar from "../ui/SearchBar";
import SyllableIndex from "../ui/SyllableIndex";
import ArtistListPanel from "./ArtistListPanel";
import { SongTableWithLoading } from "./SongTable";
import { ARTISTS_PER_PAGE, SONGS_PER_PAGE } from "../../constants/songListConstants";
import { PaginationAction } from "../../hooks/useSongListData";

/**
 * SongListMainContent が受け取るプロパティ
 */
interface SongListMainContentProps {
  /** 検索入力の現在値 */
  searchInput: string;
  /** 検索入力変更時の処理 */
  onSearchInputChange: (value: string) => void;
  /** 検索確定時の処理 */
  onSearchSubmit: (query: string) => void;
  /** 現在のアクティブ検索クエリ */
  activeQuery: string;
  /** ユーザー音域 */
  userRange?: UserRange | null;
  /** 五十音インデックス押下時の処理 */
  onIndexClick: (char: string) => void;
  /** 画面内エラーメッセージ */
  error: string | null;

  /** 検索結果一覧 */
  searchSongs: Song[];
  /** 検索結果ページ番号 */
  searchPage: number;
  /** 検索結果ページ入力値 */
  searchPageInput: string;
  /** 検索結果ページ入力更新 */
  onSearchPageInputChange: (value: string) => void;
  /** 検索結果ローディング状態 */
  searchLoading: boolean;
  /** 検索結果総ページ数 */
  totalSearchPages: number;

  /** アーティスト一覧 */
  artists: Artist[];
  /** アーティストページ番号 */
  artistPage: number;
  /** アーティストページ入力値 */
  pageInput: string;
  /** アーティストページ入力更新 */
  onPageInputChange: (value: string) => void;
  /** アーティスト一覧ローディング状態 */
  loading: boolean;
  /** アーティスト総ページ数 */
  totalPages: number;

  /** ページング操作 */
  onPaginate: (action: PaginationAction) => void;

  /** アーティスト選択 */
  onSelectArtist: (artist: Artist) => void;
  /** アーティストお気に入りトグル */
  onToggleFavoriteArtist: (artistId: number, artistName: string) => void;
  /** アーティストお気に入り判定 */
  isFavoriteArtist: (artistId: number) => boolean;

  /** 楽曲お気に入りトグル */
  onToggleFavoriteSong: (songId: number) => void;
  /** 楽曲お気に入り判定 */
  isFavoriteSong: (songId: number) => boolean;
  /** 楽曲お気に入り処理中判定 */
  isTogglingSong: (songId: number) => boolean;
}

/** SongListHeaderPanel が受け取るプロパティ */
interface SongListHeaderPanelProps {
  /** 検索入力の現在値 */
  searchInput: string;
  /** 検索入力変更時の処理 */
  onSearchInputChange: (value: string) => void;
  /** 検索確定時の処理 */
  onSearchSubmit: (query: string) => void;
  /** アクティブな検索クエリ */
  activeQuery: string;
  /** ユーザー音域 */
  userRange?: UserRange | null;
  /** 五十音インデックス押下時の処理 */
  onIndexClick: (char: string) => void;
}

/**
 * PaginationSection が受け取るプロパティ
 */
interface PaginationSectionProps {
  /** 現在ページ（0-index） */
  currentPage: number;
  /** 総ページ数 */
  totalPages: number;
  /** 入力中ページ（1-index文字列） */
  pageInput: string;
  /** ページ入力更新 */
  onPageInputChange: (value: string) => void;
  /** ページング操作 */
  onPaginate: (action: PaginationAction) => void;
}

/**
 * 共通ページネーション表示セクション
 */
const PaginationSection: React.FC<PaginationSectionProps> = ({
  currentPage,
  totalPages,
  pageInput,
  onPageInputChange,
  onPaginate,
}) => {
  if (totalPages <= 1) {
    return null;
  }

  return (
    <Pagination
      currentPage={currentPage}
      totalPages={totalPages}
      pageInput={pageInput}
      onPageInputChange={onPageInputChange}
      onPrev={() => onPaginate("prev")}
      onNext={() => onPaginate("next")}
      onPageJump={() => onPaginate("jump")}
    />
  );
};

/**
 * 楽曲一覧ページのヘッダー領域を表示します。
 */
const SongListHeaderPanel: React.FC<SongListHeaderPanelProps> = ({
  searchInput,
  onSearchInputChange,
  onSearchSubmit,
  activeQuery,
  userRange,
  onIndexClick,
}) => {
  return (
    <div className="w-full max-w-3xl flex flex-col mb-4 gap-6">
      <SearchBar
        value={searchInput}
        onChange={onSearchInputChange}
        onSubmit={onSearchSubmit}
        placeholder="楽曲名・アーティスト名で検索..."
      />
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <h1 className="text-3xl sm:text-4xl font-black italic title-gradient-cyan-fuchsia mb-2 drop-shadow-[0_0_10px_rgba(34,211,238,0.3)] tracking-wider">
            {activeQuery ? "楽曲検索結果" : "ARTISTS"}
          </h1>
          <p className="text-xs text-slate-400 font-bold tracking-wide">
            {activeQuery
              ? `"${activeQuery}" の検索結果`
              : (userRange ? "音域に合わせたキーおすすめを表示中" : "録音すると、キーおすすめが表示されます")}
          </p>
        </div>
        <SyllableIndex
          onIndexClick={onIndexClick}
          visible={!activeQuery}
        />
      </div>
    </div>
  );
};

/**
 * 楽曲一覧のメイン表示を描画します。
 */
const SongListMainContent: React.FC<SongListMainContentProps> = ({
  searchInput,
  onSearchInputChange,
  onSearchSubmit,
  activeQuery,
  userRange,
  onIndexClick,
  error,
  searchSongs,
  searchPage,
  searchPageInput,
  onSearchPageInputChange,
  searchLoading,
  totalSearchPages,
  artists,
  artistPage,
  pageInput,
  onPageInputChange,
  loading,
  totalPages,
  onPaginate,
  onSelectArtist,
  onToggleFavoriteArtist,
  isFavoriteArtist,
  onToggleFavoriteSong,
  isFavoriteSong,
  isTogglingSong,
}) => {
  return (
    <>
      <SongListHeaderPanel
        searchInput={searchInput}
        onSearchInputChange={onSearchInputChange}
        onSearchSubmit={onSearchSubmit}
        activeQuery={activeQuery}
        userRange={userRange}
        onIndexClick={onIndexClick}
      />

      {error && <ErrorBanner message={error} className="max-w-3xl mb-4" />}

      {activeQuery ? (
        <>
          <SongTableWithLoading
            loading={searchLoading}
            songs={searchSongs}
            userRange={userRange}
            rowStartIndex={searchPage * SONGS_PER_PAGE}
            showArtistColumn={true}
            titleHeaderLabel="楽曲"
            onToggleFavoriteSong={onToggleFavoriteSong}
            isFavoriteSong={isFavoriteSong}
            isToggling={isTogglingSong}
            emptyMessage="該当する楽曲が見つかりません"
          />

          {!searchLoading && (
            <PaginationSection
              currentPage={searchPage}
              totalPages={totalSearchPages}
              pageInput={searchPageInput}
              onPageInputChange={onSearchPageInputChange}
              onPaginate={onPaginate}
            />
          )}
        </>
      ) : (
        <>
          {loading && <LoadingState />}

          <ArtistListPanel
            artists={artists}
            onSelectArtist={onSelectArtist}
            onToggleFavoriteArtist={onToggleFavoriteArtist}
            isFavorite={isFavoriteArtist}
          />

          {!loading && (
            <PaginationSection
              currentPage={artistPage}
              totalPages={totalPages}
              pageInput={pageInput}
              onPageInputChange={onPageInputChange}
              onPaginate={onPaginate}
            />
          )}
        </>
      )}
    </>
  );
};

export default SongListMainContent;
