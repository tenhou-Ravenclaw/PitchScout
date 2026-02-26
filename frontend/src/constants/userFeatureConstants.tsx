import React from "react";
import { HeartIcon as HeartIconSolid } from "@heroicons/react/24/solid";

/** お気に入り機能の未ログイン時メッセージ */
export const FAVORITE_LOGIN_REQUIRED_MESSAGE = "ログインするとお気に入り機能を利用できます。";

/** お気に入りアーティスト関連メッセージ */
export const FAVORITE_ARTIST_MESSAGES = {
  syncErrorLabel: "お気に入り同期失敗",
  syncErrorUserMessage: "お気に入り情報の同期に失敗しました",
  toggleErrorLabel: "お気に入り操作失敗",
  toggleErrorUserMessage: "お気に入り操作に失敗しました",
} as const;

/** お気に入り楽曲関連メッセージ */
export const FAVORITE_SONG_MESSAGES = {
  syncErrorLabel: "お気に入り曲取得失敗",
  syncErrorUserMessage: "お気に入り曲の取得に失敗しました。",
  toggleErrorLabel: "お気に入り曲更新失敗",
  toggleErrorUserMessage: "お気に入り曲の更新に失敗しました。",
  deleteErrorLabel: "お気に入り削除失敗",
  deleteErrorUserMessage: "削除に失敗しました。",
} as const;

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
