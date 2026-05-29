import { API } from "./client";
import type { TotalVocalRange, AnalysisTimeline } from "./types";

export const getTotalVocalRange = async (limit = 20): Promise<TotalVocalRange> => {
  const res = await API.get<TotalVocalRange>("/analysis/integrated-range", { params: { limit } });
  return res.data;
};

/**
 * GET /analysis/timeline — 直近 N 件の分析タイムラインと安定音域を取得する。
 *
 * @param limit 取得する件数（デフォルト 40）
 * @returns 古い順のタイムラインポイントと安定音域
 */
export const fetchAnalysisTimeline = async (limit = 40): Promise<AnalysisTimeline> => {
  const res = await API.get<AnalysisTimeline>("/analysis/timeline", { params: { limit } });
  return res.data;
};
