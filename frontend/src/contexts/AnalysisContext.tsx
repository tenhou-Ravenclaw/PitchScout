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

/** ── アップロード時の進捗ステップ（5秒ごとに遷移、合計〜15秒想定） ── */
const STEPS_UPLOAD = [
  { progress: 10, label: "⚡ 音源を読み込み中..." },
  { progress: 35, label: "🎤 ピッチを解析中..." },
  { progress: 60, label: "🎵 もう少しで完了..." },
  { progress: 85, label: "📊 音域を計算中..." },
];

/** ── カラオケ録音（Demucs使用）時の進捗ステップ（25秒ごとに遷移、合計〜75秒想定） ── */
const STEPS_DEMUCS = [
  { progress: 20, label: "⚡ ボーカル分離を開始中..." },
  { progress: 45, label: "🎵 ボーカル抽出中（1〜2分かかります）..." },
  { progress: 70, label: "🎶 もうすぐ完了..." },
  { progress: 88, label: "📊 音域を解析中..." },
];

/** 全ステップ完了後の緩やかな進捗増加: 1秒ごとに 0.3% ずつ最大 95% まで */
const CREEP_INTERVAL_MS = 1000;
const CREEP_STEP = 0.3;
const CREEP_MAX = 95;

export const AnalysisProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stepLabel, setStepLabel] = useState("");
  
  // タイマーのIDを保持するための参照
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  /** ── 進捗タイマーの開始ロジック ──
   * 💡 モードに合わせて一定時間ごとに進捗率（%）とメッセージを更新します。
   *    全ステップ完了後は 95% まで緩やかに増加し、処理中であることをユーザーに示します。
   */
  const startAnalysisTimer = (mode: AnalysisMode) => {
    setIsAnalyzing(true);

    // すでにタイマーが動いていればクリア
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    if (mode === 'mic_record') {
      // マイク録音は短時間で終わるため固定値を表示
      setProgress(50);
      setStepLabel("解析中...");
      return;
    }

    const steps = mode === 'upload' ? STEPS_UPLOAD : STEPS_DEMUCS;
    // upload: 5秒ごと（合計15秒で最終ステップ）
    // karaoke_record: 25秒ごと（合計75秒で最終ステップ、Demucsの1〜2分に対応）
    const stepIntervalMs = mode === 'upload' ? 5000 : 25000;

    setProgress(steps[0].progress);
    setStepLabel(steps[0].label);

    // ステップインデックスをオブジェクトで保持してクロージャ越しに変更可能にする
    const idx = { current: 0 };

    timerRef.current = setInterval(() => {
      idx.current++;
      if (idx.current < steps.length) {
        // 次のステップへ遷移
        setProgress(steps[idx.current].progress);
        setStepLabel(steps[idx.current].label);
      } else {
        // 全ステップ完了 → ステップタイマーを止め、クリープタイマーに切り替える
        clearInterval(timerRef.current!);
        timerRef.current = setInterval(() => {
          setProgress((prev) => Math.min(prev + CREEP_STEP, CREEP_MAX));
        }, CREEP_INTERVAL_MS);
      }
    }, stepIntervalMs);
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