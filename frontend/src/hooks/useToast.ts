import { useState, useCallback } from "react";
import { toUserMessage } from "../api";

/**
 * **useToast カスタムフック**
 * 
 * Toastメッセージの状態管理を共通化するカスタムフックです。
 * 複数のコンポーネントで重複していたToast表示ロジックを一元管理します。
 * 
 * @returns {{
 *   toastMessage: string | null,  // 現在表示中のメッセージ（nullなら非表示）
 *   showToast: (msg: string) => void,  // メッセージを表示する関数
 *   showApiErrorToast: (error: unknown, fallbackMessage: string) => void, // APIエラーを変換して表示する関数
 *   hideToast: () => void  // メッセージを非表示にする関数
 * }}
 * 
 * @example
 * ```tsx
 * const { toastMessage, showToast, hideToast } = useToast();
 * 
 * // エラー時にToastを表示
 * catch (err) {
 *   showToast(toUserMessage(err, "処理に失敗しました"));
 * }
 * 
 * // JSX内で条件付きレンダリング
 * {toastMessage && <Toast message={toastMessage} onClose={hideToast} />}
 * ```
 */
export const useToast = () => {
  const [message, setMessage] = useState<string | null>(null);

  /**
   * Toastメッセージを表示します。
   * 
   * @param msg - 表示するメッセージ文字列
   */
  const showToast = useCallback((msg: string) => {
    setMessage(msg);
  }, []);

  /**
   * API例外をユーザー向けメッセージに変換してToast表示します。
   *
   * @param error - 捕捉した例外オブジェクト
   * @param fallbackMessage - 例外内容がない場合のフォールバックメッセージ
   */
  const showApiErrorToast = useCallback((error: unknown, fallbackMessage: string) => {
    showToast(toUserMessage(error, fallbackMessage));
  }, [showToast]);

  /**
   * Toastメッセージを非表示にします（状態をnullにクリア）。
   */
  const hideToast = useCallback(() => {
    setMessage(null);
  }, []);

  return {
    toastMessage: message,
    showToast,
    showApiErrorToast,
    hideToast
  };
};
