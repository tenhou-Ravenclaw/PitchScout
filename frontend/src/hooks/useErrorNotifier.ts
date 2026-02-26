import { useCallback } from "react";

/** エラー通知関数の型定義 */
interface UseErrorNotifierParams {
  /** API例外をToast表示する関数 */
  showApiErrorToast: (error: unknown, fallbackMessage: string) => void;
}

/**
 * ログ出力とユーザー通知を同時に行う共通フックです。
 * 表示には、呼び出し元で管理しているToast関数を利用します。
 *
 * @param params - エラー表示に利用する関数群
 * @returns {{
 *   notifyError: (logLabel: string, error: unknown, fallbackMessage: string) => void
 * }}
 *
 * @example
 * ```tsx
 * const { notifyError } = useErrorNotifier();
 *
 * try {
 *   await fetchData();
 * } catch (error) {
 *   notifyError("データ取得失敗", error, "データ取得に失敗しました。");
 * }
 * ```
 */
export const useErrorNotifier = ({ showApiErrorToast }: UseErrorNotifierParams) => {

  /**
   * エラーをコンソールへ記録し、ユーザーへToast通知します。
   *
   * @param logLabel - 開発者向けログラベル
   * @param error - 捕捉した例外オブジェクト
   * @param fallbackMessage - ユーザー向けフォールバックメッセージ
   */
  const notifyError = useCallback((logLabel: string, error: unknown, fallbackMessage: string) => {
    console.error(logLabel, error);
    showApiErrorToast(error, fallbackMessage);
  }, [showApiErrorToast]);

  return {
    notifyError,
  };
};
