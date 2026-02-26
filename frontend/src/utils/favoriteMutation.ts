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
