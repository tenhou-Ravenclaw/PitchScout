/**
 * 【Pagination.tsx】
 * 汎用的なページネーションコンポーネントです。
 * 前へ・次へボタン、直接ページ入力、ページ数表示を提供します。
 */

import React from 'react';

interface PaginationProps {
  /**
   * 現在のページ番号（0-indexed）
   */
  currentPage: number;

  /**
   * 総ページ数
   */
  totalPages: number;

  /**
   * ページ入力フィールドの制御値（1-indexed）
   */
  pageInput: string;

  /**
   * ページ入力フィールドの変更ハンドラ
   */
  onPageInputChange: (value: string) => void;

  /**
   * 「前のページ」ボタンクリック時
   */
  onPrev: () => void;

  /**
   * 「次のページ」ボタンクリック時
   */
  onNext: () => void;

  /**
   * ページジャンプ確定時（Enter キー / フォーカス離脱）
   */
  onPageJump: () => void;
}

/**
 * Pagination Component
 * 
 * @example
 * <Pagination
 *   currentPage={0}
 *   totalPages={10}
 *   pageInput="1"
 *   onPageInputChange={setPageInput}
 *   onPrev={handlePrev}
 *   onNext={handleNext}
 *   onPageJump={handlePageJump}
 * />
 */
const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  pageInput,
  onPageInputChange,
  onPrev,
  onNext,
  onPageJump
}) => {
  return (
    <div className="flex items-center justify-center gap-4 mt-8">
      <button
        onClick={onPrev}
        disabled={currentPage === 0}
        className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:bg-slate-700 disabled:opacity-50 transition-colors shadow-sm text-sm"
      >
        前のページ
      </button>
      <div className="flex items-center gap-2 text-slate-400 text-sm font-medium">
        <input
          type="text"
          value={pageInput}
          onChange={(e) => onPageInputChange(e.target.value)}
          onBlur={onPageJump}
          onKeyDown={(e) => e.key === 'Enter' && onPageJump()}
          className="w-12 h-9 text-center bg-slate-800 border border-slate-700 rounded-lg focus:ring-2 focus:ring-cyan-500/50 text-slate-200"
        />
        <span>/ {totalPages}</span>
      </div>
      <button
        onClick={onNext}
        disabled={currentPage + 1 >= totalPages}
        className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:bg-slate-700 disabled:opacity-50 transition-colors shadow-sm text-sm"
      >
        次のページ
      </button>
    </div>
  );
};

export default Pagination;
