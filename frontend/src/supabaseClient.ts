/**
 * 【supabaseClient.ts】
 * 役割：Googleログインなどの機能を提供してくれる「Supabase」に接続するための窓口を作ります。
 */

import { createClient, SupabaseClient } from "@supabase/supabase-js";

// .envファイルから設定値を読み込みます
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY;

let supabase: SupabaseClient | null = null;
let authLockChain: Promise<unknown> = Promise.resolve();
let cachedAccessToken: string | null = null;
let sessionPromise: Promise<string | null> | null = null;

const localAuthLock = async <T,>(
  _name: string,
  _acquireTimeout: number,
  fn: () => Promise<T>
): Promise<T> => {
  const run = authLockChain.catch(() => undefined).then(fn);
  authLockChain = run.then(
    () => undefined,
    () => undefined
  );
  return run;
};

const isAuthLockTimeout = (error: unknown): boolean => {
  if (!error || typeof error !== "object") return false;
  const maybeError = error as { isAcquireTimeout?: boolean; name?: string; message?: string };
  return (
    maybeError.isAcquireTimeout === true ||
    maybeError.name === "NavigatorLockAcquireTimeoutError" ||
    Boolean(maybeError.message?.includes("Navigator LockManager lock"))
  );
};

export const setCachedAccessToken = (token: string | null | undefined): void => {
  cachedAccessToken = token ?? null;
};

export const getSupabaseAccessToken = async (): Promise<string | null> => {
  if (!supabase) return null;
  if (cachedAccessToken) return cachedAccessToken;

  if (!sessionPromise) {
    sessionPromise = supabase.auth
      .getSession()
      .then(({ data: { session } }) => {
        const token = session?.access_token ?? null;
        setCachedAccessToken(token);
        return token;
      })
      .catch((error: unknown) => {
        if (isAuthLockTimeout(error)) {
          console.warn("[WARN] Supabase auth lock の取得がタイムアウトしました。ゲスト状態で続行します。");
        } else {
          console.error("[ERROR] Supabase セッション取得に失敗しました:", error);
        }
        setCachedAccessToken(null);
        return null;
      })
      .finally(() => {
        sessionPromise = null;
      });
  }

  return sessionPromise;
};

// 設定値がある場合のみ、接続クライアントを作成します
if (supabaseUrl && supabaseAnonKey) {
  supabase = createClient(supabaseUrl, supabaseAnonKey, {
    auth: {
      lock: localAuthLock,
    },
  });
} else {
  // 設定がない場合は警告を出します
  console.warn(
    "Supabase未設定: REACT_APP_SUPABASE_URL と REACT_APP_SUPABASE_ANON_KEY を frontend/.env に設定してください。認証機能は無効です。"
  );
}

export { supabase };
