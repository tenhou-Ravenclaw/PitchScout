/**
 * 【SongTable.tsx】
 * 役割：楽曲のリストを一覧表示するための「テーブル部品」です。
 * 楽曲一覧ページやお気に入りページなど、複数の場所で使い回すことができます。
 * * 💡 設計図（FRONTEND_STRUCTURE.md）に基づく移動案：
 * 1. 移動先: src/features/songs/components/SongTable.tsx
 */

import React from 'react';
// アイコン素材の読み込み
import { HeartIcon } from '@heroicons/react/24/outline';
import { HeartIcon as HeartIconSolid } from '@heroicons/react/24/solid';
// APIから「曲（Song）」や「音域（UserRange）」の型定義を借りてきます
import type { Song, UserRange } from '../api';

/**
 * ── ヘルパー部品：キーバッジ ──
 * 曲のキー（±0など）を色付きで表示します。
 * fit（適合度）に合わせて「完璧」「良好」「普通」「難しい」の色を出し分けます。
 */
const keyBadge = (key: number, fit?: string) => {
  const label = key === 0 ? "\u00b10" : key > 0 ? `+${key}` : `${key}`;
  let color: string;
  
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

/**
 * プロパティの定義 (Props)
 * このテーブルを表示するために必要なデータ一式です。
 */
interface SongTableProps {
  songs: Song[];               // 表示する曲の配列
  rowOffset?: number;          // 番号（#）の開始オフセット
  showArtistColumn?: boolean;  // 「アーティスト名」の列を出すかどうか
  artistNameOverride?: string; // アーティスト名を一律で書き換える場合に使用
  userRange: UserRange | null; // あなたの音域データ（キーおすすめに使用）
  favoriteSongIds: Set<number>;// お気に入り登録済みの曲IDセット
  togglingIds: Set<number>;    // 現在お気に入り処理中の（連打防止）IDセット
  onToggleFavorite: (songId: number) => void; // ハートを押した時の関数
}

const SongTable: React.FC<SongTableProps> = ({
  songs,
  rowOffset = 0,
  showArtistColumn = false,
  artistNameOverride,
  userRange,
  favoriteSongIds,
  togglingIds,
  onToggleFavorite,
}) => {
  return (
    <div className="w-full max-w-5xl bg-slate-900/60 backdrop-blur-md shadow-xl rounded-xl overflow-hidden border border-white/10">
      <table className="w-full text-left">
        <thead>
          <tr className="bg-slate-800/50 text-xs text-slate-400 uppercase border-b border-white/5">
            <th className="py-3 px-5 font-medium">#</th>
            <th className="py-3 px-4 font-medium">楽曲</th>
            {/* アーティスト名を表示するかどうかの条件分岐 */}
            {showArtistColumn && <th className="py-3 px-4 font-medium">アーティスト</th>}
            <th className="py-3 px-4 font-medium hidden sm:table-cell">Lowest</th>
            <th className="py-3 px-4 font-medium hidden sm:table-cell">Highest</th>
            <th className="py-3 px-4 font-medium hidden sm:table-cell">Falsetto</th>
            {/* 自分の音域データがある場合のみ「Key」列を表示 */}
            {userRange && <th className="py-3 px-4 font-medium text-center">Key</th>}
            <th className="py-3 px-2 font-medium w-10"></th>
          </tr>
        </thead>
        <tbody>
          {songs.map((song, i) => {
            // Google検索リンク用のアーティスト名
            const artistForLink = artistNameOverride || song.artist;
            return (
              <tr key={song.id} className="border-b border-cyan-500/10 hover:bg-cyan-900/20 transition-all duration-300 text-sm group">
                <td className="py-3 px-5 text-slate-500 text-xs">{rowOffset + i + 1}</td>
                <td className="py-3 px-4 font-medium">
                  {/* Googleでの歌詞検索リンク */}
                  <a
                    href={`https://www.google.com/search?q=${encodeURIComponent(`${artistForLink} ${song.title} 歌詞`)}`}
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
                {showArtistColumn && (
                  <td className="py-3 px-4 text-slate-400 whitespace-nowrap">{song.artist}</td>
                )}
                <td className="py-3 px-4 text-slate-400 whitespace-nowrap hidden sm:table-cell">{song.lowest_note || '-'}</td>
                <td className="py-3 px-4 text-slate-400 whitespace-nowrap hidden sm:table-cell">{song.highest_note || '-'}</td>
                <td className="py-3 px-4 text-slate-400 whitespace-nowrap hidden sm:table-cell">{song.falsetto_note || '-'}</td>
                {userRange && (
                  <td className="py-3 px-4 text-center">
                    {/* 推奨キーのバッジを表示 */}
                    {song.recommended_key !== undefined
                      ? keyBadge(song.recommended_key, song.fit)
                      : <span className="text-slate-600">-</span>}
                  </td>
                )}
                <td className="py-3 px-2 text-center">
                  <button
                    onClick={(e) => { e.stopPropagation(); onToggleFavorite(song.id); }}
                    disabled={togglingIds.has(song.id)}
                    className="p-1 rounded-full hover:bg-white/10 transition-colors disabled:opacity-50"
                  >
                    {/* お気に入り状態かどうかに応じてハートの形を変える */}
                    {favoriteSongIds.has(song.id)
                      ? <HeartIconSolid className="w-5 h-5 text-rose-500" />
                      : <HeartIcon className="w-5 h-5 text-slate-500 hover:text-rose-400" />}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default SongTable;