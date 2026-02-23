/**
 * 【SongListPage.tsx】
 * 役割：楽曲検索、五十音順のアーティスト一覧、お気に入り登録など、
 * ユーザーが歌いたい曲を探すための主要な画面です。
 * * 💡 将来的な改善案（FRONTEND_STRUCTURE.md より）:
 * 1. 移動先: src/features/songs/pages/SongListPage.tsx
 * 2. 巨大な「SEARCH_ALIASES（辞書）」は外部ファイルへ切り出す
 * 3. 楽曲テーブル（SongTable）などをコンポーネントとして独立させ、コード量を減らす
 */

import React, { useEffect, useState, useCallback } from 'react';
// API通信用の道具をインポート
import { 
  getArtists, 
  getArtistSongs, 
  Artist, 
  UserRange, 
  getFavoriteArtists, 
  addFavoriteArtist, 
  removeFavoriteArtist, 
  getFavorites, 
  addFavorite, 
  removeFavorite, 
  Song, 
  getSongs 
} from './api';
// アイコン素材
import { StarIcon as StarSolid } from '@heroicons/react/24/solid';
import { StarIcon as StarOutline, MagnifyingGlassIcon } from '@heroicons/react/24/outline';
import { HeartIcon } from '@heroicons/react/24/outline';
import { HeartIcon as HeartIconSolid } from '@heroicons/react/24/solid';
import { useAuth } from './contexts/AuthContext';

/**
 * ── ヘルパー部品：キーバッジ ──
 * 曲のキー（±0など）を色付きで表示します。
 * 💡 移動先案: src/components/ui/KeyBadge.tsx
 */
const keyBadge = (key: number, fit?: string) => {
  const label = key === 0 ? "\u00b10" : key > 0 ? `+${key}` : `${key}`;
  let color: string;
  // おすすめ度（fit）によって色を変更
  if (fit === "perfect") color = "bg-emerald-900/30 text-emerald-400 border border-emerald-500/30";
  else if (fit === "good") color = "bg-sky-900/30 text-sky-400 border border-sky-500/30";
  else if (fit === "ok") color = "bg-amber-900/30 text-amber-400 border border-amber-500/30";
  else if (fit === "hard") color = "bg-rose-900/30 text-rose-400 border border-rose-500/30";
  else color = "bg-slate-800 text-slate-500 border border-slate-700";
  return (
    <span className={`inline-flex items-center justify-center min-w-[2.5rem] h-6 rounded-full text-xs font-bold ${color}`}>
      {label}
    </span>
  );
};

// 五十音順ジャンプ用の配列
const INDEX_KANA = ['\u3042', '\u304b', '\u3055', '\u305f', '\u306a', '\u306f', '\u307e', '\u3084', '\u3089', '\u308f'];

/**
 * ── ヘルパー関数：読みから「行」を判定 ──
 * 「あいうえお」のどの行に属するかを数字で返します。
 */
const getConsonantRow = (reading: string): number => {
  if (!reading) return 99;
  let code = reading.codePointAt(0) ?? 0;
  // カタカナをひらがなに変換
  if (code >= 0x30A1 && code <= 0x30F6) code -= 0x60;
  if (code >= 0x3041 && code <= 0x3093) {
    if (code <= 0x304A) return 0; // あ
    if (code <= 0x3054) return 1; // か
    if (code <= 0x305E) return 2; // さ
    if (code <= 0x3069) return 3; // た
    if (code <= 0x306E) return 4; // な
    if (code <= 0x307D) return 5; // は
    if (code <= 0x3082) return 6; // ま
    if (code <= 0x3088) return 7; // や
    if (code <= 0x308D) return 8; // ら
    return 9; // わ
  }
  return 99;
};

/**
 * ── 検索エイリアス（略称辞書） ──
 * 💡 移動先案: src/constants/searchAliases.ts
 * ユーザーが「ミセス」と打っても「Mrs. GREEN APPLE」を検索できるようにします。
 */
