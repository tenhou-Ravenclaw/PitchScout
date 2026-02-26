/**
 * 既存の Set を破壊せず、要素を追加した新しい Set を返します。
 *
 * @param source - 元となる Set
 * @param value - 追加する値
 * @returns 要素追加後の新しい Set
 */
export const addToSet = <T>(source: Set<T>, value: T): Set<T> => {
  const next = new Set(source);
  next.add(value);
  return next;
};

/**
 * 既存の Set を破壊せず、要素を削除した新しい Set を返します。
 *
 * @param source - 元となる Set
 * @param value - 削除する値
 * @returns 要素削除後の新しい Set
 */
export const removeFromSet = <T>(source: Set<T>, value: T): Set<T> => {
  const next = new Set(source);
  next.delete(value);
  return next;
};

/**
 * 既存の Set を破壊せず、要素の有無を反転した新しい Set を返します。
 *
 * @param source - 元となる Set
 * @param value - 反転対象の値
 * @returns 反転後の新しい Set
 */
export const toggleInSet = <T>(source: Set<T>, value: T): Set<T> => {
  return source.has(value) ? removeFromSet(source, value) : addToSet(source, value);
};
