/**
 * 【keyBadge.tsx】
 * 役割：楽曲の推奨キー（±0など）を、歌いやすさ（fit）に応じて色分けして表示するバッジコンポーネント。
 * 設計：CSS クラス（.key-badge-* in index.css）で共有スタイルを管理し、JSX 側は className プロップのみを処理。
 */

import React from "react";
import { KeyFit } from "../api/types";

/**
 * 楽曲キーのバッジコンポーネント
 * @param key キー変更の半音数
 * @param fit フィット感（KeyFit型）
 * @returns JSX.Element
 */
export const keyBadge = (key: number, fit?: KeyFit): React.ReactElement => {
  const label: string = key === 0 ? "±0" : key > 0 ? `+${key}` : `${key}`;

  let className: string;
  switch (fit) {
    case "perfect": className = "key-badge-perfect"; break;
    case "good": className = "key-badge-good"; break;
    case "ok": className = "key-badge-ok"; break;
    case "hard": className = "key-badge-hard"; break;
    default: className = "key-badge-default";
  }
  return <span className={className}>{label}</span>;
};

