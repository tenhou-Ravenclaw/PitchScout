/**
 * 【SyllableIndex.tsx】
 * 五十音順のインデックスボタン（あ・か・さ・た...）を表示します。
 * ボタンをクリックすると、該当する行の先頭アーティストにジャンプします。
 */

import React from 'react';
import { INDEX_KANA } from '../../constants/songListConstants';

interface SyllableIndexProps {
  /**
   * 五十音ボタンクリック時のハンドラ
   * @param char - クリックされた文字（例: 'あ', 'か'）
   */
  onIndexClick: (char: string) => void;

  /**
   * インデックスを表示するかどうか（検索時は非表示）
   */
  visible: boolean;
}

/**
 * SyllableIndex Component
 * 
 * @example
 * <SyllableIndex
 *   onIndexClick={handleIndexJump}
 *   visible={!searchQuery}
 * />
 */
const SyllableIndex: React.FC<SyllableIndexProps> = ({ onIndexClick, visible }) => {
  if (!visible) return null;

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-2 text-xs text-slate-500 font-semibold tracking-wider">
        <span>五十音インデックス</span>
      </div>
      <div className="grid grid-cols-10 gap-2">
        {INDEX_KANA.map((char: string) => (
          <button
            key={char}
            onClick={() => onIndexClick(char)}
            className="w-8 h-8 flex items-center justify-center text-sm font-bold text-slate-400 bg-slate-900/60 border border-cyan-900/50 rounded-sm hover:bg-cyan-900/40 hover:text-cyan-300 hover:border-cyan-400 hover:shadow-[0_0_10px_rgba(34,211,238,0.6)] transition-all duration-300"
          >
            {char}
          </button>
        ))}
      </div>
    </div>
  );
};

export default SyllableIndex;
