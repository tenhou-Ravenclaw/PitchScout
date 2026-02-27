import React from "react";
import { useNavigate } from "react-router-dom";
import { useAppContext } from "../contexts/AppContext";
import ResultPage from "../pages/ResultPage";

export const ResultRoute: React.FC = () => {
  const navigate = useNavigate();
  const { result, isFromHistory } = useAppContext();
  return (
    <ResultPage
      result={result}
      isFromHistory={isFromHistory}
      onBack={() => navigate(isFromHistory ? "/history" : "/menu")}
    />
  );
};
