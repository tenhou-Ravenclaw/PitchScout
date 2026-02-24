/**
 * 【ResultPage.tsx】
 * 役割：録音直後、または履歴から選んだ際に、真っ先に表示される「簡易結果」ページです。
 */
import React from "react";
import ResultView from "../components/features/ResultView";
import { AnalysisResult } from "../api";

/** ResultPage が受け取るプロパティ */
interface ResultPageProps {
  /** 解析結果データ */
  result: AnalysisResult | null;
  /** 履歴から遷移してきたかどうか */
  isFromHistory: boolean;
  /** 戻るボタン押下時の処理 */
  onBack: () => void;
}

const ResultPage: React.FC<ResultPageProps> = ({ result, isFromHistory, onBack }) => {

  return (
    <div className="min-h-screen bg-transparent p-8">
      {/* ── 戻るボタンの分岐 ──
         💡 履歴から来た場合は履歴一覧へ、録音直後ならメニュー画面へ戻るように制御しています。
      */}
      <button
        onClick={onBack}
        className="btn-back-link mb-6"
      >
        {isFromHistory ? "\u2190 履歴に戻る" : "\u2190 トップへ戻る"}
      </button>

      {/* ── 結果ビュー（ResultView）の表示 ── */}
      <div className="max-w-3xl mx-auto bg-transparent p-0 rounded-2xl">
        {result && <ResultView result={result} />}
      </div>
    </div>
  );
};

export default ResultPage;