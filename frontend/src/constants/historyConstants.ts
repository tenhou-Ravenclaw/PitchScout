/** 分析履歴の取得失敗メッセージ */
export const HISTORY_FETCH_ERROR_MESSAGE = "履歴の取得に失敗しました。";

/** 分析履歴削除関連メッセージ */
export const HISTORY_DELETE_MESSAGES = {
  errorLabel: "履歴削除失敗",
  errorUserMessage: "削除に失敗しました。",
  confirmMessage: "この履歴を削除しますか？",
} as const;

/** 履歴削除アニメーションの待機時間（ms） */
export const HISTORY_DELETE_ANIMATION_WAIT_MS = 300;

/** 履歴スワイプUIのしきい値 */
export const HISTORY_SWIPE_THRESHOLDS = {
  maxOffset: 250,
  deleteExecute: 150,
  revealDeleteButton: 60,
  revealOffset: 120,
} as const;
