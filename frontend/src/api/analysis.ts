import { API } from "./client";
import type { AnalysisResult } from "./types";

/** マイクで録音した音声を解析する関数 */
export const analyzeVoice = async (blob: Blob, noFalsetto: boolean = false): Promise<AnalysisResult> => {
  const formData = new FormData();
  formData.append("file", blob, "recording.webm");
  if (noFalsetto) formData.append("no_falsetto", "true");
  const res = await API.post<AnalysisResult>("/analyze", formData);
  return res.data;
};

// 重複定義を削除
/** アップロードした音源（カラオケなど）を解析する関数 */
export const analyzeKaraoke = async (
  file: File | Blob,
  filename: string,
  noFalsetto: boolean = false,
): Promise<AnalysisResult> => {
  const formData = new FormData();
  formData.append("file", file, filename);
  if (noFalsetto) formData.append("no_falsetto", "true");
  const res = await API.post<AnalysisResult>("/analyze-karaoke", formData);
  return res.data;
};
