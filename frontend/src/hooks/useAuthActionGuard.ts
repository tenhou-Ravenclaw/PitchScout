import { useCallback } from "react";

/**
 * 認証ガードフックの設定です。
 */
interface UseAuthActionGuardParams {
  /** 現在の認証状態 */
  isAuthenticated: boolean;
  /** 未認証時に実行する処理 */
  onUnauthorized: () => void;
}

/**
 * 認証が必要な処理の実行前ガードを提供します。
 *
 * @param params - ガードの設定
 * @returns {{ ensureAuthenticated: () => boolean, guardAction: <T>(action: () => T) => T | undefined }}
 */
export const useAuthActionGuard = ({
  isAuthenticated,
  onUnauthorized,
}: UseAuthActionGuardParams): {
  ensureAuthenticated: () => boolean;
  guardAction: <T>(action: () => T) => T | undefined;
} => {
  /**
   * 認証状態を確認し、未認証時はハンドラを実行します。
   *
   * @returns true: 認証済み / false: 未認証
   */
  const ensureAuthenticated = useCallback((): boolean => {
    if (!isAuthenticated) {
      onUnauthorized();
      return false;
    }
    return true;
  }, [isAuthenticated, onUnauthorized]);

  /**
   * 認証済みの場合のみ指定アクションを実行します。
   *
   * @param action - 実行対象の処理
   * @returns 実行結果。未認証時は undefined
   */
  const guardAction = useCallback(<T,>(action: () => T): T | undefined => {
    if (!ensureAuthenticated()) {
      return undefined;
    }
    return action();
  }, [ensureAuthenticated]);

  return {
    ensureAuthenticated,
    guardAction,
  };
};
