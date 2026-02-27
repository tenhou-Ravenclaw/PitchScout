/**
 * 【SongListPage.tsx】
 * 役割：楽曲とアーティストの検索・一覧を表示する、アプリで最も多機能なページです。
 * 特徴：
 * 1. アーティスト名での絞り込み表示
 * 2. 楽曲名・アーティスト名でのキーワード検索（略称対応）
 * 3. 五十音インデックスによる高速ジャンプ
 * 4. ユーザーの音域に合わせた推奨キー（±0～±7）の表示
 */

import React from 'react';
import { UserRange } from '../api';
import { useToast } from '../hooks/useToast';
import { useFavoriteArtists } from '../hooks/useFavoriteArtists';
import { useFavoriteSongs } from '../hooks/useFavoriteSongs';
import { useSongListData } from '../hooks/useSongListData';
import Toast from '../components/ui/Toast';
import SongListArtistSongsView from '../components/features/SongListArtistSongsView';
import SongListMainContent from '../components/features/SongListMainContent';
import SongListHeaderPanel from '../components/features/SongListHeaderPanel';

/**
 * ── 以下、定数とヘルパーは constants/songListConstants.ts に移動しました ──
 */

/** SongListPage が受け取るプロパティ */
interface SongListPageProps {
  /** 検索クエリ */
  searchQuery?: string;
  /** ユーザー音域 */
  userRange?: UserRange | null;
  /** ログイン誘導時の処理 */
  onLoginClick?: () => void;
  /** 検索クエリ変更時の処理 */
  onSearchChange?: (query: string) => void;
}

const SongListPage: React.FC<SongListPageProps> = ({ searchQuery = "", userRange, onLoginClick, onSearchChange }) => {
  // ── お気に入り管理 ──
  const { toggleFavorite: toggleFavoriteArtist, isFavorite } = useFavoriteArtists(); // アーティスト
  const { toggleFavoriteSong, isFavoriteSong, isToggling } = useFavoriteSongs(onLoginClick); // 楽曲
  const { toastMessage, showToast, hideToast } = useToast();

  const {
    activeQuery,
    searchInput,
    setSearchInput,
    artists,
    artistPage,
    pageInput,
    setPageInput,
    loading,
    error,
    searchSongs,
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
    handlePaginate,
    handleIndexJump,
  } = useSongListData({
    initialQuery: searchQuery,
    userRange,
    notifyError: showToast,
    onSearchChange,
  });


  // ── 描画：メインの検索・一覧画面 ──
  return (
    <div className="flex flex-col items-center min-h-[calc(100vh-80px)] bg-transparent p-4 sm:p-8">
      {toastMessage && <Toast message={toastMessage} onClose={hideToast} />}

      {/* 描画：アーティスト別の楽曲一覧 or メインコンテンツ */}
      {selectedArtist ? (
        <SongListArtistSongsView
          artistName={selectedArtist.name}
          artistSongs={artistSongs}
          songsLoading={songsLoading}
          userRange={userRange}
          onBack={closeSelectedArtist}
          onToggleFavoriteSong={toggleFavoriteSong}
          isFavoriteSong={isFavoriteSong}
          isToggling={isToggling}
        />
      ) : (
        <>
          {/* ヘッダーパネル（検索バー、タイトル、インデックス）はアーティスト未選択時のみ表示する */}
          <SongListHeaderPanel
            searchInput={searchInput}
            onSearchInputChange={setSearchInput}
            onSearchSubmit={handleSearchSubmit}
            activeQuery={activeQuery}
            userRange={userRange}
            onIndexClick={handleIndexJump}
          />

          <SongListMainContent
            searchInput={searchInput}
            onSearchInputChange={setSearchInput}
            onSearchSubmit={handleSearchSubmit}
            activeQuery={activeQuery}
            userRange={userRange}
            onIndexClick={handleIndexJump}
            error={error}
            searchSongs={searchSongs}
            searchPage={searchPage}
            searchPageInput={searchPageInput}
            onSearchPageInputChange={setSearchPageInput}
            searchLoading={searchLoading}
            totalSearchPages={totalSearchPages}
            artists={artists}
            artistPage={artistPage}
            pageInput={pageInput}
            onPageInputChange={setPageInput}
            loading={loading}
            totalPages={totalPages}
            onPaginate={handlePaginate}
            onSelectArtist={handleSelectArtist}
            onToggleFavoriteArtist={toggleFavoriteArtist}
            isFavoriteArtist={isFavorite}
            onToggleFavoriteSong={toggleFavoriteSong}
            isFavoriteSong={isFavoriteSong}
            isTogglingSong={isToggling}
            hideHeader={true} // SongListMainContent 側のヘッダーを非表示にする
          />
        </>
      )}
    </div>
  );
};

export default SongListPage;