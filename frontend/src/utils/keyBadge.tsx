/**
 * 【keyBadge.tsx】
 * 役割：楽曲の推奨キー（±0など）を、歌いやすさ（fit）に応じて色分けして表示するバッジコンポーネント。
 */

import React from "react";

/**
 * キーバッジを生成します。
 * @param key - キー変更の半音数（-2, 0, +3 など）
 * @param fit - フィット感（"perfect" | "good" | "ok" | "hard"）
 * @returns バッジのReact要素
 */
export const keyBadge = (key: number, fit?: string) => {
  const label = key === 0 ? "±0" : key > 0 ? `+${key}` : `${key}`;
  let color: string;
  
  // フィット感（perfect, good, ok, hard）に基づいて背景色と文字色を決定
  if (fit === "perfect") color = "bg-emerald-900/30 text-emerald-400 border border-emerald-500/30";
  else if (fit === "good") color = "bg-sky-900/30 text-sky-400 border border-sky-500/30";
  else if (fit === "ok") color = "bg-amber-900/30 text-amber-400 border border-amber-500/30";
  else if (fit === "hard") color = "bg-rose-900/30 text-rose-400 border border-rose-500/30";
  else color = "bg-slate-800 text-slate-500 border border-slate-700";
  
  return (
    <span className={`inline-flex items-center justify-center min-w-[2.5rem] h-6 rounded-full text-xs font-bold ${color}`}>
      {label}
    </span>
  );
};
