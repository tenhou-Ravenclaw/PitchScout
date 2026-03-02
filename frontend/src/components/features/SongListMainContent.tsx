/**
 * 【SongListMainContent.tsx】
 * 役割：楽曲一覧ページのメイン表示（検索結果 / アーティスト一覧）を担当するビューコンポーネントです。
 * 特徴：ヘッダー、エラー表示、検索結果表示、一覧表示、ページネーションを集約します。
 */

import React from "react";
import { Artist, Song, UserRange } from "../../api";
import ErrorBanner from "../ui/ErrorBanner";
import LoadingState from "../ui/LoadingState";
import PageNav from "../ui/PageNav";
import ArtistListPanel from "./ArtistListPanel";
import SongListHeaderPanel from "./SongListHeaderPanel";
import SongTable from "./SongTable";
import { SONGS_PER_PAGE } from "../../constants/songListConstants";
import { PageAction } from "../../hooks/useSongListData";

/**
 * SongListMainContent が受け取るプロパティ
 */
interface SongListMainContentProps {
  /** 検索入力値 */
  searchInput: string;
  /** 検索入力変更 */
  onSearchInputChange: (value: string) => void;
  /** 検索実行 */
  onSearchSubmit: (query: string) => void;
  /** 現在の検索クエリ */
  activeQuery: string;
  /** ユーザー声域 */
  userRange?: UserRange | null;
  /** インデックスジャンプ */
  onIndexClick: (char: string) => Promise<void>;
  /** エラー文 */
  error: string | null;
  /** 検索結果楽曲 */
  searchSongs: Song[];
  /** 検索ページ番号 */
  searchPage: number;
  /** 検索ページ入力値 */
  searchPageInput: string;
  /** 検索ページ入力変更 */
  onSearchPageInputChange: (value: string) => void;
  /** 検索中フラグ */
  searchLoading: boolean;
  /** 検索ページ総数 */
  totalSearchPages: number;
  /** アーティスト一覧 */
  artists: Artist[];
  /** アーティストページ番号 */
  artistPage: number;
  /** ページ入力値 */
  pageInput: string;
  /** ページ入力変更 */
  onPageInputChange: (value: string) => void;
  /** ローディングフラグ */
  loading: boolean;
  /** ページ総数 */
  totalPages: number;
  /** ページング操作 */
  onPaginate: (action: PageAction) => void;
  /** アーティスト選択 */
  onSelectArtist: (artist: Artist) => void;
  /** お気に入りアーティスト切替 */
  onToggleFavoriteArtist: (artistId: number, artistName: string) => Promise<void>;
  /** お気に入りアーティスト判定 */
  isFavoriteArtist: (artistId: number, artistName: string) => boolean;
  /** お気に入り楽曲切替 */
  onToggleFavoriteSong: (id: number) => void;
  /** お気に入り楽曲判定 */
  isFavoriteSong: (id: number) => boolean;
  /** 楽曲お気に入り切替中判定 */
  isTogglingSong: (id: number) => boolean;
  /** ヘッダーを非表示にする（親要素で表示する場合など） */
  hideHeader?: boolean;
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
  onPaginate: (action: PageAction) => void;
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
    <PageNav
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
  hideHeader,
}) => {
  return (
    <>
      {!hideHeader && (
        <SongListHeaderPanel
          searchInput={searchInput}
          onSearchInputChange={onSearchInputChange}
          onSearchSubmit={onSearchSubmit}
          activeQuery={activeQuery}
          userRange={userRange}
          onIndexClick={onIndexClick}
        />
      )}

      {error && <ErrorBanner message={error} className="max-w-3xl mb-4" />}

      {activeQuery ? (
        <>
          {searchLoading ? (
            <LoadingState />
          ) : searchSongs.length === 0 ? (
            <p className="mt-6 text-slate-400 text-center">該当する楽曲が見つかりません</p>
          ) : (
            <SongTable
              songs={searchSongs}
              userRange={userRange}
              rowStartIndex={searchPage * SONGS_PER_PAGE}
              showArtistColumn={true}
              titleHeaderLabel="楽曲"
              onToggleFavoriteSong={onToggleFavoriteSong}
              isFavoriteSong={isFavoriteSong}
              isToggling={isTogglingSong}
            />
          )}

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
            isFavorite={artistId => isFavoriteArtist(artistId, artists.find(a => a.id === artistId)?.name ?? "")}
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
