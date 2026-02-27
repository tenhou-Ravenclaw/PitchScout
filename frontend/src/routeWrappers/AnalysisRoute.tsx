import React from "react";
import { useAuth } from "../contexts/AuthContext";
import { useAppContext } from "../contexts/AppContext";
import AnalysisResultPage from "../pages/AnalysisResultPage";

export const AnalysisRoute: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const { result } = useAppContext();
  return (
    <div className="min-h-screen bg-transparent">
      <AnalysisResultPage result={result} isAuthenticated={isAuthenticated} />
    </div>
  );
};
