import { API } from "./client";
import type { TotalVocalRange } from "./types";

export const getTotalVocalRange = async (limit = 20): Promise<TotalVocalRange> => {
  const res = await API.get<TotalVocalRange>("/analysis/integrated-range", { params: { limit } });
  return res.data;
};
