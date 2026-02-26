/**
 * お気に入り状態に応じて追加または削除のAPI処理を実行します。
 *
 * @param isFavorite - 現在お気に入り済みかどうか
 * @param onAdd - 未登録時に実行する追加処理
 * @param onRemove - 登録済み時に実行する削除処理
 */
export const runFavoriteMutation = async (
  isFavorite: boolean,
  onAdd: () => Promise<unknown>,
  onRemove: () => Promise<unknown>,
): Promise<void> => {
  if (isFavorite) {
    await onRemove();
    return;
  }
  await onAdd();
};

/** お気に入りトグル実行時のエラー通知設定 */
interface FavoriteMutationErrorConfig {
  /** 開発者向けログラベル */
  errorLabel: string;
  /** ユーザー向けエラーメッセージ */
  errorUserMessage: string;
  /** 共通エラー通知関数 */
  notifyError: (label: string, error: unknown, message: string) => void;
}

/** お気に入り機能のエラー文言設定 */
interface FavoriteErrorMessages {
  /** 開発者向けログラベル */
  errorLabel: string;
  /** ユーザー向けエラーメッセージ */
  errorUserMessage: string;
}

/** お気に入りトグル拡張実行関数の引数 */
interface ExecuteFavoriteMutationParams {
  /** 現在お気に入り済みかどうか */
  isFavorite: boolean;
  /** 未登録時に実行する追加処理 */
  onAdd: () => Promise<unknown>;
  /** 登録済み時に実行する削除処理 */
  onRemove: () => Promise<unknown>;
  /** 成功時の後処理 */
  onSuccess?: () => void;
  /** 失敗時の後処理 */
  onError?: (error: unknown) => void;
  /** 完了時の後処理（成功/失敗共通） */
  onFinally?: () => void;
  /** エラー通知設定（指定時のみ通知を実行） */
  errorConfig?: FavoriteMutationErrorConfig;
}

/**
 * お気に入りトグル処理を実行し、成功・失敗・完了時の共通フローを提供します。
 *
 * @param params - 実行設定
 */
export const executeFavoriteMutation = async ({
  isFavorite,
  onAdd,
  onRemove,
  onSuccess,
  onError,
  onFinally,
  errorConfig,
}: ExecuteFavoriteMutationParams): Promise<void> => {
  try {
    await runFavoriteMutation(isFavorite, onAdd, onRemove);
    onSuccess?.();
  } catch (error) {
    if (errorConfig) {
      errorConfig.notifyError(errorConfig.errorLabel, error, errorConfig.errorUserMessage);
    }
    onError?.(error);
  } finally {
    onFinally?.();
  }
};

/**
 * お気に入り機能向けのエラー通知設定を作成します。
 *
 * @param notifyError - 共通エラー通知関数
 * @param messages - エラーメッセージ設定
 * @returns executeFavoriteMutation に渡せるエラー設定
 */
export const createFavoriteMutationErrorConfig = (
  notifyError: (label: string, error: unknown, message: string) => void,
  messages: FavoriteErrorMessages,
): FavoriteMutationErrorConfig => {
  return {
    notifyError,
    errorLabel: messages.errorLabel,
    errorUserMessage: messages.errorUserMessage,
  };
};

/**
 * 同期処理向けの共通エラーハンドラを作成します。
 *
 * @param notifyError - 共通エラー通知関数
 * @param messages - エラーメッセージ設定
 * @returns 同期失敗時に利用するエラーハンドラ
 */
export const createFavoriteSyncErrorHandler = (
  notifyError: (label: string, error: unknown, message: string) => void,
  messages: FavoriteErrorMessages,
): ((error: unknown) => void) => {
  return (error: unknown): void => {
    notifyError(messages.errorLabel, error, messages.errorUserMessage);
  };
};
