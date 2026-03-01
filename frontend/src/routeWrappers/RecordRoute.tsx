/**
 * 【RecordRoute.tsx】
 * 役割：メニュー画面（Record）とルーティングロジックを接続するルートラッパーです。
 * 特徴：遷移先パスの決定と、解析中フラグの受け渡しを担当します。
 */
import React from "react";
import { useNavigate } from "react-router-dom";
import Record from "../pages/Record";
import { useAnalysis } from "../contexts/AnalysisContext";

/**
 * RecordRoute
 *
 * Recordページにクリックハンドラと解析中状態を注入し、
 * 画面遷移をルート層で一元管理します。
 */
export const RecordRoute: React.FC = () => {
  const navigate = useNavigate();
  const { isAnalyzing } = useAnalysis();
  return (
    <Record
      onNormalClick={() => navigate("/record/normal")}
      onKaraokeClick={() => navigate("/record/karaoke")}
      onUploadClick={() => navigate("/record/upload")}
      onHistoryClick={() => navigate("/history")}
      isAnalyzing={isAnalyzing}
    />
  );
};
