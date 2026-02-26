/** 履歴削除アニメーションの待機時間（ms） */
export const HISTORY_DELETE_ANIMATION_WAIT_MS = 300;

/** 履歴スワイプUIのしきい値 */
export const HISTORY_SWIPE_THRESHOLDS = {
  maxOffset: 250,
  deleteExecute: 150,
  revealDeleteButton: 60,
  revealOffset: 120,
} as const;
