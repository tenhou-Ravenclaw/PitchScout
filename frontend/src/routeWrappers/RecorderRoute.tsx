import React from "react";
import { useAnalysisCompletion } from "../routeWrappers/useAnalysisCompletion";
import RecorderPage from "../pages/RecorderPage";

export const RecorderRoute: React.FC = () => {
  const { handleComplete, goMenu } = useAnalysisCompletion();
  return (
    <RecorderPage
      isKaraokeMode={false}
      onBack={goMenu}
      onComplete={handleComplete}
    />
  );
};
