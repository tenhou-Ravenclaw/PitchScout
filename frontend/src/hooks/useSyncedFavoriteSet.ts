import { Dispatch, SetStateAction, useCallback } from "react";
import { useAuthSyncedEffect } from "./useAuthSyncedEffect";

/**
 * 認証連動のお気に入りID同期フックの設定です。
 */
interface UseSyncedFavoriteSetParams {
  /** 認証状態 */
  isAuthenticated: boolean;
  /** 同期先の Set 状態更新関数 */
  setIdSet: Dispatch<SetStateAction<Set<number>>>;
  /** サーバーからお気に入りID配列を取得する関数 */
  fetchIds: () => Promise<number[]>;
  /** 同期エラー時の通知関数 */
  onSyncError: (error: unknown) => void;
}

/**
 * お気に入りIDの Set 状態を、認証状態に合わせて自動同期します。
 * 未認証時は空にリセットし、認証時は fetchIds の結果で上書きします。
 *
 * @param params - 同期に必要な設定
 */
export const useSyncedFavoriteSet = ({
  isAuthenticated,
  setIdSet,
  fetchIds,
  onSyncError,
}: UseSyncedFavoriteSetParams): void => {
  const reset = useCallback(() => {
    setIdSet(new Set());
  }, [setIdSet]);

  const sync = useCallback(async () => {
    try {
      const ids = await fetchIds();
      setIdSet(new Set(ids));
    } catch (error) {
      onSyncError(error);
    }
  }, [fetchIds, onSyncError, setIdSet]);

  useAuthSyncedEffect({
    isAuthenticated,
    reset,
    sync,
  });
};
