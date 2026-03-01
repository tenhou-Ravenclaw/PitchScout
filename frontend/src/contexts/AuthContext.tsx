/**
 * 【AuthContext.tsx】
 * 役割：Supabase（認証基盤）を使った「ログイン・ログアウト」の状態を管理します。
 */
import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react";
// Supabase公式のUser型と、設定済みのクライアントを読み込みます
import { User } from "@supabase/supabase-js";
import { supabase } from "../supabaseClient";

/** ── 認証データの設計図 ── */
interface AuthContextType {
  user: User | null;         // ログイン中のユーザー情報
  isAuthenticated: boolean;  // ログインしているか
  isLoading: boolean;        // 認証状態を確認中か
  loginWithGoogle: () => Promise<void>; // Googleログイン実行
  logout: () => Promise<void>;          // ログアウト実行
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  loginWithGoogle: async () => { },
  logout: async () => { },
});

export const useAuth = () => useContext(AuthContext);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  /**
   * ── 起動時のログインチェック ──
   */
  useEffect(() => {
    if (!supabase) {
      setIsLoading(false);
      return;
    }

    // 1. 現在のセッション（ログイン情報）を確認
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      setIsLoading(false);
    });

    // 2. 認証状態の変化（ログインした、ログアウトした等）をリアルタイムで監視
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setUser(session?.user ?? null);
        setIsLoading(false);
      }
    );

    return () => subscription.unsubscribe(); // 終了時に監視を止める
  }, []);

  /** ── Googleログインの実行 ──
   * 💡 window.location.origin を使うことで、開発時は http://localhost:3000、
   *    本番時は https://pitchscout.ten-hou.com へ自動的にリダイレクト先が決まります。
   *    環境変数や手動の本番判定は不要です。
   */
  const loginWithGoogle = useCallback(async () => {
    if (!supabase) {
      console.warn("Supabase未設定のためログインできません");
      return;
    }

    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: window.location.origin,
      },
    });
  }, []);

  /** ── ログアウトの実行 ── */
  const logout = useCallback(async () => {
    if (!supabase) return;
    await supabase.auth.signOut();
    setUser(null);
  }, []);

  /** ── パフォーマンス最適化 (useMemo) ── */
  const value = useMemo(
    () => ({ user, isAuthenticated: !!user, isLoading, loginWithGoogle, logout }),
    [user, isLoading, loginWithGoogle, logout]
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};