import React from "react";
import { useAnalysisCompletion } from "../routeWrappers/useAnalysisCompletion";
import RecorderPage from "../pages/RecorderPage";

export const KaraokeRoute: React.FC = () => {
  const { handleComplete, goMenu } = useAnalysisCompletion();
  return (
    <RecorderPage
      isKaraokeMode={true}
      onBack={goMenu}
      onComplete={handleComplete}
    />
  );
};
