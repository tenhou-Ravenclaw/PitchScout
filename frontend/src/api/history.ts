import { API } from "./client";
import type { AnalysisHistoryRecord } from "./types";

/**
 * 分析履歴一覧を取得します。
 *
 * @param limit - 取得上限件数
 * @returns 分析履歴レコード配列
 */
export const getAnalysisHistory = async (
  limit = 50,
): Promise<AnalysisHistoryRecord[]> => {
  const res = await API.get<AnalysisHistoryRecord[]>("/analysis/history", {
    params: { limit },
  });
  return res.data;
};

/**
 * 指定した分析履歴を削除します。
 *
 * @param recordId - 履歴レコードID
 * @returns APIの削除結果メッセージ
 */
export const deleteAnalysisHistory = async (
  recordId: string,
): Promise<{ message: string }> => {
  const res = await API.delete(`/analysis/history/${recordId}`);
  return res.data;
};
