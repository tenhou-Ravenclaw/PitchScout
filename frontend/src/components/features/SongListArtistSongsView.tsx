/**
 * 【SongListArtistSongsView.tsx】
 * 役割：選択中アーティストの楽曲一覧表示を担当するビューコンポーネントです。
 * 特徴：戻る導線、ヘッダー、楽曲テーブルの表示責務を集約します。
 */

import React from "react";
import { Song, UserRange } from "../../api";
import { SongTableWithLoading } from "./SongTable";

/** ArtistSongsHeader が受け取るプロパティ */
interface ArtistSongsHeaderProps {
  /** 戻るボタン押下時の処理 */
  onBack: () => void;
  /** 表示対象のアーティスト名 */
  artistName: string;
  /** 表示対象の楽曲数 */
  songCount: number;
}

/**
 * SongListArtistSongsView が受け取るプロパティ
 */
interface SongListArtistSongsViewProps {
  /** 表示対象のアーティスト名 */
  artistName: string;
  /** 表示対象の楽曲一覧 */
  artistSongs: Song[];
  /** 楽曲取得中フラグ */
  songsLoading: boolean;
  /** ユーザー音域 */
  userRange?: UserRange | null;
  /** 戻る操作時の処理 */
  onBack: () => void;
  /** 楽曲のお気に入りトグル */
  onToggleFavoriteSong: (songId: number) => void;
  /** 楽曲がお気に入りか判定 */
  isFavoriteSong: (songId: number) => boolean;
  /** 楽曲がお気に入り処理中か判定 */
  isToggling: (songId: number) => boolean;
}

/**
 * アーティスト選択時ヘッダーを表示します。
 */
const ArtistSongsHeader: React.FC<ArtistSongsHeaderProps> = ({
  onBack,
  artistName,
  songCount,
}) => {
  return (
    <div className="w-full max-w-5xl mb-6">
      <button
        onClick={onBack}
        className="btn-back-link transition-all duration-300 mb-6 drop-shadow-[0_0_5px_rgba(34,211,238,0)] hover:drop-shadow-[0_0_8px_rgba(34,211,238,0.5)]"
      >
        &larr; アーティスト一覧に戻る
      </button>
      <div className="flex items-center gap-6">
        <div className="relative w-16 h-16 bg-slate-900 rounded-full flex items-center justify-center text-cyan-400 text-2xl font-bold border-2 border-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.6)]">
          {artistName.charAt(0)}
        </div>
        <div>
          <h1 className="text-3xl sm:text-4xl font-black italic title-gradient-cyan-fuchsia drop-shadow-[0_0_10px_rgba(34,211,238,0.3)] tracking-wider">
            {artistName}
          </h1>
          <p className="text-sm text-cyan-400 mt-1 font-bold tracking-widest">{songCount}曲</p>
        </div>
      </div>
    </div>
  );
};

/**
 * 選択中アーティストの楽曲ビューを表示します。
 */
const SongListArtistSongsView: React.FC<SongListArtistSongsViewProps> = ({
  artistName,
  artistSongs,
  songsLoading,
  userRange,
  onBack,
  onToggleFavoriteSong,
  isFavoriteSong,
  isToggling,
}) => {
  return (
    <div className="flex flex-col items-center min-h-[calc(100vh-80px)] bg-transparent p-4 sm:p-8">
      <ArtistSongsHeader
        onBack={onBack}
        artistName={artistName}
        songCount={artistSongs.length}
      />

      <SongTableWithLoading
        loading={songsLoading}
        songs={artistSongs}
        userRange={userRange}
        rowStartIndex={0}
        titleHeaderLabel="Title"
        searchArtistNameOverride={artistName}
        onToggleFavoriteSong={onToggleFavoriteSong}
        isFavoriteSong={isFavoriteSong}
        isToggling={isToggling}
      />
    </div>
  );
};

export default SongListArtistSongsView;
