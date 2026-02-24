/**
 * 【HomeRoute.tsx】
 * 役割：録音メニュー画面（Home）を表示するためのラッパーです。
 * 各ボタンが押された時の「行き先」を指示します。
 */
import React from "react";
import { useNavigate } from "react-router-dom";
import Home from "../Home";

const HomeRoute: React.FC = () => {
  const navigate = useNavigate();
  return (
    <Home
      // Home画面の各ボタンに遷移先のパス（URL）を割り当てます
      onNormalClick={() => navigate("/record")}
      onKaraokeClick={() => navigate("/karaoke")}
      onUploadClick={() => navigate("/upload")}
      onHistoryClick={() => navigate("/history")}
    />
  );
};

export default HomeRoute;