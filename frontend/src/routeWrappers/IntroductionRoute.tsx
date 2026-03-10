import React from "react";
import { useNavigate } from "react-router-dom";
import Introduction from "../pages/Introduction";

export const IntroductionRoute: React.FC = () => {
  const navigate = useNavigate();

  return (
    <Introduction
      onRecordClick={() => navigate("/record")}
      onHistoryClick={() => navigate("/analysis")}
    />
  );
};
