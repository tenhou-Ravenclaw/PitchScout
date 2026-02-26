import React, { Dispatch, SetStateAction, useCallback, useState } from "react";
import { AnalysisHistoryRecord, deleteAnalysisHistory } from "../api";
import {
  HISTORY_DELETE_MESSAGES,
  HISTORY_DELETE_ANIMATION_WAIT_MS,
  HISTORY_SWIPE_THRESHOLDS,
} from "../constants/historyConstants";
import { ErrorNotifier } from "./useErrorToastNotifier";
import { executeDeleteActionWithNotification } from "../utils/deleteAction";

/** 履歴削除フックの設定 */
interface UseHistoryDeleteParams {
  /** 履歴一覧の状態更新関数 */
  setHistory: Dispatch<SetStateAction<AnalysisHistoryRecord[]>>;
  /** エラー通知関数 */
  notifyError: ErrorNotifier;
}

/** スワイプ操作中の座標情報 */
interface SwipeState {
  /** 開始時のX座標 */
  startX: number;
  /** 最新のX座標 */
  currentX: number;
}

/**
 * 履歴削除（確認ダイアログ + アニメーション待機 + API削除）を管理するフックです。
 *
 * @param params - 削除処理に必要な設定
 * @returns 削除状態と削除ハンドラ
 */
export const useHistoryDelete = ({
  setHistory,
  notifyError,
}: UseHistoryDeleteParams): {
  deletingId: string | null;
  performDelete: (recordId: string) => Promise<void>;
  handleDelete: (event: React.MouseEvent, recordId: string) => Promise<void>;
  swipedId: string | null;
  swipeOffset: number;
  handleTouchStart: (event: React.TouchEvent, recordId: string) => void;
  handleTouchMove: (event: React.TouchEvent, recordId: string) => void;
  handleTouchEnd: (recordId: string) => Promise<void>;
  cancelSwipe: () => void;
  isSwiping: (recordId: string) => boolean;
} => {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [swipedId, setSwipedId] = useState<string | null>(null);
  const [swipeOffset, setSwipeOffset] = useState<number>(0);
  const swipeStates = React.useRef<Record<string, SwipeState>>({});

  /**
   * 確認済みの削除処理を実行します。
   *
   * @param recordId - 削除対象の履歴ID
   */
  const performDelete = useCallback(
    async (recordId: string): Promise<void> => {
      await executeDeleteActionWithNotification<string>({
        targetId: recordId,
        runDelete: deleteAnalysisHistory,
        errorConfig: {
          notifyError,
          errorLabel: HISTORY_DELETE_MESSAGES.errorLabel,
          errorUserMessage: HISTORY_DELETE_MESSAGES.errorUserMessage,
        },
        onBefore: async () => {
          setDeletingId(recordId);
          await new Promise((resolve) =>
            setTimeout(resolve, HISTORY_DELETE_ANIMATION_WAIT_MS),
          );
        },
        onSuccess: () => {
          setHistory((prev) => prev.filter((record) => record.id !== recordId));
        },
        onFinally: () => {
          setDeletingId(null);
        },
      });
    },
    [notifyError, setHistory],
  );

  /**
   * ボタンクリック時の削除処理（確認ダイアログ付き）です。
   *
   * @param event - クリックイベント
   * @param recordId - 削除対象の履歴ID
   */
  const handleDelete = useCallback(
    async (event: React.MouseEvent, recordId: string): Promise<void> => {
      event.stopPropagation();
      if (!window.confirm(HISTORY_DELETE_MESSAGES.confirmMessage)) {
        return;
      }
      await performDelete(recordId);
    },
    [performDelete],
  );

  /** スワイプ開始時の座標を保持します。 */
  const handleTouchStart = useCallback(
    (event: React.TouchEvent, recordId: string): void => {
      const touch = event.touches[0];
      swipeStates.current[recordId] = {
        startX: touch.clientX,
        currentX: touch.clientX,
      };
    },
    [],
  );

  /** スワイプ移動量に応じて削除UIの表示状態を更新します。 */
  const handleTouchMove = useCallback(
    (event: React.TouchEvent, recordId: string): void => {
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
    },
    [],
  );

  /** スワイプ終了時に削除・ボタン表示・キャンセルを判定します。 */
  const handleTouchEnd = useCallback(
    async (recordId: string): Promise<void> => {
      const state = swipeStates.current[recordId];
      if (!state) {
        return;
      }

      const diff = state.startX - state.currentX;

      if (diff > HISTORY_SWIPE_THRESHOLDS.deleteExecute) {
        delete swipeStates.current[recordId];
        setSwipedId(null);
        setSwipeOffset(0);
        await performDelete(recordId);
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
    },
    [performDelete],
  );

  /** 開いているスワイプ状態を閉じます。 */
  const cancelSwipe = useCallback((): void => {
    setSwipedId(null);
    setSwipeOffset(0);
  }, []);

  /** 指定レコードがスワイプ中かどうかを返します。 */
  const isSwiping = useCallback((recordId: string): boolean => {
    return !!swipeStates.current[recordId];
  }, []);

  return {
    deletingId,
    performDelete,
    handleDelete,
    swipedId,
    swipeOffset,
    handleTouchStart,
    handleTouchMove,
    handleTouchEnd,
    cancelSwipe,
    isSwiping,
  };
};
