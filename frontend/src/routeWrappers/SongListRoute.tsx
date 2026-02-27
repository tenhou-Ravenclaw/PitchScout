import React from "react";
import { useNavigate } from "react-router-dom";
import { useAppContext } from "../contexts/AppContext";
import SongListPage from "../pages/SongListPage";

export const SongListRoute: React.FC = () => {
  const navigate = useNavigate();
  const { searchQuery, setSearchQuery, userRange } = useAppContext();
  return (
    <SongListPage
      searchQuery={searchQuery}
      userRange={userRange}
      onLoginClick={() => navigate("/login")}
      onSearchChange={setSearchQuery}
    />
  );
};
