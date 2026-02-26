import React, { useCallback, useRef, useState } from "react";
import { HISTORY_SWIPE_THRESHOLDS } from "../constants/historyConstants";

/** スワイプ操作中の座標情報 */
interface SwipeState {
  /** 開始時のX座標 */
  startX: number;
  /** 最新のX座標 */
  currentX: number;
}

/** 履歴スワイプフックの設定 */
interface UseHistorySwipeParams {
  /** スワイプ削除確定時に実行する処理 */
  onDelete: (recordId: string) => Promise<void>;
}

/**
 * 履歴カードのスワイプ操作（開始・移動・終了）を管理するフックです。
 *
 * @param params - スワイプ処理の設定
 * @returns スワイプ状態とイベントハンドラ群
 */
export const useHistorySwipe = ({ onDelete }: UseHistorySwipeParams): {
  swipedId: string | null;
  swipeOffset: number;
  handleTouchStart: (event: React.TouchEvent, recordId: string) => void;
  handleTouchMove: (event: React.TouchEvent, recordId: string) => void;
  handleTouchEnd: (recordId: string) => Promise<void>;
  cancelSwipe: () => void;
  isSwiping: (recordId: string) => boolean;
} => {
  const [swipedId, setSwipedId] = useState<string | null>(null);
  const [swipeOffset, setSwipeOffset] = useState<number>(0);
  const swipeStates = useRef<Record<string, SwipeState>>({});

  /** スワイプ開始を記録します。 */
  const handleTouchStart = useCallback((event: React.TouchEvent, recordId: string): void => {
    const touch = event.touches[0];
    swipeStates.current[recordId] = {
      startX: touch.clientX,
      currentX: touch.clientX,
    };
  }, []);

  /** スワイプ移動に応じて表示位置を更新します。 */
  const handleTouchMove = useCallback((event: React.TouchEvent, recordId: string): void => {
    const touch = event.touches[0];
    const state = swipeStates.current[recordId];
    if (!state) {
      return;
    }

    state.currentX = touch.clientX;
    const diff = state.startX - touch.clientX;

    if (diff > 0) {
      const offset = Math.min(diff, HISTORY_SWIPE_THRESHOLDS.maxOffset);
      setSwipeOffset(offset);
      setSwipedId(recordId);
      return;
    }

    setSwipeOffset(0);
    setSwipedId(null);
  }, []);

  /** スワイプ終了時にしきい値に応じた処理を実行します。 */
  const handleTouchEnd = useCallback(async (recordId: string): Promise<void> => {
    const state = swipeStates.current[recordId];
    if (!state) {
      return;
    }

    const diff = state.startX - state.currentX;

    if (diff > HISTORY_SWIPE_THRESHOLDS.deleteExecute) {
      delete swipeStates.current[recordId];
      setSwipedId(null);
      setSwipeOffset(0);
      await onDelete(recordId);
      return;
    }

    if (diff > HISTORY_SWIPE_THRESHOLDS.revealDeleteButton) {
      setSwipedId(recordId);
      setSwipeOffset(HISTORY_SWIPE_THRESHOLDS.revealOffset);
      delete swipeStates.current[recordId];
      return;
    }

    setSwipedId(null);
    setSwipeOffset(0);
    delete swipeStates.current[recordId];
  }, [onDelete]);

  /** スワイプ表示状態を解除します。 */
  const cancelSwipe = useCallback((): void => {
    setSwipedId(null);
    setSwipeOffset(0);
  }, []);

  /** 指定カードがドラッグ中かどうかを返します。 */
  const isSwiping = useCallback((recordId: string): boolean => {
    return !!swipeStates.current[recordId];
  }, []);

  return {
    swipedId,
    swipeOffset,
    handleTouchStart,
    handleTouchMove,
    handleTouchEnd,
    cancelSwipe,
    isSwiping,
  };
};
