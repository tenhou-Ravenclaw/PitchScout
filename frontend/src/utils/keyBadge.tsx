/**
 * 【keyBadge.tsx】
 * 役割：楽曲の推奨キー（±0など）を、歌いやすさ（fit）に応じて色分けして表示するバッジコンポーネント。
 * 設計：CSS クラス（.key-badge-* in index.css）で共有スタイルを管理し、JSX 側は className プロップのみを処理。
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

  // フィット感に基づいて CSS クラスを選択（index.css の @layer components で定義）
  let className: string;
  if (fit === "perfect") className = "key-badge-perfect";
  else if (fit === "good") className = "key-badge-good";
  else if (fit === "ok") className = "key-badge-ok";
  else if (fit === "hard") className = "key-badge-hard";
  else className = "key-badge-default";

  return <span className={className}>{label}</span>;
};

