import { useEffect, useRef } from "react";

/**
 * 認証付きデータロードフックの設定です。
 */
interface UseAuthenticatedDataLoaderParams<T> {
  /** ログイン状態 */
  isAuthenticated: boolean;
  /** データ取得処理 */
  fetchData: () => Promise<T>;
  /** 取得成功時の反映処理 */
  onSuccess: (data: T) => void;
  /** 取得失敗時の処理 */
  onError: (error: unknown) => void;
  /** ローディング状態更新関数 */
  setLoading: (loading: boolean) => void;
  /** 取得開始前に実行する処理 */
  onStart?: () => void;
}

/**
 * 認証状態に応じた初期データロードを実行します。
 * 未ログイン時はローディングを終了し、ログイン時のみ取得処理を実行します。
 *
 * @param params - ロードに必要な設定
 */
export const useAuthenticatedDataLoader = <T>({
  isAuthenticated,
  fetchData,
  onSuccess,
  onError,
  setLoading,
  onStart,
}: UseAuthenticatedDataLoaderParams<T>): void => {
  const fetchDataRef = useRef(fetchData);
  const onSuccessRef = useRef(onSuccess);
  const onErrorRef = useRef(onError);
  const setLoadingRef = useRef(setLoading);
  const onStartRef = useRef(onStart);

  useEffect(() => {
    fetchDataRef.current = fetchData;
    onSuccessRef.current = onSuccess;
    onErrorRef.current = onError;
    setLoadingRef.current = setLoading;
    onStartRef.current = onStart;
  }, [fetchData, onError, onStart, onSuccess, setLoading]);

  useEffect(() => {
    if (!isAuthenticated) {
      setLoadingRef.current(false);
      return;
    }

    let active = true;
    setLoadingRef.current(true);
    onStartRef.current?.();

    fetchDataRef.current()
      .then((data) => {
        if (!active) {
          return;
        }
        onSuccessRef.current(data);
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }
        onErrorRef.current(error);
      })
      .finally(() => {
        if (!active) {
          return;
        }
        setLoadingRef.current(false);
      });

    return () => {
      active = false;
    };
  }, [isAuthenticated]);
};
