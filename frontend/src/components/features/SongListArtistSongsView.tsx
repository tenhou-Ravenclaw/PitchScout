/**
 * 【SongListArtistSongsView.tsx】
 * 役割：選択中アーティストの楽曲一覧表示を担当するビューコンポーネントです。
 * 特徴：戻る導線、ヘッダー、楽曲テーブルの表示責務を集約します。
 */

import React from "react";
import { Song, UserRange } from "../../api";
import LoadingState from "../ui/LoadingState";
import ArtistSongsHeader from "./ArtistSongsHeader";
import SongTable from "./SongTable";

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

      {songsLoading ? (
        <LoadingState />
      ) : (
        <SongTable
          songs={artistSongs}
          userRange={userRange}
          rowStartIndex={0}
          titleHeaderLabel="Title"
          searchArtistNameOverride={artistName}
          onToggleFavoriteSong={onToggleFavoriteSong}
          isFavoriteSong={isFavoriteSong}
          isToggling={isToggling}
        />
      )}
    </div>
  );
};

export default SongListArtistSongsView;
