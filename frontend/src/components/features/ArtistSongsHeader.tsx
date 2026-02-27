/**
 * 【ArtistSongsHeader.tsx】
 * 役割：アーティスト選択後の楽曲一覧ヘッダーを表示するコンポーネントです。
 * 特徴：戻る導線とアーティスト情報（名前・曲数）を統一的に描画します。
 */

import React from "react";

/**
 * ArtistSongsHeader が受け取るプロパティ
 */
interface ArtistSongsHeaderProps {
  /** 戻るボタン押下時の処理 */
  onBack: () => void;
  /** 表示対象のアーティスト名 */
  artistName: string;
  /** 表示対象の楽曲数 */
  songCount: number;
  /** ユーザー音域 */
  userRange?: import("../../api").UserRange | null;
}

/**
 * アーティスト選択時ヘッダーを表示します。
 */
const ArtistSongsHeader: React.FC<ArtistSongsHeaderProps> = ({
  onBack,
  artistName,
  songCount,
  userRange,
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
          <div className="flex items-center gap-4 mt-1">
            <p className="text-sm text-cyan-400 font-bold tracking-widest">{songCount}曲</p>
            {userRange && (
              <p className="text-xs text-slate-400 font-bold tracking-wide border-l border-slate-700 pl-4">
                音域に合わせたキーおすすめを表示中
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ArtistSongsHeader;
