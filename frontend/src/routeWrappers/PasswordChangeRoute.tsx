import React from "react";
import { useAuth } from "../contexts/AuthContext";
import PasswordChangePage from "../pages/PasswordChangePage";

/**
 * パスワード変更画面のルートラッパー。
 */
export const PasswordChangeRoute: React.FC = () => {
  const { isAuthenticated, loginWithGoogle } = useAuth();

  return (
    <PasswordChangePage
      isAuthenticated={isAuthenticated}
      onLoginClick={loginWithGoogle}
    />
  );
};
