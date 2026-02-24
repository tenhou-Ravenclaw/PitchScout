/**
 * 【error.ts】
 * 役割：API 例外オブジェクトをユーザー向けメッセージへ変換するユーティリティ。
 */

/** API エラーに含まれる可能性のあるレスポンス構造 */
interface ApiErrorPayload {
  error?: string;
  detail?: string;
  message?: string;
}

/** API エラーに含まれる可能性のあるトップレベル構造 */
interface ApiLikeError {
  code?: string;
  message?: string;
  response?: {
    data?: ApiErrorPayload;
  };
}

/**
 * 例外オブジェクトをユーザー向けエラーメッセージに変換します。
 */
export function toUserMessage(error: unknown, fallback: string): string {
  const apiError = error as ApiLikeError;

  if (
    apiError?.message?.includes("timeout") ||
    apiError?.code === "ECONNABORTED"
  ) {
    return "⏱️ 処理時間が10分を超えたため、タイムアウトしました。時間をおいてもう一度お試しください。";
  }

  if (apiError?.message?.includes("Network Error")) {
    return "ネットワークエラーが発生しました。通信環境を確認してもう一度お試しください。";
  }

  return (
    apiError?.response?.data?.error ||
    apiError?.response?.data?.detail ||
    apiError?.response?.data?.message ||
    apiError?.message ||
    fallback
  );
}
