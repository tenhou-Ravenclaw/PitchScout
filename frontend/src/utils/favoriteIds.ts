/**
 * お気に入り配列からID配列を抽出します。
 *
 * @param items - 変換対象の配列
 * @param selectId - 要素からIDを取り出す関数
 * @returns 抽出したID配列
 */
export const mapFavoriteIds = <T>(items: T[], selectId: (item: T) => number): number[] => {
  return items.map((item) => selectId(item));
};

/**
 * お気に入り一覧の取得とID抽出をまとめて実行します。
 *
 * @param fetchItems - 配列を取得する関数
 * @param selectId - 要素からIDを取り出す関数
 * @returns 抽出したID配列
 */
export const fetchFavoriteIds = async <T>(
  fetchItems: () => Promise<T[]>,
  selectId: (item: T) => number,
): Promise<number[]> => {
  const items = await fetchItems();
  return mapFavoriteIds(items, selectId);
};
