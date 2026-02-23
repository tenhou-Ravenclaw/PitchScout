/**
 * 【AnalysisRoute.tsx】
 * 役割：全体のデータ箱(Context)からデータを取り出し、画面に渡す「中継役」です。
 */

import React from "react";
// 💡 1つ上の階層(src)にある AnalysisResultPage.tsx を読み込みます
import AnalysisResultPage from "../AnalysisResultPage";
import { useAppContext } from "../contexts/AppContext";

const AnalysisRoute: React.FC = () => {
  // アプリ全体のデータ箱から「result」を取り出します
  const { result } = useAppContext();

  return (
    <div className="min-h-screen bg-transparent">
      {/* 💡 表示用コンポーネントにデータを渡します */}
      <AnalysisResultPage result={result} />
    </div>
  );
};

export default AnalysisRoute;