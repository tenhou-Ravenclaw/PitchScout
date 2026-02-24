/**
 * 【AnalysisRoute.tsx】
 * 役割：詳細解析結果ページ（AnalysisResultPage）を表示するためのラッパーです。
 * AppContext から最新の解析結果（result）を取り出して渡します。
 */
import React from "react";
import AnalysisResultPage from "../AnalysisResultPage";
import { useAppContext } from "../contexts/AppContext";

const AnalysisRoute: React.FC = () => {
  // アプリ全体の共有データから解析結果を取得します
  const { result } = useAppContext();

  return (
    <div className="min-h-screen bg-transparent">
      {/* 取得した解析結果をページコンポーネントに渡して表示します */}
      <AnalysisResultPage result={result} />
    </div>
  );
};

export default AnalysisRoute;