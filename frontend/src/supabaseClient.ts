/**
 * 【supabaseClient.ts】
 * 役割：Googleログインなどの機能を提供してくれる「Supabase」に接続するための窓口を作ります。
 */

import { createClient, SupabaseClient } from "@supabase/supabase-js";

// .envファイルから設定値を読み込みます
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY;

let supabase: SupabaseClient | null = null;

// 設定値がある場合のみ、接続クライアントを作成します
if (supabaseUrl && supabaseAnonKey) {
  supabase = createClient(supabaseUrl, supabaseAnonKey);
} else {
  // 設定がない場合は警告を出します
  console.warn(
    "Supabase未設定: REACT_APP_SUPABASE_URL と REACT_APP_SUPABASE_ANON_KEY を frontend/.env に設定してください。認証機能は無効です。"
  );
}

export { supabase };