const SEARCH_ALIASES: Record<string, string> = {
  "ミセス": "Mrs. GREEN APPLE",
  "みせす": "Mrs. GREEN APPLE",
  "ヒゲダン": "Official髭男dism",
  "ひげだん": "Official髭男dism",
  "ワンオク": "ONE OK ROCK",
  "わんおく": "ONE OK ROCK",
  "バウンディ": "Vaundy",
  "ばうんでぃ": "Vaundy",
  "キングヌー": "King Gnu",
  "きんぐぬー": "King Gnu",
  "ヌー": "King Gnu",
  "ヨアソビ": "YOASOBI",
  "よあそび": "YOASOBI",
  "セカオワ": "SEKAI NO OWARI",
  "せかおわ": "SEKAI NO OWARI",
  "ラッド": "RADWIMPS",
  "らっど": "RADWIMPS",
  "ヨルシカ": "ヨルシカ",
  "ずとまよ": "ずっと真夜中でいいのに。",
  "ズトマヨ": "ずっと真夜中でいいのに。",
  "マカエン": "マカロニえんぴつ",
  "まかえん": "マカロニえんぴつ",
  "サウシー": "Saucy Dog",
  "さうしー": "Saucy Dog",
  "リョクシャカ": "緑黄色社会",
  "りょくしゃか": "緑黄色社会",
  "マイヘア": "My Hair is Bad",
  "まいへあ": "My Hair is Bad",
  "ノベブラ": "Novelbright",
  "ノーベル": "Novelbright",
  "ビーファ": "BE:FIRST",
  "びーふぁ": "BE:FIRST",
  "アド": "Ado",
  "あど": "Ado",
  "ユーリ": "優里",
  "ゆうり": "優里",
  "ミスチル": "Mr.Children",
  "みすちる": "Mr.Children",
  "ポルノ": "ポルノグラフィティ",
  "バンプ": "BUMP OF CHICKEN",
  "アジカン": "ASIAN KUNG-FU GENERATION",
  "エルレ": "ELLEGARDEN",
  "ウーバー": "UVERworld",
  "ラルク": "L'Arc~en~Ciel",
  "ブルハ": "THE BLUE HEARTS",
  "モンパチ": "MONGOL800",
  "ドロス": "![Alexandros]",
  "アレキ": "![Alexandros]",
  "スピッツ": "スピッツ",
  "源さん": "星野源"
};

const ARTISTS_PER_PAGE = 10;
const SONGS_PER_PAGE = 10;

