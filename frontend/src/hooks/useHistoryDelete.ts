import React, { Dispatch, SetStateAction, useCallback, useState } from "react";
import { AnalysisHistoryRecord, deleteAnalysisHistory } from "../api";
import { HISTORY_DELETE_MESSAGES } from "../constants/historyMessages";
import { HISTORY_DELETE_ANIMATION_WAIT_MS } from "../constants/historyUiConstants";
import { ErrorNotifier } from "./useErrorNotifier";
import { executeDeleteAction } from "../utils/deleteAction";

/** 履歴削除フックの設定 */
interface UseHistoryDeleteParams {
  /** 履歴一覧の状態更新関数 */
  setHistory: Dispatch<SetStateAction<AnalysisHistoryRecord[]>>;
  /** エラー通知関数 */
  notifyError: ErrorNotifier;
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
} => {
  const [deletingId, setDeletingId] = useState<string | null>(null);

  /**
   * 確認済みの削除処理を実行します。
   *
   * @param recordId - 削除対象の履歴ID
   */
  const performDelete = useCallback(async (recordId: string): Promise<void> => {
    await executeDeleteAction<string>({
      targetId: recordId,
      runDelete: deleteAnalysisHistory,
      onBefore: async () => {
        setDeletingId(recordId);
        await new Promise((resolve) => setTimeout(resolve, HISTORY_DELETE_ANIMATION_WAIT_MS));
      },
      onSuccess: () => {
        setHistory((prev) => prev.filter((record) => record.id !== recordId));
      },
      onError: (error: unknown) => {
        notifyError(HISTORY_DELETE_MESSAGES.errorLabel, error, HISTORY_DELETE_MESSAGES.errorUserMessage);
      },
      onFinally: () => {
        setDeletingId(null);
      },
    });
  }, [notifyError, setHistory]);

  /**
   * ボタンクリック時の削除処理（確認ダイアログ付き）です。
   *
   * @param event - クリックイベント
   * @param recordId - 削除対象の履歴ID
   */
  const handleDelete = useCallback(async (event: React.MouseEvent, recordId: string): Promise<void> => {
    event.stopPropagation();
    if (!window.confirm(HISTORY_DELETE_MESSAGES.confirmMessage)) {
      return;
    }
    await performDelete(recordId);
  }, [performDelete]);

  return {
    deletingId,
    performDelete,
    handleDelete,
  };
};
