/**
 * 【SongTable.tsx】
 * 役割：楽曲テーブル（アーティスト別表示 / 検索結果表示）を共通化するための表示コンポーネントです。
 * 特徴：キー提案バッジ・お気に入りトグル・歌詞検索リンク表示を一元化します。
 */

import React from "react";
import { HeartIcon } from "@heroicons/react/24/outline";
import { HeartIcon as HeartIconSolid } from "@heroicons/react/24/solid";
import { Song, UserRange } from "../../api";
import { keyBadge } from "../../utils/keyBadge";

/**
 * SongTable が受け取るプロパティ
 */
interface SongTableProps {
  /** 表示する楽曲一覧 */
  songs: Song[];
  /** ユーザー音域（存在する場合のみ Key 列を表示） */
  userRange?: UserRange | null;
  /** 行番号の開始オフセット */
  rowStartIndex?: number;
  /** アーティスト列を表示するか */
  showArtistColumn?: boolean;
  /** タイトル列の見出し */
  titleHeaderLabel?: string;
  /** 外部検索時に優先使用するアーティスト名 */
  searchArtistNameOverride?: string;
  /** 楽曲のお気に入りトグル */
  onToggleFavoriteSong: (songId: number) => void;
  /** 楽曲がお気に入りか判定 */
  isFavoriteSong: (songId: number) => boolean;
  /** 楽曲がお気に入り処理中か判定 */
  isToggling: (songId: number) => boolean;
}

/**
 * 楽曲テーブルを表示します。
 */
const SongTable: React.FC<SongTableProps> = ({
  songs,
  userRange,
  rowStartIndex = 0,
  showArtistColumn = false,
  titleHeaderLabel = "Title",
  searchArtistNameOverride,
  onToggleFavoriteSong,
  isFavoriteSong,
  isToggling,
}) => {
  return (
    <div className="table-container">
      <table className="w-full text-left">
        <thead>
          <tr className="table-header">
            <th className="py-3 px-5 font-medium">#</th>
            <th className="py-3 px-4 font-medium">{titleHeaderLabel}</th>
            {showArtistColumn && <th className="py-3 px-4 font-medium">アーティスト</th>}
            <th className="py-3 px-4 font-medium">Lowest</th>
            <th className="py-3 px-4 font-medium">Highest</th>
            <th className="py-3 px-4 font-medium hidden sm:table-cell">Falsetto</th>
            {userRange && <th className="py-3 px-4 font-medium text-center">Key</th>}
            <th className="py-3 px-2 font-medium w-10"></th>
          </tr>
        </thead>
        <tbody>
          {songs.map((song, i) => {
            const artistForSearch = searchArtistNameOverride || song.artist;
            return (
              <tr key={song.id} className="table-row group">
                <td className="py-3 px-5 text-slate-500 text-xs">{rowStartIndex + i + 1}</td>
                <td className="py-3 px-4 font-medium">
                  <a
                    href={`https://www.google.com/search?q=${encodeURIComponent(`${artistForSearch} ${song.title} 歌詞`)}`}
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
                <td className="py-3 px-4 text-slate-400 whitespace-nowrap">{song.lowest_note || "-"}</td>
                <td className="py-3 px-4 text-slate-400 whitespace-nowrap">{song.highest_note || "-"}</td>
                <td className="py-3 px-4 text-slate-400 whitespace-nowrap hidden sm:table-cell">{song.falsetto_note || "-"}</td>
                {userRange && (
                  <td className="py-3 px-4 text-center">
                    {song.recommended_key !== undefined
                      ? keyBadge(song.recommended_key, song.fit)
                      : <span className="text-slate-600">-</span>}
                  </td>
                )}
                <td className="py-3 px-2 text-center">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleFavoriteSong(song.id);
                    }}
                    disabled={isToggling(song.id)}
                    className="p-1 rounded-full hover:bg-white/10 transition-colors disabled:opacity-50"
                  >
                    {isFavoriteSong(song.id)
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
