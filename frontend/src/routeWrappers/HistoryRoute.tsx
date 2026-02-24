/**
 * 【HistoryRoute.tsx】
 * 役割：履歴ページ（HistoryPage）の橋渡しです。
 * 過去のデータが選ばれたときに、それを「現在の結果」としてセットする重要なロジックを持ちます。
 */
import React from "react";
import { useNavigate } from "react-router-dom";
import HistoryPage from "../HistoryPage";
import { useAppContext } from "../contexts/AppContext";
import { AnalysisResult, AnalysisHistoryRecord } from "../api";

const HistoryRoute: React.FC = () => {
  const navigate = useNavigate();
  // 解析結果の保存機能と、「履歴から来た」というフラグの操作機能を取得
  const { setResult, setIsFromHistory } = useAppContext();

  /** ── 履歴から特定のデータが選ばれた時の処理 ── */
  const handleSelectRecord = (record: AnalysisHistoryRecord) => {
    if (record.result_json) {
      // 詳細データ（JSON）がある場合はそのままセット
      setResult(record.result_json);
    } else {
      // 簡易データしかない場合は、表示に必要な形に整えて（Mock）セットします
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
    // 「履歴からの表示」であることを記録し、結果画面（/result）へ移動します
    setIsFromHistory(true);
    navigate("/result");
  };

  return (
    <HistoryPage
      onLoginClick={() => navigate("/login")}
      onSelectRecord={handleSelectRecord}
    />
  );
};

export default HistoryRoute;