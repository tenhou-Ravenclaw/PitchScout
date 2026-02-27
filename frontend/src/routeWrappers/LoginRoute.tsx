import React from "react";
import { useAuth } from "../contexts/AuthContext";
import LoginPage from "../pages/LoginPage";

export const LoginRoute: React.FC = () => {
  const { loginWithGoogle } = useAuth();
  return <LoginPage onLogin={loginWithGoogle} />;
};
