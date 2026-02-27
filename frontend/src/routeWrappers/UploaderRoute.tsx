import React from "react";
import { useAnalysisCompletion } from "../routeWrappers/useAnalysisCompletion";
import UploaderPage from "../pages/UploaderPage";

export const UploaderRoute: React.FC = () => {
  const { handleComplete, goMenu } = useAnalysisCompletion();
  return (
    <UploaderPage
      onBack={goMenu}
      onComplete={handleComplete}
    />
  );
};
