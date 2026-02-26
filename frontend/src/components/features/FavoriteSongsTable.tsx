import React from "react";
import { FavoriteSong } from "../../api";
import FavoriteSongRow from "./FavoriteSongRow";

/** お気に入り楽曲テーブルのプロパティ */
interface FavoriteSongsTableProps {
  /** お気に入り楽曲一覧 */
  favorites: FavoriteSong[];
  /** 削除処理中の楽曲ID集合 */
  removingIds: Set<number>;
  /** 行削除時の処理 */
  onRemove: (songId: number) => void;
}

/**
 * お気に入り楽曲テーブル全体を描画するコンポーネントです。
 */
const FavoriteSongsTable: React.FC<FavoriteSongsTableProps> = ({
  favorites,
  removingIds,
  onRemove,
}) => {
  return (
    <div className="table-container">
      <table className="w-full text-left">
        <thead>
          <tr className="table-header">
            <th className="py-3 px-5 font-medium">#</th>
            <th className="py-3 px-4 font-medium">Title</th>
            <th className="py-3 px-4 font-medium">Artist</th>
            <th className="py-3 px-4 font-medium hidden sm:table-cell">Lowest</th>
            <th className="py-3 px-4 font-medium hidden sm:table-cell">Highest</th>
            <th className="py-3 px-4 font-medium hidden sm:table-cell">Falsetto</th>
            <th className="py-3 px-2 font-medium w-10"></th>
          </tr>
        </thead>
        <tbody>
          {favorites.map((favorite, index) => (
            <FavoriteSongRow
              key={favorite.favorite_id}
              favorite={favorite}
              index={index}
              removing={removingIds.has(favorite.song_id)}
              onRemove={onRemove}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default React.memo(FavoriteSongsTable);
