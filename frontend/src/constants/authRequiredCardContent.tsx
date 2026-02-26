import React from "react";
import { HeartIcon as HeartIconSolid } from "@heroicons/react/24/solid";

/** AuthRequiredCard の表示内容定義 */
export interface AuthRequiredCardContent {
  /** 表示タイトル */
  title: string;
  /** 説明メッセージ */
  message: string;
  /** 表示アイコン */
  icon: React.ReactNode;
}

/** お気に入りページの未ログイン表示内容 */
export const FAVORITES_AUTH_REQUIRED_CONTENT: AuthRequiredCardContent = {
  title: "お気に入り",
  message: "ログインするとお気に入りの楽曲を保存できます",
  icon: <HeartIconSolid className="w-12 h-12 text-rose-500/50" />,
};

/** 履歴ページの未ログイン表示内容 */
export const HISTORY_AUTH_REQUIRED_CONTENT: AuthRequiredCardContent = {
  title: "分析履歴",
  message: "ログインすると過去の分析履歴を確認できます",
  icon: (
    <svg className="w-12 h-12 text-cyan-500/50" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
};
