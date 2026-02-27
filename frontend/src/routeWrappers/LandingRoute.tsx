import React from "react";
import { useNavigate } from "react-router-dom";
import Landing from "../pages/Landing";

export const LandingRoute: React.FC = () => {
  const navigate = useNavigate();
  return (
    <Landing
      onRecordClick={() => navigate("/menu")}
      onHistoryClick={() => navigate("/history")}
    />
  );
};
