/**
 * 【UploaderPage.tsx】
 * 役割：手持ちのカラオケ音源ファイル（mp3など）をアップロードして解析するためのページです。
 */
import React from "react";
import KaraokeUploader from "../components/KaraokeUploader";
import { AnalysisResult } from "../api";

/** UploaderPage が受け取るプロパティ */
interface UploaderPageProps {
  /** 戻るボタン押下時の処理 */
  onBack: () => void;
  /** 解析完了時の処理 */
  onComplete: (data: AnalysisResult) => void;
}

const UploaderPage: React.FC<UploaderPageProps> = ({ onBack, onComplete }) => {

  /** ── アップロード完了時の処理 ── */
  const handleResult = (data: AnalysisResult) => {
    onComplete(data);
  };

  return (
    <div className="min-h-screen bg-transparent p-8">
      {/* ── 戻るボタン ── */}
      <button
        onClick={onBack}
        className="btn-back-link mb-6"
      >
        &larr; メニューに戻る
      </button>

      {/* ── アップロードエリアのカード ── */}
      <div className="max-w-3xl mx-auto bg-slate-900/80 backdrop-blur-xl p-8 sm:p-12 rounded-3xl shadow-[0_0_30px_rgba(0,0,0,0.8)] border border-slate-700/50 relative overflow-hidden">
        {/* 背景装飾 */}
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-fuchsia-500/10 rounded-full blur-3xl pointer-events-none"></div>

        {/* ── アップローダーコンポーネントの呼び出し ── */}
        <KaraokeUploader onResult={handleResult} />
      </div>
    </div>
  );
};

export default UploaderPage;