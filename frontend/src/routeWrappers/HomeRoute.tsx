import React from "react";
import { useNavigate } from "react-router-dom";
import Home from "../pages/Home";

export const HomeRoute: React.FC = () => {
  const navigate = useNavigate();
  return (
    <Home
      onRecordClick={() => navigate("/menu")}
      onHistoryClick={() => navigate("/history")}
    />
  );
};
