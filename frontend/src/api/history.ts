import { API } from "./client";
import type { AnalysisHistoryRecord } from "./types";

export const getAnalysisHistory = async (limit = 50): Promise<AnalysisHistoryRecord[]> => {
  const res = await API.get<AnalysisHistoryRecord[]>("/analysis/history", { params: { limit } });
  return res.data;
};

export const deleteAnalysisHistory = async (recordId: string): Promise<{ message: string }> => {
  const res = await API.delete(`/analysis/history/${recordId}`);
  return res.data;
};
