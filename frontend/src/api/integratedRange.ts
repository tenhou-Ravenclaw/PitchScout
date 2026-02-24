import { API } from "./client";
import type { IntegratedVocalRange } from "./types";

export const getIntegratedVocalRange = async (limit = 20): Promise<IntegratedVocalRange> => {
  const res = await API.get<IntegratedVocalRange>("/analysis/integrated-range", { params: { limit } });
  return res.data;
};