const SongListPage: React.FC<{
  searchQuery?: string;     // URL等から渡される検索語
  userRange?: UserRange | null; // 解析済みの音域データ
  onLoginClick?: () => void;
  onSearchChange?: (query: string) => void;
}> = ({ searchQuery = "", userRange, onLoginClick, onSearchChange }) => {
  const { isAuthenticated } = useAuth();

  // ── 状態管理 (State) ──
  const [activeQuery, setActiveQuery] = useState(searchQuery); // 実際に検索に使っている語
  const [searchInput, setSearchInput] = useState(searchQuery); // 入力中の文字
  
  // アーティスト一覧データ
  const [artists, setArtists] = useState<Artist[]>([]);
  const [totalArtists, setTotalArtists] = useState(0);
  const [artistPage, setArtistPage] = useState(0);
  const [pageInput, setPageInput] = useState("1");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 楽曲検索結果データ
  const [searchSongs, setSearchSongs] = useState<Song[]>([]);
  const [totalSearchSongs, setTotalSearchSongs] = useState(0);
  const [searchPage, setSearchPage] = useState(0);
  const [searchPageInput, setSearchPageInput] = useState("1");
  const [searchLoading, setSearchLoading] = useState(false);

  // アーティスト詳細表示
  const [selectedArtist, setSelectedArtist] = useState<Artist | null>(null);
  const [artistSongs, setArtistSongs] = useState<Song[]>([]);
  const [songsLoading, setSongsLoading] = useState(false);

  // お気に入りIDのセット
  const [favoriteIds, setFavoriteIds] = useState<number[]>([]);
  const [favoriteSongIds, setFavoriteSongIds] = useState<Set<number>>(new Set());
  const [togglingIds, setTogglingIds] = useState<Set<number>>(new Set());

  // ── データ取得関数 ──

  /** アーティスト一覧を取得 */
  const fetchArtists = useCallback(async (page: number) => {
    setLoading(true);
    try {
      // 略称があれば変換、なければそのまま使用
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

  /** 特定のキーワードで曲を検索 */
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
    } finally {
      setSearchLoading(false);
    }
  }, [activeQuery, userRange]);

  // ── 副作用 (Effects) ──

  // 検索語が変わったらページを1枚目に戻す
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

  // アーティスト一覧の読み込み
  useEffect(() => {
    if (!activeQuery) fetchArtists(artistPage);
  }, [artistPage, activeQuery, fetchArtists]);

  // 楽曲検索結果の読み込み
  useEffect(() => {
    if (activeQuery) fetchSearchSongs(searchPage);
  }, [searchPage, activeQuery, fetchSearchSongs]);

  // 初期化時にお気に入り情報を取得
  useEffect(() => {
    getFavoriteArtists().then(favs => setFavoriteIds(favs.map(f => f.artist_id)));
    if (isAuthenticated) {
      getFavorites(500).then(favs => setFavoriteSongIds(new Set(favs.map(f => f.song_id))));
    }
  }, [isAuthenticated]);

  // ── イベント操作 ──

  /** アーティストをクリックした時にその人の曲を表示 */
  const handleSelectArtist = useCallback(async (artist: Artist) => {
    setSelectedArtist(artist);
    setSongsLoading(true);
    try {
      const songs = await getArtistSongs(artist.id, userRange);
      setArtistSongs(songs);
    } finally {
      setSongsLoading(false);
    }
  }, [userRange]);

  /** アーティストの星（お気に入り）を切り替え */
  const toggleFavorite = async (e: React.MouseEvent, id: number, name: string) => {
    e.stopPropagation(); // 行クリックイベントが発生しないように止める
    try {
      if (favoriteIds.includes(id)) {
        await removeFavoriteArtist(id);
        setFavoriteIds(prev => prev.filter(fid => fid !== id));
      } else {
        await addFavoriteArtist(id, name);
        setFavoriteIds(prev => [...prev, id]);
      }
    } catch (err: any) {
      alert("\u30ed\u30b0\u30a4\u30f3\u304c\u5fc5\u8981\u3001\u307e\u305f\u306f\u4e0a\u9650\uff11\uff10\u7d44\u3067\u3059");
    }
  };

  /** 曲のハート（お気に入り）を切り替え */
  const handleToggleFavoriteSong = useCallback(async (songId: number) => {
    if (!isAuthenticated) {
      onLoginClick?.();
      return;
    }
    // オプティミスティック更新（通信完了を待たずに画面を変える）
    let wasFavorite = false;
    setFavoriteSongIds(prev => {
      wasFavorite = prev.has(songId);
      const next = new Set(prev);
      wasFavorite ? next.delete(songId) : next.add(songId);
      return next;
    });
    setTogglingIds(prev => new Set(prev).add(songId));
    try {
      if (wasFavorite) await removeFavorite(songId);
      else await addFavorite(songId);
    } catch (err) {
      // 失敗したら元に戻す
      setFavoriteSongIds(prev => {
        const next = new Set(prev);
        wasFavorite ? next.add(songId) : next.delete(songId);
        return next;
      });
    } finally {
      setTogglingIds(prev => {
        const next = new Set(prev);
        next.delete(songId);
        return next;
      });
    }
  }, [isAuthenticated, onLoginClick]);

  // ── ページネーション操作 ──
  const totalPages = Math.ceil(totalArtists / ARTISTS_PER_PAGE);
  const totalSearchPages = Math.ceil(totalSearchSongs / SONGS_PER_PAGE);

  const handleNext = () => {
    if (activeQuery) { if (searchPage + 1 < totalSearchPages) setSearchPage(p => p + 1); }
    else { if (artistPage + 1 < totalPages) setArtistPage(p => p + 1); }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handlePrev = () => {
    if (activeQuery) { if (searchPage > 0) setSearchPage(p => p - 1); }
    else { if (artistPage > 0) setArtistPage(p => p - 1); }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handlePageJump = () => {
    if (activeQuery) {
      let p = parseInt(searchPageInput, 10);
      if (isNaN(p) || p < 1) p = 1;
      setSearchPage(p - 1);
    } else {
      let p = parseInt(pageInput, 10);
      if (isNaN(p) || p < 1) p = 1;
      setArtistPage(p - 1);
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  /** 五十音ジャンプ：目的の行まで二分探索でページを飛ばす */
  const handleIndexJump = useCallback(async (char: string) => {
    const targetRow = INDEX_KANA.indexOf(char);
    if (targetRow === -1 || totalArtists === 0) return;
    setLoading(true);
    try {
      let low = 0, high = Math.max(totalPages - 1, 0), found = 0;
      while (low <= high) {
        const mid = Math.floor((low + high) / 2);
        const { artists: page } = await getArtists(ARTISTS_PER_PAGE, mid * ARTISTS_PER_PAGE);
        if (!page.length) break;
        const firstRow = getConsonantRow(page[0].reading || "");
        const lastRow = getConsonantRow(page[page.length - 1].reading || "");
        if (targetRow < firstRow) high = mid - 1;
        else if (targetRow > lastRow) low = mid + 1;
        else { found = mid; high = mid - 1; }
      }
      setArtistPage(found);
      setPageInput((found + 1).toString());
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } finally {
      setLoading(false);
    }
  }, [totalArtists, totalPages]);

  // ── 表示 (Render) ──

  // アーティスト詳細モード
  if (selectedArtist) {
    return (
      <div className="flex flex-col items-center min-h-[calc(100vh-80px)] p-4 sm:p-8">
        <div className="w-full max-w-5xl mb-6">
          <button onClick={() => setSelectedArtist(null)} className="text-slate-500 hover:text-cyan-400 font-bold mb-6">
            &larr; \u30a2\u30fc\u30c6\u30a3\u30b9\u30c8\u4e00\u89a7\u306b\u623b\u308b
          </button>
          <div className="flex items-center gap-6">
            <div className="w-16 h-16 bg-slate-900 rounded-full flex items-center justify-center text-cyan-400 text-2xl font-bold border-2 border-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.6)]">
              {selectedArtist.name.charAt(0)}
            </div>
            <div>
              <h1 className="text-3xl font-black italic text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-fuchsia-400">
                {selectedArtist.name}
              </h1>
              <p className="text-cyan-400 font-bold">{artistSongs.length}\u66f2</p>
            </div>
          </div>
        </div>

        {songsLoading ? (
          <p className="text-slate-500">\u8aad\u307f\u8fbc\u307f\u4e2d...</p>
        ) : (
          <div className="w-full max-w-5xl bg-slate-900/60 backdrop-blur-md rounded-xl border border-white/10 overflow-hidden">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-slate-800/50 text-xs text-slate-400 border-b border-white/5">
                  <th className="py-3 px-5">#</th>
                  <th className="py-3 px-4">Title</th>
                  <th className="py-3 px-4">Lowest</th>
                  <th className="py-3 px-4">Highest</th>
                  {userRange && <th className="py-3 px-4 text-center">Key</th>}
                  <th className="py-3 px-2 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {artistSongs.map((song, i) => (
                  <tr key={song.id} className="border-b border-cyan-500/10 hover:bg-cyan-900/20 text-sm">
                    <td className="py-3 px-5 text-slate-500">{i + 1}</td>
                    <td className="py-3 px-4 font-medium">
                      <a href={`https://www.google.com/search?q=${encodeURIComponent(`${selectedArtist.name} ${song.title} \u6b4c\u8a5e`)}`} target="_blank" rel="noopener noreferrer" className="text-slate-200 hover:text-cyan-400">
                        {song.title}
                      </a>
                    </td>
                    <td className="py-3 px-4 text-slate-400">{song.lowest_note || '-'}</td>
                    <td className="py-3 px-4 text-slate-400">{song.highest_note || '-'}</td>
                    {userRange && (
                      <td className="py-3 px-4 text-center">
                        {song.recommended_key !== undefined ? keyBadge(song.recommended_key, song.fit) : '-'}
                      </td>
                    )}
                    <td className="py-3 px-2">
                      <button onClick={() => handleToggleFavoriteSong(song.id)} disabled={togglingIds.has(song.id)}>
                        {favoriteSongIds.has(song.id) ? <HeartIconSolid className="w-5 h-5 text-rose-500" /> : <HeartIcon className="w-5 h-5 text-slate-500" />}
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

  // メイン画面（検索 ＆ アーティスト一覧）
  return (
    <div className="flex flex-col items-center min-h-[calc(100vh-80px)] p-4 sm:p-8">
      <div className="w-full max-w-3xl flex flex-col mb-4 gap-6">
        <form className="relative w-full group" onSubmit={(e) => { e.preventDefault(); if (onSearchChange) onSearchChange(searchInput); }}>
          <input type="text" placeholder="\u697d\u66f2\u540d\u30fb\u30a2\u30fc\u30c6\u30a3\u30b9\u30c8\u540d\u3067\u691c\u7d22..." value={searchInput} onChange={(e) => setSearchInput(e.target.value)} className="w-full pl-10 pr-10 py-3 bg-slate-900/40 border border-cyan-500/30 rounded-lg text-slate-200 focus:ring-1 focus:ring-cyan-400" />
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          {searchInput && (
            <button type="button" onClick={() => { setSearchInput(''); setActiveQuery(''); if (onSearchChange) onSearchChange(''); }} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-cyan-400">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          )}
        </form>
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <h1 className="text-3xl font-black italic text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-fuchsia-400 to-yellow-400">
            {activeQuery ? '\u697d\u66f2\u691c\u7d22\u7d50\u679c' : 'ARTISTS'}
          </h1>
          {!activeQuery && (
            <div className="flex flex-wrap gap-2">
              {INDEX_KANA.map(char => (
                <button key={char} onClick={() => handleIndexJump(char)} className="w-8 h-8 text-sm font-bold text-slate-400 bg-slate-900/60 border border-cyan-900/50 rounded-sm hover:text-cyan-300 hover:border-cyan-400 transition-all">
                  {char}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {error && <p className="text-rose-400 mb-4">{error}</p>}

      {activeQuery ? (
        // 楽曲検索結果の表示
        <>
          {searchLoading ? <p className="text-slate-500">\u8aad\u307f\u8fbc\u307f\u4e2d...</p> : (
            <div className="w-full max-w-5xl bg-slate-900/60 backdrop-blur-md rounded-xl border border-white/10 overflow-hidden">
              <table className="w-full text-left">
                <thead>
                  <tr className="bg-slate-800/50 text-xs text-slate-400 border-b border-white/5">
                    <th className="py-3 px-5">#</th>
                    <th className="py-3 px-4">Song</th>
                    <th className="py-3 px-4">Artist</th>
                    {userRange && <th className="py-3 px-4 text-center">Key</th>}
                    <th className="py-3 px-2 w-10"></th>
                  </tr>
                </thead>
                <tbody>
                  {searchSongs.map((song, i) => (
                    <tr key={song.id} className="border-b border-cyan-500/10 hover:bg-cyan-900/20 text-sm">
                      <td className="py-3 px-5 text-slate-500">{searchPage * SONGS_PER_PAGE + i + 1}</td>
                      <td className="py-3 px-4 font-medium">
                        <a href={`https://www.google.com/search?q=${encodeURIComponent(`${song.artist} ${song.title} \u6b4c\u8a5e`)}`} target="_blank" rel="noopener noreferrer" className="text-slate-200 hover:text-cyan-400">
                          {song.title}
                        </a>
                      </td>
                      <td className="py-3 px-4 text-slate-400">{song.artist}</td>
                      {userRange && (
                        <td className="py-3 px-4 text-center">
                          {song.recommended_key !== undefined ? keyBadge(song.recommended_key, song.fit) : '-'}
                        </td>
                      )}
                      <td className="py-3 px-2">
                        <button onClick={() => handleToggleFavoriteSong(song.id)} disabled={togglingIds.has(song.id)}>
                          {favoriteSongIds.has(song.id) ? <HeartIconSolid className="w-5 h-5 text-rose-500" /> : <HeartIcon className="w-5 h-5 text-slate-500" />}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {/* 楽曲検索のページネーション */}
          {!searchLoading && totalSearchSongs > SONGS_PER_PAGE && (
            <div className="flex items-center gap-4 mt-8">
              <button onClick={handlePrev} disabled={searchPage === 0} className="px-4 py-2 bg-slate-800 text-slate-300 rounded-lg disabled:opacity-50">Prev</button>
              <input type="text" value={searchPageInput} onChange={e => setSearchPageInput(e.target.value)} onBlur={handlePageJump} className="w-12 h-9 text-center bg-slate-800 rounded-lg" />
              <button onClick={handleNext} disabled={searchPage + 1 >= totalSearchPages} className="px-4 py-2 bg-slate-800 text-slate-300 rounded-lg disabled:opacity-50">Next</button>
            </div>
          )}
        </>
      ) : (
        // アーティスト一覧の表示
        <>
          {loading && <p className="text-slate-500">\u8aad\u307f\u8fbc\u307f\u4e2d...</p>}
          <div className="w-full max-w-3xl bg-slate-900/60 backdrop-blur-md rounded-xl border border-cyan-500/20 overflow-hidden">
            {artists.map((artist) => (
              <div key={artist.id} className="group relative flex items-center w-full border-b border-cyan-500/10 last:border-0 hover:bg-cyan-900/20 transition-all">
                <button onClick={() => handleSelectArtist(artist)} className="flex-1 flex items-center justify-between p-4 pl-6 text-left">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-slate-900 rounded-full flex items-center justify-center text-cyan-400 font-bold border-2 border-cyan-400">
                      {artist.name.charAt(0)}
                    </div>
                    <p className="font-bold text-slate-200 group-hover:text-cyan-400">{artist.name}</p>
                  </div>
                  <span className="text-xs text-cyan-400 bg-slate-900/80 px-3 py-1 rounded-sm border border-cyan-500/30">{artist.song_count}\u66f2</span>
                </button>
                <button onClick={(e) => toggleFavorite(e, artist.id, artist.name)} className="p-4 pr-6">
                  {favoriteIds.includes(artist.id) ? <StarSolid className="w-6 h-6 text-amber-400" /> : <StarOutline className="w-6 h-6 text-slate-500" />}
                </button>
              </div>
            ))}
          </div>
          {/* アーティスト一覧のページネーション */}
          {!loading && totalArtists > ARTISTS_PER_PAGE && (
            <div className="flex items-center gap-4 mt-8">
              <button onClick={handlePrev} disabled={artistPage === 0} className="px-4 py-2 bg-slate-800 text-slate-300 rounded-lg disabled:opacity-50">\u524d\u306e\u30da\u30fc\u30b8</button>
              <input type="text" value={pageInput} onChange={e => setPageInput(e.target.value)} onBlur={handlePageJump} className="w-12 h-9 text-center bg-slate-800 rounded-lg" />
              <button onClick={handleNext} disabled={artistPage + 1 >= totalPages} className="px-4 py-2 bg-slate-800 text-slate-300 rounded-lg disabled:opacity-50">\u6b21\u306e\u30da\u30fc\u30b8</button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default SongListPage;