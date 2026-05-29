import React, { useState } from "react";
import { Link } from "react-router-dom";
import { requestPasswordReset, toUserMessage } from "../api";
import CenteredCardShell from "../components/ui/cards/CenteredCardShell";
import ErrorBanner from "../components/ui/ErrorBanner";

/**
 * パスワードリセット画面コンポーネント。
 */
const PasswordResetPage: React.FC = () => {
  const [email, setEmail] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [successMessage, setSuccessMessage] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string>("");

  /**
   * パスワードリセットメール送信を実行します。
   * @param event フォーム送信イベント
   */
  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setErrorMessage("");
    setSuccessMessage("");
    setIsSubmitting(true);

    try {
      const response = await requestPasswordReset(email.trim());
      setSuccessMessage(response.message);
    } catch (error: unknown) {
      setErrorMessage(toUserMessage(error, "パスワードリセットメール送信に失敗しました。"));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <CenteredCardShell cardClassName="max-w-md text-left">
      <h1 className="text-xl font-bold text-white mb-2">パスワードリセット</h1>
      <p className="text-sm text-slate-400 mb-6">
        登録済みメールアドレスにリセット用リンクを送信します。
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="reset-email" className="block text-sm text-slate-300 mb-1">
            メールアドレス
          </label>
          <input
            id="reset-email"
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="w-full rounded-xl bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-500"
            placeholder="example@mail.com"
          />
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="btn-primary-cyan w-full rounded-xl px-6 py-3 text-sm disabled:opacity-60"
        >
          {isSubmitting ? "送信中..." : "リセットメールを送信"}
        </button>
      </form>

      {errorMessage && <ErrorBanner message={errorMessage} className="mt-4" />}
      {successMessage && (
        <p className="mt-4 rounded-lg border border-emerald-500/30 bg-emerald-950/20 px-3 py-2 text-sm text-emerald-300">
          {successMessage}
        </p>
      )}

      <div className="mt-6 flex items-center justify-between text-xs">
        <Link to="/login" className="text-cyan-400 hover:text-cyan-300 transition-colors">
          ログインへ戻る
        </Link>
        <Link to="/change-password" className="text-cyan-400 hover:text-cyan-300 transition-colors">
          パスワード変更
        </Link>
      </div>
    </CenteredCardShell>
  );
};

export default React.memo(PasswordResetPage);
