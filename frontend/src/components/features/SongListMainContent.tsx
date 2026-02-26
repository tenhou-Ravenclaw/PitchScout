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
import { SongTableWithLoading } from "./SongTable";
import {
  ARTISTS_PER_PAGE,
  SONGS_PER_PAGE,
} from "../../constants/songListConstants";
import { PaginationAction } from "../../hooks/useSongListData";
import { StarIcon as StarSolid } from "@heroicons/react/24/solid";
import { StarIcon as StarOutline } from "@heroicons/react/24/outline";

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

/** ArtistListPanel が受け取るプロパティ */
interface ArtistListPanelProps {
  /** 表示対象のアーティスト一覧 */
  artists: Artist[];
  /** アーティスト選択時の処理 */
  onSelectArtist: (artist: Artist) => void;
  /** お気に入りトグル時の処理 */
  onToggleFavoriteArtist: (artistId: number, artistName: string) => void;
  /** お気に入り判定 */
  isFavorite: (artistId: number) => boolean;
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
              : userRange
                ? "音域に合わせたキーおすすめを表示中"
                : "録音すると、キーおすすめが表示されます"}
          </p>
        </div>
        <SyllableIndex onIndexClick={onIndexClick} visible={!activeQuery} />
      </div>
    </div>
  );
};

/**
 * アーティスト一覧を表示します。
 */
const ArtistListPanel: React.FC<ArtistListPanelProps> = ({
  artists,
  onSelectArtist,
  onToggleFavoriteArtist,
  isFavorite,
}) => {
  return (
    <div className="w-full max-w-3xl bg-slate-900/60 backdrop-blur-md rounded-xl shadow-[0_0_20px_rgba(0,0,0,0.5)] border border-cyan-500/20 overflow-hidden">
      {artists.map((artist) => (
        <div
          key={artist.id}
          className="group relative flex items-center w-full border-b border-cyan-500/10 last:border-0 hover:bg-cyan-900/20 transition-all duration-300"
        >
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-cyan-400 opacity-0 group-hover:opacity-100 shadow-[0_0_10px_rgba(34,211,238,1)] transition-opacity duration-300"></div>
          <button
            onClick={() => onSelectArtist(artist)}
            className="flex-1 flex items-center justify-between p-4 pl-6 text-left"
          >
            <div className="flex items-center gap-4">
              <div className="relative w-10 h-10 bg-slate-900 rounded-full flex items-center justify-center text-cyan-400 font-bold text-sm border-2 border-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.5)] group-hover:shadow-[0_0_15px_rgba(34,211,238,0.8)] transition-all duration-300">
                {artist.name.charAt(0)}
              </div>
              <p className="font-bold text-slate-200 group-hover:text-cyan-400 transition-colors drop-shadow-[0_0_5px_rgba(34,211,238,0)] group-hover:drop-shadow-[0_0_5px_rgba(34,211,238,0.5)]">
                {artist.name}
              </p>
            </div>
            <span className="text-xs text-cyan-400 bg-slate-900/80 px-3 py-1 rounded-sm border border-cyan-500/30 shadow-[0_0_5px_rgba(34,211,238,0.2)]">
              {artist.song_count}
              {"曲"}
            </span>
          </button>

          <button
            onClick={(event) => {
              event.stopPropagation();
              onToggleFavoriteArtist(artist.id, artist.name);
            }}
            className="p-4 pr-6 transition-transform hover:scale-125 z-10"
          >
            {isFavorite(artist.id) ? (
              <StarSolid className="w-6 h-6 text-amber-400 drop-shadow-[0_0_8px_rgba(250,204,21,0.8)]" />
            ) : (
              <StarOutline className="w-6 h-6 text-slate-500 hover:text-cyan-400 transition-colors" />
            )}
          </button>
        </div>
      ))}
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
