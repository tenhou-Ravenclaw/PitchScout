import { Dispatch, SetStateAction, useCallback } from "react";
import { ErrorNotifier } from "./useErrorNotifier";
import { useSyncedFavoriteSet } from "./useSyncedFavoriteSet";
import { createFavoriteSyncErrorHandler } from "../utils/favoriteMutation";
import { fetchFavoriteIds } from "../utils/favoriteIds";

/** お気に入り同期フックの設定です。 */
interface UseSyncedFavoriteIdsParams<T> {
  /** 認証状態 */
  isAuthenticated: boolean;
  /** 同期先のSet状態更新関数 */
  setIdSet: Dispatch<SetStateAction<Set<number>>>;
  /** お気に入り配列を取得する関数 */
  fetchItems: () => Promise<T[]>;
  /** 要素からIDを取り出す関数 */
  selectId: (item: T) => number;
  /** 共通エラー通知関数 */
  notifyError: ErrorNotifier;
  /** 同期失敗時のログラベル */
  syncErrorLabel: string;
  /** 同期失敗時のユーザー向けメッセージ */
  syncErrorUserMessage: string;
}

/**
 * お気に入りIDの同期処理（取得 + ID抽出 + エラー通知）を共通化するフックです。
 *
 * @param params - 同期処理設定
 */
export const useSyncedFavoriteIds = <T>({
  isAuthenticated,
  setIdSet,
  fetchItems,
  selectId,
  notifyError,
  syncErrorLabel,
  syncErrorUserMessage,
}: UseSyncedFavoriteIdsParams<T>): void => {
  const fetchIds = useCallback(async (): Promise<number[]> => {
    return fetchFavoriteIds(fetchItems, selectId);
  }, [fetchItems, selectId]);

  const handleSyncError = useCallback(
    createFavoriteSyncErrorHandler(notifyError, {
      errorLabel: syncErrorLabel,
      errorUserMessage: syncErrorUserMessage,
    }),
    [notifyError, syncErrorLabel, syncErrorUserMessage],
  );

  useSyncedFavoriteSet({
    isAuthenticated,
    setIdSet,
    fetchIds,
    onSyncError: handleSyncError,
  });
};
