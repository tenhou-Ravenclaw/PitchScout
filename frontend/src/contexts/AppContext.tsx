/**
 * 【AppContext.tsx】
 * 役割：アプリ全体の「記憶（グローバルステート）」を管理します。
 * 解析結果、ユーザーの音域、検索ワードなど、ページをまたいで保持したいデータを扱います。
 */
import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from "react";
// APIから型定義を読み込みます
import { AnalysisResult, UserRange } from "../api";

/** ── ブラウザに音域を保存するための鍵（Key） ── */
const RANGE_STORAGE_KEY = "voiceRange";

/** ── 保存された音域を読み出す関数 ── */
function loadSavedRange(): UserRange | null {
  try {
    const saved = localStorage.getItem(RANGE_STORAGE_KEY);
    if (saved) return JSON.parse(saved) as UserRange;
  } catch { /* ignore */ }
  return null;
}

/** ── 音域をブラウザに保存する関数 ── */
function saveRange(range: UserRange) {
  localStorage.setItem(RANGE_STORAGE_KEY, JSON.stringify(range));
}

/** ── 共有データの設計図 ── */
interface AppContextType {
  result: AnalysisResult | null; // 最新の解析結果
  setResult: React.Dispatch<React.SetStateAction<AnalysisResult | null>>;
  userRange: UserRange | null;    // ユーザーの音域（楽曲とのマッチングに使用）
  setUserRange: React.Dispatch<React.SetStateAction<UserRange | null>>;
  searchQuery: string;           // 楽曲検索の入力ワード
  setSearchQuery: React.Dispatch<React.SetStateAction<string>>;
  isFromHistory: boolean;        // 履歴画面から来たかどうか
  setIsFromHistory: React.Dispatch<React.SetStateAction<boolean>>;
  clearRange: () => void;        // 保存された音域を消去
}

const AppContext = createContext<AppContextType>(null!);

export const useAppContext = () => useContext(AppContext);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // ── 状態の初期化 ──
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [userRange, setUserRange] = useState<UserRange | null>(loadSavedRange); // 初期値としてブラウザから読み込む
  const [searchQuery, setSearchQuery] = useState("");
  const [isFromHistory, setIsFromHistory] = useState(false);

  /**
   * ── 解析結果が変わった時の自動保存 ──
   * 💡 新しい解析結果が出たら、そこから地声・裏声の音域を抜き出して自動で userRange を更新し、保存します。
   */
  useEffect(() => {
    if (result && !result.error && result.chest_min_hz && result.chest_max_hz) {
      const range: UserRange = {
        chest_min_hz: result.chest_min_hz,
        chest_max_hz: result.chest_max_hz,
      };
      if (result.falsetto_max_hz) {
        range.falsetto_max_hz = result.falsetto_max_hz;
      }
      setUserRange(range);
      saveRange(range);
    }
  }, [result]);

  /** ── 音域データのクリア ── */
  const clearRange = useCallback(() => {
    setUserRange(null);
    localStorage.removeItem(RANGE_STORAGE_KEY);
  }, []);

  /** ── パフォーマンス最適化 (useMemo) ──
   * 共有するデータ一式をまとめ、必要な時だけ再作成します。
   */
  const value = useMemo(
    () => ({ result, setResult, userRange, setUserRange, searchQuery, setSearchQuery, isFromHistory, setIsFromHistory, clearRange }),
    [result, userRange, searchQuery, isFromHistory, clearRange]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};