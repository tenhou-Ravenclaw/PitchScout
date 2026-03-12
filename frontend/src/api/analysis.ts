import { API } from "./client";
import type { AnalysisResult } from "./types";

/**
 * マイクで録音した音声を解析する関数
 * @param blob - 録音データ
 * @param filename - サーバーに渡すファイル名（拡張子でフォーマット判定される）
 * @param noFalsetto - 裏声除外フラグ
 */
export const analyzeVoice = async (
  blob: Blob,
  filename: string = "recording.webm",
  noFalsetto: boolean = false,
): Promise<AnalysisResult> => {
  const formData = new FormData();
  formData.append("file", blob, filename);
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
