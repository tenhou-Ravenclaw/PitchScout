import axios, { InternalAxiosRequestConfig } from "axios";
import { supabase } from "../supabaseClient";

/** リトライフラグを持つ拡張リクエスト設定 */
interface RetryableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

/** Axios インスタンス（API 通信の共通設定） */
export const API = axios.create({
  baseURL:
    process.env.REACT_APP_API_URL || (process.env.NODE_ENV === "production" ? "/api" : "http://127.0.0.1:8000"),
  
});

/** 認証トークンを自動付与するリクエストインターセプター */
API.interceptors.request.use(async (config) => {
  if (supabase) {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

/**
 * 401 レスポンスを処理するインターセプター。
 * - トークンのリフレッシュを1回だけ試みる。
 * - リフレッシュ成功 → 元のリクエストをリトライ。
 * - リフレッシュ失敗 → Supabase セッションをクリアしてエラーを返す。
 */
API.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as RetryableConfig;

    if (
      error.response?.status === 401 &&
      supabase &&
      !originalRequest._retry
    ) {
      originalRequest._retry = true;

      const { data, error: refreshError } = await supabase.auth.refreshSession();
      if (!refreshError && data.session) {
        // リフレッシュ成功: 新しいトークンで元のリクエストをリトライ
        originalRequest.headers = originalRequest.headers || {};
        originalRequest.headers.Authorization = `Bearer ${data.session.access_token}`;
        return API(originalRequest);
      }

      // リフレッシュ失敗: セッションをクリア（ログアウト状態にする）
      await supabase.auth.signOut();
    }

    return Promise.reject(error);
  }
);

export default API;
