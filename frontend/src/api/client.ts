import axios from "axios";
import { supabase } from "../supabaseClient";

/** Axios インスタンス（API 通信の共通設定） */
export const API = axios.create({
  baseURL:
    process.env.REACT_APP_API_URL || (process.env.NODE_ENV === "production" ? "/api" : "http://127.0.0.1:8000"),
});

/** 認証トークンを自動付与するインターセプター */
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

export default API;
