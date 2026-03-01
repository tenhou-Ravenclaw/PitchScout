import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAppContext } from "../contexts/AppContext";
import { AnalysisResult } from "../api";

export const useAnalysisCompletion = () => {
  const navigate = useNavigate();
  const { setResult, setIsFromHistory } = useAppContext();

  const handleComplete = useCallback(
    (data: AnalysisResult) => {
      setResult(data);
      setIsFromHistory(false);
      navigate("/result");
    },
    [navigate, setIsFromHistory, setResult]
  );

  const goMenu = useCallback(() => {
    navigate("/record");
  }, [navigate]);

  return { handleComplete, goMenu };
};
