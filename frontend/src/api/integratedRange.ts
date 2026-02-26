import { API } from "./client";
import type { IntegratedVocalRange } from "./types";

/**
 * 複数履歴を統合した声域分析結果を取得します。
 *
 * @param limit - 統合対象とする履歴件数
 * @returns 統合声域データ
 */
export const getIntegratedVocalRange = async (limit = 20): Promise<IntegratedVocalRange> => {
  const res = await API.get<IntegratedVocalRange>("/analysis/integrated-range", { params: { limit } });
  return res.data;
};
