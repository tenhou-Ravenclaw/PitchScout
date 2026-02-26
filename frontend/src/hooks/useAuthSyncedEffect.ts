import { useEffect } from "react";

/**
 * 認証状態に応じて、未認証時はリセットし、認証時は同期処理を実行する共通フック。
 */
interface UseAuthSyncedEffectParams {
  /** 認証状態 */
  isAuthenticated: boolean;
  /** 未認証時のリセット処理 */
  reset: () => void;
  /** 認証時の同期処理 */
  sync: () => Promise<void>;
}

/**
 * 認証連動の同期処理を実行します。
 */
export const useAuthSyncedEffect = ({
  isAuthenticated,
  reset,
  sync,
}: UseAuthSyncedEffectParams): void => {
  useEffect(() => {
    if (!isAuthenticated) {
      reset();
      return;
    }
    void sync();
  }, [isAuthenticated, reset, sync]);
};
