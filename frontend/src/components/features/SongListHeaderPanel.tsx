/**
 * 【SongListHeaderPanel.tsx】
 * 役割：楽曲一覧ページ上部の検索UIと見出し表示を担当するコンポーネントです。
 * 特徴：検索バー、状態に応じたタイトル/補助文、五十音インデックスの表示をまとめます。
 */

import React from "react";
import type { UserRange } from "../../api";
import SearchBar from "../ui/SearchBar";
import SyllableIndex from "../ui/SyllableIndex";

/**
 * SongListHeaderPanel が受け取るプロパティ
 */
interface SongListHeaderPanelProps {
  /** 検索入力の現在値 */
  searchInput: string;
  /** 検索入力変更時の処理 */
  onSearchInputChange: (value: string) => void;
  /** 検索確定時の処理 */
  onSearchSubmit: (query: string) => void;
  /** アクティブな検索クエリ */
  activeQuery: string;
  /** ユーザー音域 */
  userRange?: UserRange | null;
  /** 五十音インデックス押下時の処理 */
  onIndexClick: (char: string) => Promise<void>;
}

/**
 * 楽曲一覧ページのヘッダー領域を表示します。
 */
const SongListHeaderPanel: React.FC<SongListHeaderPanelProps> = ({
  searchInput,
  onSearchInputChange,
  onSearchSubmit,
  activeQuery,
  userRange,
  onIndexClick,
}) => {
  return (
    <div className="w-full max-w-3xl flex flex-col mb-4 gap-6">
      <SearchBar
        value={searchInput}
        onChange={onSearchInputChange}
        onSubmit={onSearchSubmit}
        placeholder="楽曲名・アーティスト名で検索..."
      />
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <h1 className="text-3xl sm:text-4xl font-black italic title-gradient-cyan-fuchsia mb-2 drop-shadow-[0_0_10px_rgba(34,211,238,0.3)] tracking-wider">
            {activeQuery ? "楽曲検索結果" : "ARTISTS"}
          </h1>
          <p className="text-xs text-slate-400 font-bold tracking-wide">
            {activeQuery
              ? `"${activeQuery}" の検索結果`
              : (userRange ? "" : "録音すると、キーおすすめが表示されます")}
          </p>
        </div>
        <SyllableIndex
          onIndexClick={onIndexClick}
          visible={!activeQuery}
        />
      </div>
    </div>
  );
};

export default SongListHeaderPanel;
