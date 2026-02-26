import { useErrorNotifier, ErrorNotifier } from "./useErrorNotifier";
import { useToast } from "./useToast";

/** Toast連携エラー通知フックの返り値です。 */
interface UseErrorToastNotifierResult {
  /** 現在表示中のToastメッセージ */
  toastMessage: string | null;
  /** 通常Toastを表示する関数 */
  showToast: (message: string, duration?: number) => void;
  /** APIエラーをユーザー向け文言に変換してToast表示する関数 */
  showApiErrorToast: (error: unknown, fallbackMessage: string) => void;
  /** Toastを閉じる関数 */
  hideToast: () => void;
  /** ログ出力とToast表示を行うエラー通知関数 */
  notifyError: ErrorNotifier;
}

/**
 * Toast表示と共通エラー通知を1つにまとめて提供します。
 * ページ側での `useToast` / `useErrorNotifier` の重複記述を減らすために使用します。
 *
 * @returns Toast状態とエラー通知関数
 */
export const useErrorToastNotifier = (): UseErrorToastNotifierResult => {
  const { toastMessage, showToast, showApiErrorToast, hideToast } = useToast();
  const { notifyError } = useErrorNotifier({ showApiErrorToast });

  return {
    toastMessage,
    showToast,
    showApiErrorToast,
    hideToast,
    notifyError,
  };
};
