import React from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import FavoritesPage from "../pages/FavoritesPage";

export const FavoritesRoute: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  return (
    <FavoritesPage
      isAuthenticated={isAuthenticated}
      onLoginClick={() => navigate("/login")}
    />
  );
};
