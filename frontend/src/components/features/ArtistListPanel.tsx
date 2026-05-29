/**
 * 【ArtistListPanel.tsx】
 * 役割：アーティスト一覧表示とお気に入りトグル表示を共通化するコンポーネントです。
 * 特徴：アーティスト選択とお気に入り操作のUIを一箇所に集約し、ページ本体の責務を軽くします。
 */

import React from "react";
import { StarIcon as StarSolid } from "@heroicons/react/24/solid";
import { StarIcon as StarOutline } from "@heroicons/react/24/outline";
import { Artist } from "../../api";
import { getConsonantRow } from "../../constants/songListConstants";

/**
 * ArtistListPanel が受け取るプロパティ
 */
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
 * アーティスト一覧を表示します。
 */
const ArtistListPanel: React.FC<ArtistListPanelProps> = ({
  artists,
  onSelectArtist,
  onToggleFavoriteArtist,
  isFavorite,
}) => {
  return (
    <div id="artist-list-panel" className="w-full max-w-3xl bg-slate-900/60 backdrop-blur-md rounded-xl shadow-[0_0_20px_rgba(0,0,0,0.5)] border border-cyan-500/20 overflow-hidden">
      {artists.map((artist) => (
        <div
          key={artist.id}
          id={`artist-${artist.id}`}
          data-row={getConsonantRow(artist.reading || "")}
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
              <p className="font-bold text-slate-200 group-hover:text-cyan-400 transition-colors drop-shadow-[0_0_5px_rgba(34,211,238,0)] group-hover:drop-shadow-[0_0_5px_rgba(34,211,238,0.5)]">{artist.name}</p>
            </div>
            <span className="text-xs text-cyan-400 bg-slate-900/80 px-3 py-1 rounded-sm border border-cyan-500/30 shadow-[0_0_5px_rgba(34,211,238,0.2)]">{artist.song_count}{"曲"}</span>
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
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

export default ArtistListPanel;
