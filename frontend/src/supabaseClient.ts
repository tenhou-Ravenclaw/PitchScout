/**
 * 【supabaseClient.ts】
 * 役割：Supabase（バックエンドサービス）と連携するためのクライアントを初期化します。
 * これにより、アプリからログイン機能やデータベース保存が利用できるようになります。
 * 💡 設計図（FRONTEND_STRUCTURE.md）に基づく移動案：
 * 1. 移動先: src/lib/supabase.ts
 * 2. 理由：外部ライブラリ（SDK）の設定ファイルは lib フォルダにまとめると整理しやすくなります。
 */

import { createClient, SupabaseClient } from "@supabase/supabase-js";

// .env ファイルに設定した環境変数（URLと鍵）を読み込みます
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY;

// Supabaseクライアントを保持するための変数
let supabase: SupabaseClient | null = null;

// 環境変数が正しく設定されているかチェックします
if (supabaseUrl && supabaseAnonKey) {
  // 設定があればクライアントを作成
  supabase = createClient(supabaseUrl, supabaseAnonKey);
} else {
  // 設定がない場合は警告を出し、認証機能を無効にします
  console.warn(
    "Supabase未設定: REACT_APP_SUPABASE_URL と REACT_APP_SUPABASE_ANON_KEY を frontend/.env に設定してください。認証機能は無効です。"
  );
}

// 他のファイルから supabase を使えるようにエクスポート
export { supabase };