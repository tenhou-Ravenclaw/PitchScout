/**
 * 【SearchBar.tsx】
 * 楽曲名・アーティスト名を検索するための入力フォームです。
 * クリアボタン、検索アイコン、フォーカス時の光るエフェクトを含みます。
 */

import React from 'react';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';

interface SearchBarProps {
  /**
   * 検索入力の現在値
   */
  value: string;

  /**
   * 検索入力の変更ハンドラ
   */
  onChange: (value: string) => void;

  /**
   * フォーム送信時（Enter キー or 検索ボタン）
   */
  onSubmit: (query: string) => void;

  /**
   * プレースホルダーテキスト（任意）
   */
  placeholder?: string;
}

/**
 * SearchBar Component
 * 
 * @example
 * <SearchBar
 *   value={searchInput}
 *   onChange={setSearchInput}
 *   onSubmit={handleSearch}
 *   placeholder="楽曲名・アーティスト名で検索..."
 * />
 */
const SearchBar: React.FC<SearchBarProps> = ({
  value,
  onChange,
  onSubmit,
  placeholder = "楽曲名・アーティスト名で検索..."
}) => {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(value);
  };

  const handleClear = () => {
    onChange("");
    onSubmit("");
  };

  return (
    <form
      className="relative w-full group"
      onSubmit={handleSubmit}
    >
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full pl-10 pr-10 py-3 bg-slate-900/40 backdrop-blur-md border border-cyan-500/30 rounded-lg text-slate-200 focus:outline-none focus:ring-1 focus:ring-cyan-400 focus:border-cyan-400 focus:shadow-[0_0_15px_rgba(34,211,238,0.6)] placeholder-slate-500 transition-all duration-300"
      />
      <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 group-focus-within:text-cyan-400 transition-colors" />

      {/* クリアボタン */}
      {value && (
        <button
          type="button"
          onClick={handleClear}
          className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 flex items-center justify-center text-slate-500 hover:text-cyan-400 transition-colors"
        >
          ✕
        </button>
      )}
    </form>
  );
};

export default SearchBar;
