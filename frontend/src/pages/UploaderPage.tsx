/**
 * 【UploaderPage.tsx】
 * 役割：手持ちのカラオケ音源ファイル（mp3など）をアップロードして解析するためのページです。
 */
import React from "react";
import KaraokeUploader from "../components/features/KaraokeUploader";
import AnalysisCardShell from "../components/ui/cards/AnalysisCardShell";
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
      <AnalysisCardShell>
        {/* ── アップローダーコンポーネントの呼び出し ── */}
        <KaraokeUploader onResult={handleResult} />
      </AnalysisCardShell>
    </div>
  );
};

export default UploaderPage;