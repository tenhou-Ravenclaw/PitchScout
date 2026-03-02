import React from "react";
import { useNavigate } from "react-router-dom";
import MenuPage from "../pages/MenuPage";
import { useAnalysis } from "../contexts/AnalysisContext";

export const MenuRoute: React.FC = () => {
  const navigate = useNavigate();
  const { isAnalyzing } = useAnalysis();
  return (
    <MenuPage
      onNormalClick={() => navigate("/record")}
      onKaraokeClick={() => navigate("/karaoke")}
      onUploadClick={() => navigate("/upload")}
      onHistoryClick={() => navigate("/history")}
      isAnalyzing={isAnalyzing}
    />
  );
};
