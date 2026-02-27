import React from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useAppContext } from "../contexts/AppContext";
import { AnalysisResult, AnalysisHistoryRecord } from "../api";
import HistoryPage from "../pages/HistoryPage";

export const HistoryRoute: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { setResult, setIsFromHistory } = useAppContext();

  const handleSelectRecord = (record: AnalysisHistoryRecord) => {
    if (record.result_json) {
      setResult(record.result_json);
    } else {
      const mockResult: AnalysisResult = {
        overall_min: record.vocal_range_min || "-",
        overall_max: record.vocal_range_max || "-",
        overall_min_hz: 0,
        overall_max_hz: 0,
        chest_min: record.vocal_range_min || undefined,
        chest_max: record.vocal_range_max || undefined,
        falsetto_max: record.falsetto_max || undefined,
      };
      setResult(mockResult);
    }
    setIsFromHistory(true);
    navigate("/result");
  };

  return (
    <HistoryPage
      isAuthenticated={isAuthenticated}
      onLoginClick={() => navigate("/login")}
      onSelectRecord={handleSelectRecord}
    />
  );
};
