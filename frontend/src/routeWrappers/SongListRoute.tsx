/**
 * 【SongListRoute.tsx】
 * 役割：楽曲一覧ページ（SongListPage）のラッパーです。
 * 検索キーワード（searchQuery）や音域データを共有データから取得して渡します。
 */
import React from "react";
import { useNavigate } from "react-router-dom";
import SongListPage from "../SongListPage";
import { useAppContext } from "../contexts/AppContext";

const SongListRoute: React.FC = () => {
  const navigate = useNavigate();
  // 共有データから検索ワード、検索ワードの変更関数、音域データを取得します
  const { searchQuery, setSearchQuery, userRange } = useAppContext();

  return (
    <SongListPage
      searchQuery={searchQuery}
      userRange={userRange}
      onLoginClick={() => navigate("/login")}
      // 検索バーの内容が変更されたら、共有データの検索ワードを更新します
      onSearchChange={setSearchQuery}
    />
  );
};

export default SongListRoute;