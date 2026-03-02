import React from "react";
import { useNavigate } from "react-router-dom";
import HomePage from "../pages/HomePage";
import { useAppContext } from "../contexts/AppContext";
import { useAuth } from "../contexts/AuthContext";

export const LandingRoute: React.FC = () => {
  const navigate = useNavigate();
  const { result, searchQuery, setSearchQuery } = useAppContext();
  const { isAuthenticated, user, logout } = useAuth();

  return (
    <HomePage
      result={result}
      isAuthenticated={isAuthenticated}
      onRecordClick={() => navigate("/record")}
      onGuideClick={() => navigate("/guide")}
      onHistoryClick={() => navigate("/history")}
      onFavoritesClick={() => navigate("/favorites")}
      initialSearchQuery={searchQuery}
      onSearchSubmit={(query: string) => {
        const trimmed = query.trim();
        setSearchQuery(trimmed);
        navigate(trimmed ? `/songs?q=${encodeURIComponent(trimmed)}` : "/songs");
      }}
      userName={user?.user_metadata?.full_name || user?.email || null}
      onLogoutClick={logout}
    />
  );
};
