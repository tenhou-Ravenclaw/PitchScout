import React from "react";
import { HeartIcon as HeartIconSolid } from "@heroicons/react/24/solid";
import { FavoriteSong } from "../../api";

/** お気に入り楽曲テーブル行のプロパティ */
interface FavoriteSongRowProps {
  /** 表示するお気に入り楽曲 */
  favorite: FavoriteSong;
  /** 表示順（1始まりで表示） */
  index: number;
  /** 削除処理中かどうか */
  removing: boolean;
  /** 削除ボタン押下時の処理 */
  onRemove: (songId: number) => void;
}

/**
 * お気に入り楽曲一覧の1行を描画するコンポーネントです。
 */
const FavoriteSongRow: React.FC<FavoriteSongRowProps> = ({
  favorite,
  index,
  removing,
  onRemove,
}) => {
  return (
    <tr className="table-row group">
      <td className="py-3 px-5 text-slate-500 text-xs">{index + 1}</td>
      <td className="py-3 px-4 text-slate-200 font-medium group-hover:text-white transition-colors">
        {favorite.title}
      </td>
      <td className="py-3 px-4 text-slate-400">{favorite.artist || "-"}</td>
      <td className="py-3 px-4 text-slate-400 whitespace-nowrap hidden sm:table-cell">
        {favorite.lowest_note || "-"}
      </td>
      <td className="py-3 px-4 text-slate-400 whitespace-nowrap hidden sm:table-cell">
        {favorite.highest_note || "-"}
      </td>
      <td className="py-3 px-4 text-slate-400 whitespace-nowrap hidden sm:table-cell">
        {favorite.falsetto_note || "-"}
      </td>
      <td className="py-3 px-2 text-center">
        <button
          onClick={() => onRemove(favorite.song_id)}
          disabled={removing}
          className="p-1 rounded-full hover:bg-white/10 transition-colors disabled:opacity-50"
        >
          <HeartIconSolid className="w-5 h-5 text-rose-500" />
        </button>
      </td>
    </tr>
  );
};

export default React.memo(FavoriteSongRow);
