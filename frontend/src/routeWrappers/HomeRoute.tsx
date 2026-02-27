import React from "react";
import { useNavigate } from "react-router-dom";
import Home from "../pages/Home";
import { useAnalysis } from "../contexts/AnalysisContext";

export const HomeRoute: React.FC = () => {
  const navigate = useNavigate();
  const { isAnalyzing } = useAnalysis();
  return (
    <Home
      onNormalClick={() => navigate("/record")}
      onKaraokeClick={() => navigate("/karaoke")}
      onUploadClick={() => navigate("/upload")}
      onHistoryClick={() => navigate("/history")}
      isAnalyzing={isAnalyzing}
    />
  );
};
