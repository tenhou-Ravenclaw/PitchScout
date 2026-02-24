/**
 * 【FavoritesRoute.tsx】
 * 役割：お気に入りページ（FavoritesPage）を表示するためのラッパーです。
 * ログインが必要な場合の処理や、ユーザーの音域データを渡します。
 */
import React from "react";
import { useNavigate } from "react-router-dom";
import FavoritesPage from "../FavoritesPage";
import { useAppContext } from "../contexts/AppContext";

const FavoritesRoute: React.FC = () => {
  const navigate = useNavigate(); // 画面遷移用のフック
  const { userRange } = useAppContext(); // ユーザーの音域データを取得

  return (
    <FavoritesPage
      userRange={userRange}
      // ログインボタンが押されたらログイン画面へ飛ばす処理を渡します
      onLoginClick={() => navigate("/login")}
    />
  );
};

export default FavoritesRoute;