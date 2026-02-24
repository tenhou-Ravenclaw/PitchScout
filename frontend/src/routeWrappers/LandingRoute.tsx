/**
 * 【LandingRoute.tsx】
 * 役割：アプリの最初の二択画面（Landing）のラッパーです。
 */
import React from "react";
import { useNavigate } from "react-router-dom";
import Landing from "../Landing";

const LandingRoute: React.FC = () => {
  const navigate = useNavigate();
  return (
    <Landing
      // 大きな二つのエリアが押された時の遷移先を定義します
      onRecordClick={() => navigate("/menu")}
      onHistoryClick={() => navigate("/history")}
    />
  );
};

export default LandingRoute;