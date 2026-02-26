/**
 * 削除処理テンプレートの設定です。
 */
interface ExecuteDeleteActionParams<IdType> {
  /** 削除対象のID */
  targetId: IdType;
  /** 実際の削除API処理 */
  runDelete: (id: IdType) => Promise<unknown>;
  /** 削除前に実行する処理 */
  onBefore?: (id: IdType) => Promise<void> | void;
  /** 削除成功時に実行する処理 */
  onSuccess?: (id: IdType) => Promise<void> | void;
  /** 削除失敗時に実行する処理 */
  onError?: (error: unknown, id: IdType) => Promise<void> | void;
  /** 削除後に必ず実行する処理 */
  onFinally?: (id: IdType) => Promise<void> | void;
}

/**
 * 削除処理の共通フロー（before → runDelete → success / error → finally）を実行します。
 *
 * @param params - 削除フローの各処理
 */
export const executeDeleteAction = async <IdType>({
  targetId,
  runDelete,
  onBefore,
  onSuccess,
  onError,
  onFinally,
}: ExecuteDeleteActionParams<IdType>): Promise<void> => {
  await onBefore?.(targetId);

  try {
    await runDelete(targetId);
    await onSuccess?.(targetId);
  } catch (error) {
    await onError?.(error, targetId);
  } finally {
    await onFinally?.(targetId);
  }
};
