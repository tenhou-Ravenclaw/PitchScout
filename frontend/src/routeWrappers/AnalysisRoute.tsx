import React from "react";
import AnalysisResultPage from "../AnalysisResultPage";
import { useAppContext } from "../contexts/AppContext";

const AnalysisRoute: React.FC = () => {
  const { result } = useAppContext();

  return (
    <div className="min-h-screen bg-transparent">
      <AnalysisResultPage result={result} />
    </div>
  );
};

export default AnalysisRoute;
