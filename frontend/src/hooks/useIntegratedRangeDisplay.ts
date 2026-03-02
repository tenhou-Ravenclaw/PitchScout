import { useEffect, useState } from "react";
import {
  AnalysisResult,
  IntegratedVocalRange,
  getIntegratedVocalRange,
  toUserMessage,
} from "../api";

/** 共通表示データフックの引数 */
interface UseIntegratedRangeDisplayParams {
  /** 単発解析結果 */
  result: AnalysisResult | null;
  /** ログイン中かどうか */
  isAuthenticated: boolean;
  /** 取得件数の上限 */
  limit?: number;
  /** 取得失敗時の通知コールバック */
  onError?: (message: string) => void;
}

/** 共通表示データフックの返り値 */
interface UseIntegratedRangeDisplayResult {
  /** 画面表示に使う分析データ（統合優先） */
  displayData: AnalysisResult | IntegratedVocalRange | null;
  /** 統合音域データ（未取得時はnull） */
  integratedRange: IntegratedVocalRange | null;
  /** 統合音域を使用中かどうか */
  useIntegrated: boolean;
  /** 統合音域取得中かどうか */
  loadingIntegrated: boolean;
}

/**
 * 解析結果表示用データ（単発/統合）を共通で解決するフック。
 *
 * ログイン中は統合音域を取得し、取得済みなら統合データを優先して返す。
 * 非ログイン時、または取得前/取得失敗時は単発解析結果を返す。
 */
export const useIntegratedRangeDisplay = ({
  result,
  isAuthenticated,
  limit = 20,
  onError,
}: UseIntegratedRangeDisplayParams): UseIntegratedRangeDisplayResult => {
  const [integratedRange, setIntegratedRange] = useState<IntegratedVocalRange | null>(null);
  const [loadingIntegrated, setLoadingIntegrated] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;

    const fetchIntegratedRange = async (): Promise<void> => {
      if (!isAuthenticated) {
        if (isMounted) {
          setIntegratedRange(null);
          setLoadingIntegrated(false);
        }
        return;
      }

      setLoadingIntegrated(true);
      try {
        const data = await getIntegratedVocalRange(limit);
        if (isMounted) {
          setIntegratedRange(data);
        }
      } catch (error) {
        if (isMounted) {
          setIntegratedRange(null);
        }
        onError?.(toUserMessage(error, "統合音域の取得に失敗しました"));
      } finally {
        if (isMounted) {
          setLoadingIntegrated(false);
        }
      }
    };

    fetchIntegratedRange();

    return () => {
      isMounted = false;
    };
  }, [isAuthenticated, limit, onError]);

  const useIntegrated = isAuthenticated && !!integratedRange;
  const displayData = useIntegrated ? integratedRange : result;

  return {
    displayData,
    integratedRange,
    useIntegrated,
    loadingIntegrated,
  };
};
