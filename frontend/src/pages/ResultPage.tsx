/**
 * 【ResultPage.tsx】
 * 役割：録音直後、または履歴から選んだ際に、真っ先に表示される「簡易結果」ページです。
 */
import React from "react";
import { useNavigate } from "react-router-dom";
// 結果のビジュアル表示を担当するパーツを読み込みます
import ResultView from "../components/ResultView";
import { useAppContext } from "../contexts/AppContext";

const ResultPage: React.FC = () => {
  const navigate = useNavigate();
  // 共有データから「解析結果」と「それが履歴からのものか」という情報を取得します
  const { result, isFromHistory } = useAppContext();

  return (
    <div className="min-h-screen bg-transparent p-8">
      {/* ── 戻るボタンの分岐 ──
         💡 履歴から来た場合は履歴一覧へ、録音直後ならメニュー画面へ戻るように制御しています。
      */}
      <button
        onClick={() => navigate(isFromHistory ? "/history" : "/menu")}
        className="mb-6 text-slate-500 hover:text-cyan-400 font-bold flex items-center gap-2 transition-colors"
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