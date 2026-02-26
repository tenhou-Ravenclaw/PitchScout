/**
 * 【AnalysisContext.tsx】
 * 役割：音声解析中の「進捗状況（プログレスバー）」や「メッセージ」を管理します。
 * 特徴：解析モード（アップロード・カラオケ録音など）に応じた疑似的なタイマー進行を制御します。
 */
import React, { createContext, useState, useContext, ReactNode, useRef } from 'react';

/** ── 解析モードの型定義 ── */
export type AnalysisMode = 'upload' | 'karaoke_record' | 'mic_record' | null;

/** ── 共有データの設計図 ── */
interface AnalysisContextType {
  isAnalyzing: boolean; // 解析中かどうか
  setIsAnalyzing: (isAnalyzing: boolean) => void;
  progress: number;     // プログレスバーの数値（0～100）
  setProgress: (progress: number | ((prev: number) => number)) => void;
  stepLabel: string;    // 画面に表示する「〇〇中...」というメッセージ
  setStepLabel: (label: string) => void;
  startAnalysisTimer: (mode: AnalysisMode) => void; // タイマー開始
  stopAnalysisTimer: () => void;                    // タイマー停止
}

const AnalysisContext = createContext<AnalysisContextType | undefined>(undefined);

/** ── アップロード時の進捗ステップ ── */
const STEPS_UPLOAD = [
  { progress: 10, label: "⚡ 音源を読み込み中..." },
  { progress: 35, label: "🎤 超高速ボーカル分離中..." },
  { progress: 60, label: "🎵 もう少しで完了..." },
  { progress: 85, label: "📊 音域を解析中..." },
];

/** ── カラオケ録音（Demucs使用）時の進捗ステップ ── */
const STEPS_DEMUCS = [
  { progress: 20, label: "⚡ 超高速ボーカル分離中..." },
  { progress: 50, label: "🎵 ボーカル抽出中（1〜2分）..." },
  { progress: 75, label: "🎶 もうすぐ完了..." },
  { progress: 90, label: "📊 音域を解析中..." },
];

export const AnalysisProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stepLabel, setStepLabel] = useState("");
  
  // タイマーのIDを保持するための参照
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  /** ── 進捗タイマーの開始ロジック ──
   * 💡 モードに合わせて一定時間ごとに進捗率（%）とメッセージを更新します。
   */
  const startAnalysisTimer = (mode: AnalysisMode) => {
    setIsAnalyzing(true);
    let stepIndex = 0;
    
    // すでにタイマーが動いていればクリア
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    
    if (mode === 'upload') {
      setProgress(STEPS_UPLOAD[0].progress);
      setStepLabel(STEPS_UPLOAD[0].label);
      timerRef.current = setInterval(() => {
        stepIndex++;
        if (stepIndex < STEPS_UPLOAD.length) {
          setProgress(STEPS_UPLOAD[stepIndex].progress);
          setStepLabel(STEPS_UPLOAD[stepIndex].label);
        }
      }, 8000); // 8秒ごとに次のステップへ
    } else if (mode === 'karaoke_record') {
      setProgress(STEPS_DEMUCS[0].progress);
      setStepLabel(STEPS_DEMUCS[0].label);
      timerRef.current = setInterval(() => {
        stepIndex++;
        if (stepIndex < STEPS_DEMUCS.length) {
          setProgress(STEPS_DEMUCS[stepIndex].progress);
          setStepLabel(STEPS_DEMUCS[stepIndex].label);
        }
      }, 8000);
    } else if (mode === 'mic_record') {
      // マイク録音は一瞬で終わるため、固定値を表示
      setProgress(50);
      setStepLabel("解析中...");
    }
  };

  /** ── タイマーの停止 ── */
  const stopAnalysisTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  React.useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, []);

  return (
    <AnalysisContext.Provider value={{ 
      isAnalyzing, setIsAnalyzing, 
      progress, setProgress, 
      stepLabel, setStepLabel,
      startAnalysisTimer, stopAnalysisTimer
    }}>
      {children}
    </AnalysisContext.Provider>
  );
};

/** ── 他の部品からデータを使うためのフック ── */
export const useAnalysis = () => {
  const context = useContext(AnalysisContext);
  if (!context) {
    throw new Error('useAnalysis must be used within an AnalysisProvider');
  }
  return context;
};