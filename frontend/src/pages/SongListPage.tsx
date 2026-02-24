/**
 * 【SongListPage.tsx】
 * 役割：楽曲とアーティストの検索・一覧を表示する、アプリで最も多機能なページです。
 * 特徴：
 * 1. アーティスト名での絞り込み表示
 * 2. 楽曲名・アーティスト名でのキーワード検索（略称対応）
 * 3. 五十音インデックスによる高速ジャンプ
 * 4. ユーザーの音域に合わせた推奨キー（±0～±7）の表示
 */

import React, { useEffect, useState, useCallback } from 'react';
import { getArtists, getArtistSongs, Artist, UserRange, Song, getSongs, toUserMessage } from '../api';
import { StarIcon as StarSolid } from '@heroicons/react/24/solid';
import { StarIcon as StarOutline } from '@heroicons/react/24/outline';
import { HeartIcon } from '@heroicons/react/24/outline';
import { HeartIcon as HeartIconSolid } from '@heroicons/react/24/solid';
import { useToast } from '../hooks/useToast';
import { useFavoriteArtists } from '../hooks/useFavoriteArtists';
import { useFavoriteSongs } from '../hooks/useFavoriteSongs';
import ErrorBanner from '../components/ui/ErrorBanner';
import Toast from '../components/ui/Toast';
import Pagination from '../components/ui/Pagination';
import SearchBar from '../components/ui/SearchBar';
import SyllableIndex from '../components/ui/SyllableIndex';
import { keyBadge } from '../utils/keyBadge';
import { INDEX_KANA, getConsonantRow, SEARCH_ALIASES, ARTISTS_PER_PAGE, SONGS_PER_PAGE } from '../constants/songListConstants';

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

  // ── 検索クエリの状態 ──
  const [activeQuery, setActiveQuery] = useState(searchQuery);
  const [searchInput, setSearchInput] = useState(searchQuery);
  useEffect(() => {
    setActiveQuery(searchQuery);
    setSearchInput(searchQuery);
  }, [searchQuery]);

  // ── アーティスト一覧の状態 ──
  const [artists, setArtists] = useState<Artist[]>([]);
  const [totalArtists, setTotalArtists] = useState(0);
  const [artistPage, setArtistPage] = useState(0);
  const [pageInput, setPageInput] = useState("1");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ── 楽曲検索結果の状態 ──
  const [searchSongs, setSearchSongs] = useState<Song[]>([]);
  const [totalSearchSongs, setTotalSearchSongs] = useState(0);
  const [searchPage, setSearchPage] = useState(0);
  const [searchPageInput, setSearchPageInput] = useState("1");
  const [searchLoading, setSearchLoading] = useState(false);

  // ── 選択中のアーティスト詳細の状態 ──
  const [selectedArtist, setSelectedArtist] = useState<Artist | null>(null);
  const [artistSongs, setArtistSongs] = useState<Song[]>([]);
  const [songsLoading, setSongsLoading] = useState(false);

  // ── お気に入り管理 ──
  const { favoriteIds, toggleFavorite: toggleFavoriteArtist, isFavorite } = useFavoriteArtists(); // アーティスト
  const { favoriteSongIds, toggleFavoriteSong, isFavoriteSong, isToggling } = useFavoriteSongs(onLoginClick); // 楽曲
  const { toastMessage, showToast, hideToast } = useToast();

  /** ── アーティスト一覧取得 ──
   * 指定されたページのアーティストデータをサーバーから取得します。
   */
  const fetchArtists = useCallback(async (page: number) => {
    setLoading(true);
    try {
      // 検索クエリを略称辞書で変換（ヒットしなければそのまま使用）
      const effectiveQuery = SEARCH_ALIASES[activeQuery] || activeQuery;
      const data = await getArtists(ARTISTS_PER_PAGE, page * ARTISTS_PER_PAGE, effectiveQuery);
      setArtists(data.artists);
      setTotalArtists(data.total);
      setError(null);
    } catch (err: any) {
      setError("\u697d\u66f2\u306e\u53d6\u5f97\u306b\u5931\u6557\u3057\u307e\u3057\u305f");
    } finally {
      setLoading(false);
    }
  }, [activeQuery]);

  /** ── 楽曲検索 ──
   * 入力されたキーワードに基づいて、おすすめキーを含めた楽曲一覧を取得します。
   */
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
    } catch (err: any) {
      setError("\u697d\u66f2\u691c\u7d22\u306b\u5931\u6557\u3057\u307e\u3057\u305f");
      setSearchSongs([]);
      setTotalSearchSongs(0);
    } finally {
      setSearchLoading(false);
    }
  }, [activeQuery, userRange]);

  // 検索クエリが変わったらページをリセット
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

  // ページ変更時にアーティスト情報を取得
  useEffect(() => {
    if (!activeQuery) {
      fetchArtists(artistPage);
      setPageInput((artistPage + 1).toString());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [artistPage, activeQuery]);

  // ページ変更時に楽曲検索結果を取得
  useEffect(() => {
    if (activeQuery) {
      fetchSearchSongs(searchPage);
      setSearchPageInput((searchPage + 1).toString());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchPage, activeQuery]);


  /** ── アーティスト選択時の楽曲取得 ── */
  const handleSelectArtist = useCallback(async (artist: Artist) => {
    setSelectedArtist(artist);
    setSongsLoading(true);
    try {
      const songs = await getArtistSongs(artist.id, userRange);
      setArtistSongs(songs);
    } catch (err) {
      console.error("\u697d\u66f2\u53d6\u5f97\u5931\u6557:", err);
      setArtistSongs([]);
      showToast(toUserMessage(err, "アーティストの楽曲取得に失敗しました。"));
    } finally {
      setSongsLoading(false);
    }
  }, [userRange]);

  const totalPages = Math.ceil(totalArtists / ARTISTS_PER_PAGE);
  const totalSearchPages = Math.ceil(totalSearchSongs / SONGS_PER_PAGE);

  // ページ移動：次へ
  const handleNext = () => {
    if (activeQuery) {
      if (searchPage + 1 < totalSearchPages) setSearchPage(p => p + 1);
    } else {
      if (artistPage + 1 < totalPages) setArtistPage(p => p + 1);
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // ページ移動：前へ
  const handlePrev = () => {
    if (activeQuery) {
      if (searchPage > 0) setSearchPage(p => p - 1);
    } else {
      if (artistPage > 0) setArtistPage(p => p - 1);
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // 指定ページへジャンプ
  const handlePageJump = () => {
    if (activeQuery) {
      let p = parseInt(searchPageInput, 10);
      if (isNaN(p)) { setSearchPageInput((searchPage + 1).toString()); return; }
      if (p < 1) p = 1; if (p > totalSearchPages) p = totalSearchPages;
      setSearchPage(p - 1); setSearchPageInput(p.toString());
    } else {
      let p = parseInt(pageInput, 10);
      if (isNaN(p)) { setPageInput((artistPage + 1).toString()); return; }
      if (p < 1) p = 1; if (p > totalPages) p = totalPages;
      setArtistPage(p - 1); setPageInput(p.toString());
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  /** ── インデックスジャンプ ──
   * 五十音順（あ、か、さ...）に基づいて、目的のページを二分探索で見つけ出します。
   */
  const handleIndexJump = useCallback(async (char: string) => {
    const targetRow = INDEX_KANA.indexOf(char);
    if (targetRow === -1 || totalArtists === 0) return;

    // 現在表示中のページにあればスクロール
    const indexInPage = artists.findIndex(a => getConsonantRow(a.reading || "") >= targetRow);
    if (indexInPage !== -1 && getConsonantRow(artists[indexInPage].reading || "") === targetRow) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    setLoading(true);
    try {
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

      setArtistPage(found);
      setPageInput((found + 1).toString());
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err) {
      console.error('Index jump failed', err);
      showToast(toUserMessage(err, "インデックス移動に失敗しました。"));
    } finally {
      setLoading(false);
    }
  }, [artists, totalArtists, totalPages]);

  // ── 描画：アーティスト別の楽曲一覧 ──
  if (selectedArtist) {
    return (
      <div className="flex flex-col items-center min-h-[calc(100vh-80px)] bg-transparent p-4 sm:p-8">
        <div className="w-full max-w-5xl mb-6">
          <button
            onClick={() => setSelectedArtist(null)}
            className="btn-back-link transition-all duration-300 mb-6 drop-shadow-[0_0_5px_rgba(34,211,238,0)] hover:drop-shadow-[0_0_8px_rgba(34,211,238,0.5)]"
          >
            &larr; アーティスト一覧に戻る
          </button>
          <div className="flex items-center gap-6">
            <div className="relative w-16 h-16 bg-slate-900 rounded-full flex items-center justify-center text-cyan-400 text-2xl font-bold border-2 border-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.6)]">
              {selectedArtist.name.charAt(0)}
            </div>
            <div>
              <h1 className="text-3xl sm:text-4xl font-black italic title-gradient-cyan-fuchsia drop-shadow-[0_0_10px_rgba(34,211,238,0.3)] tracking-wider">
                {selectedArtist.name}
              </h1>
              <p className="text-sm text-cyan-400 mt-1 font-bold tracking-widest">{artistSongs.length}{'\u66f2'}</p>
            </div>
          </div>
        </div>

        {songsLoading ? (
          <p className="mt-6 text-slate-500">{'\u8aad\u307f\u8fbc\u307f\u4e2d...'}</p>
        ) : (
          <div className="table-container">
            <table className="w-full text-left">
              <thead>
                <tr className="table-header">
                  <th className="py-3 px-5 font-medium">#</th>
                  <th className="py-3 px-4 font-medium">Title</th>
                  <th className="py-3 px-4 font-medium">Lowest</th>
                  <th className="py-3 px-4 font-medium">Highest</th>
                  <th className="py-3 px-4 font-medium hidden sm:table-cell">Falsetto</th>
                  {userRange && <th className="py-3 px-4 font-medium text-center">Key</th>}
                  <th className="py-3 px-2 font-medium w-10"></th>
                </tr>
              </thead>
              <tbody>
                {artistSongs.map((song, i) => (
                  <tr key={song.id} className="table-row group">
                    <td className="py-3 px-5 text-slate-500 text-xs">{i + 1}</td>
                    <td className="py-3 px-4 font-medium">
                      <a
                        href={`https://www.google.com/search?q=${encodeURIComponent(`${selectedArtist.name} ${song.title} 歌詞`)}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-slate-200 hover:text-cyan-400 transition-colors inline-flex items-center gap-1 group/link"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {song.title}
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3 h-3 text-slate-500 group-hover/link:text-cyan-400 transition-colors">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                        </svg>
                      </a>
                    </td>
                    <td className="py-3 px-4 text-slate-400 whitespace-nowrap">{song.lowest_note || '-'}</td>
                    <td className="py-3 px-4 text-slate-400 whitespace-nowrap">{song.highest_note || '-'}</td>
                    <td className="py-3 px-4 text-slate-400 whitespace-nowrap hidden sm:table-cell">{song.falsetto_note || '-'}</td>
                    {userRange && (
                      <td className="py-3 px-4 text-center">
                        {song.recommended_key !== undefined
                          ? keyBadge(song.recommended_key, song.fit)
                          : <span className="text-slate-600">-</span>}
                      </td>
                    )}
                    <td className="py-3 px-2 text-center">
                      <button
                        onClick={(e) => { e.stopPropagation(); toggleFavoriteSong(song.id); }}
                        disabled={isToggling(song.id)}
                        className="p-1 rounded-full hover:bg-white/10 transition-colors disabled:opacity-50"
                      >
                        {isFavoriteSong(song.id)
                          ? <HeartIconSolid className="w-5 h-5 text-rose-500" />
                          : <HeartIcon className="w-5 h-5 text-slate-500 hover:text-rose-400" />}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  }

  // ── 描画：メインの検索・一覧画面 ──
  return (
    <div className="flex flex-col items-center min-h-[calc(100vh-80px)] bg-transparent p-4 sm:p-8">
      {toastMessage && <Toast message={toastMessage} onClose={hideToast} />}

      <div className="w-full max-w-3xl flex flex-col mb-4 gap-6">
        <SearchBar
          value={searchInput}
          onChange={setSearchInput}
          onSubmit={(query) => {
            setActiveQuery(query);
            if (onSearchChange) {
              onSearchChange(query);
            }
          }}
          placeholder="楽曲名・アーティスト名で検索..."
        />
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h1 className="text-3xl sm:text-4xl font-black italic title-gradient-cyan-fuchsia mb-2 drop-shadow-[0_0_10px_rgba(34,211,238,0.3)] tracking-wider">
              {activeQuery ? '楽曲検索結果' : 'ARTISTS'}
            </h1>
            <p className="text-xs text-slate-400 font-bold tracking-wide">
              {activeQuery
                ? `"${activeQuery}" の検索結果`
                : (userRange ? "音域に合わせたキーおすすめを表示中" : "録音すると、キーおすすめが表示されます")
              }
            </p>
          </div>
          <SyllableIndex
            onIndexClick={handleIndexJump}
            visible={!activeQuery}
          />
        </div>
      </div>

      {error && <ErrorBanner message={error} className="max-w-3xl mb-4" />}

      {activeQuery ? (
        // ── 描画：キーワード検索結果 ──
        <>
          {searchLoading ? (
            <p className="mt-6 text-slate-500">{'読み込み中...'}</p>
          ) : searchSongs.length === 0 ? (
            <p className="mt-6 text-slate-400 text-center">該当する楽曲が見つかりません</p>
          ) : (
            <div className="table-container">
              <table className="w-full text-left">
                <thead>
                  <tr className="table-header">
                    <th className="py-3 px-5 font-medium">#</th>
                    <th className="py-3 px-4 font-medium">楽曲</th>
                    <th className="py-3 px-4 font-medium">アーティスト</th>
                    <th className="py-3 px-4 font-medium">Lowest</th>
                    <th className="py-3 px-4 font-medium">Highest</th>
                    <th className="py-3 px-4 font-medium hidden sm:table-cell">Falsetto</th>
                    {userRange && <th className="py-3 px-4 font-medium text-center">Key</th>}
                    <th className="py-3 px-2 font-medium w-10"></th>
                  </tr>
                </thead>
                <tbody>
                  {searchSongs.map((song, i) => (
                    <tr key={song.id} className="table-row group">
                      <td className="py-3 px-5 text-slate-500 text-xs">{searchPage * SONGS_PER_PAGE + i + 1}</td>
                      <td className="py-3 px-4 font-medium">
                        <a
                          href={`https://www.google.com/search?q=${encodeURIComponent(`${song.artist} ${song.title} 歌詞`)}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-slate-200 hover:text-cyan-400 transition-colors inline-flex items-center gap-1 group/link"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {song.title}
                          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3 h-3 text-slate-500 group-hover/link:text-cyan-400 transition-colors">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                          </svg>
                        </a>
                      </td>
                      <td className="py-3 px-4 text-slate-400 whitespace-nowrap">{song.artist}</td>
                      <td className="py-3 px-4 text-slate-400 whitespace-nowrap">{song.lowest_note || '-'}</td>
                      <td className="py-3 px-4 text-slate-400 whitespace-nowrap">{song.highest_note || '-'}</td>
                      <td className="py-3 px-4 text-slate-400 whitespace-nowrap hidden sm:table-cell">{song.falsetto_note || '-'}</td>
                      {userRange && (
                        <td className="py-3 px-4 text-center">
                          {song.recommended_key !== undefined
                            ? keyBadge(song.recommended_key, song.fit)
                            : <span className="text-slate-600">-</span>}
                        </td>
                      )}
                      <td className="py-3 px-2 text-center">
                        <button
                          onClick={(e) => { e.stopPropagation(); toggleFavoriteSong(song.id); }}
                          disabled={isToggling(song.id)}
                          className="p-1 rounded-full hover:bg-white/10 transition-colors disabled:opacity-50"
                        >
                          {isFavoriteSong(song.id)
                            ? <HeartIconSolid className="w-5 h-5 text-rose-500" />
                            : <HeartIcon className="w-5 h-5 text-slate-500 hover:text-rose-400" />}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* 検索結果のページネーション */}
          {!searchLoading && totalSearchSongs > SONGS_PER_PAGE && (
            <Pagination
              currentPage={searchPage}
              totalPages={totalSearchPages}
              pageInput={searchPageInput}
              onPageInputChange={setSearchPageInput}
              onPrev={handlePrev}
              onNext={handleNext}
              onPageJump={handlePageJump}
            />
          )}
        </>
      ) : (
        // ── 描画：アーティスト一覧 ──
        <>
          {loading && <p className="mt-6 text-slate-500">{'読み込み中...'}</p>}

          <div className="w-full max-w-3xl bg-slate-900/60 backdrop-blur-md rounded-xl shadow-[0_0_20px_rgba(0,0,0,0.5)] border border-cyan-500/20 overflow-hidden">
            {artists.map((artist) => (
              <div key={artist.id} className="group relative flex items-center w-full border-b border-cyan-500/10 last:border-0 hover:bg-cyan-900/20 transition-all duration-300">
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-cyan-400 opacity-0 group-hover:opacity-100 shadow-[0_0_10px_rgba(34,211,238,1)] transition-opacity duration-300"></div>
                <button
                  onClick={() => handleSelectArtist(artist)}
                  className="flex-1 flex items-center justify-between p-4 pl-6 text-left"
                >
                  <div className="flex items-center gap-4">
                    <div className="relative w-10 h-10 bg-slate-900 rounded-full flex items-center justify-center text-cyan-400 font-bold text-sm border-2 border-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.5)] group-hover:shadow-[0_0_15px_rgba(34,211,238,0.8)] transition-all duration-300">
                      {artist.name.charAt(0)}
                    </div>
                    <p className="font-bold text-slate-200 group-hover:text-cyan-400 transition-colors drop-shadow-[0_0_5px_rgba(34,211,238,0)] group-hover:drop-shadow-[0_0_5px_rgba(34,211,238,0.5)]">{artist.name}</p>
                  </div>
                  <span className="text-xs text-cyan-400 bg-slate-900/80 px-3 py-1 rounded-sm border border-cyan-500/30 shadow-[0_0_5px_rgba(34,211,238,0.2)]">{artist.song_count}{'\u66f2'}</span>
                </button>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleFavoriteArtist(artist.id, artist.name);
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

          {/* アーティスト一覧のページネーション */}
          {!loading && totalArtists > ARTISTS_PER_PAGE && (
            <Pagination
              currentPage={artistPage}
              totalPages={totalPages}
              pageInput={pageInput}
              onPageInputChange={setPageInput}
              onPrev={handlePrev}
              onNext={handleNext}
              onPageJump={handlePageJump}
            />
          )}
        </>
      )}
    </div>
  );
};

export default SongListPage;