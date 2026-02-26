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
