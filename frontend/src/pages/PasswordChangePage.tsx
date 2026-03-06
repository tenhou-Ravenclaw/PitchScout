import React, { useState } from "react";
import { Link } from "react-router-dom";
import { toUserMessage, updatePassword } from "../api";
import CenteredCardShell from "../components/ui/cards/CenteredCardShell";
import ErrorBanner from "../components/ui/ErrorBanner";
import AuthRequiredCard from "../components/ui/cards/AuthRequiredCard";

/** パスワード変更画面のプロパティ */
interface PasswordChangePageProps {
  /** ログイン状態 */
  isAuthenticated: boolean;
  /** ログイン処理 */
  onLoginClick: () => void;
}

/**
 * パスワード変更画面コンポーネント。
 */
const PasswordChangePage: React.FC<PasswordChangePageProps> = ({
  isAuthenticated,
  onLoginClick,
}) => {
  const [newPassword, setNewPassword] = useState<string>("");
  const [confirmPassword, setConfirmPassword] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [successMessage, setSuccessMessage] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string>("");

  /**
   * パスワード更新処理を実行します。
   * @param event フォーム送信イベント
   */
  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setErrorMessage("");
    setSuccessMessage("");

    const trimmedPassword = newPassword.trim();
    if (trimmedPassword.length < 8) {
      setErrorMessage("パスワードは8文字以上で入力してください。");
      return;
    }
    if (trimmedPassword !== confirmPassword.trim()) {
      setErrorMessage("確認用パスワードが一致しません。");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await updatePassword(trimmedPassword);
      setSuccessMessage(response.message);
      setNewPassword("");
      setConfirmPassword("");
    } catch (error: unknown) {
      setErrorMessage(toUserMessage(error, "パスワード更新に失敗しました。"));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <AuthRequiredCard
        title="パスワード変更"
        message="ログイン後にパスワードを変更できます"
        onLoginClick={onLoginClick}
        icon={(
          <svg className="w-12 h-12 text-cyan-500/50" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 7a3 3 0 10-6 0v3m-2 0h10a2 2 0 012 2v5a2 2 0 01-2 2H7a2 2 0 01-2-2v-5a2 2 0 012-2z" />
          </svg>
        )}
      />
    );
  }

  return (
    <CenteredCardShell cardClassName="max-w-md text-left">
      <h1 className="text-xl font-bold text-white mb-2">パスワード変更</h1>
      <p className="text-sm text-slate-400 mb-6">新しいパスワードを設定します（8文字以上）。</p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="new-password" className="block text-sm text-slate-300 mb-1">
            新しいパスワード
          </label>
          <input
            id="new-password"
            type="password"
            required
            minLength={8}
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            className="w-full rounded-xl bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-500"
          />
        </div>

        <div>
          <label htmlFor="confirm-password" className="block text-sm text-slate-300 mb-1">
            新しいパスワード（確認）
          </label>
          <input
            id="confirm-password"
            type="password"
            required
            minLength={8}
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            className="w-full rounded-xl bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-500"
          />
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="btn-primary-cyan w-full rounded-xl px-6 py-3 text-sm disabled:opacity-60"
        >
          {isSubmitting ? "更新中..." : "パスワードを更新"}
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
        <Link to="/reset-password" className="text-cyan-400 hover:text-cyan-300 transition-colors">
          パスワードリセット
        </Link>
      </div>
    </CenteredCardShell>
  );
};

export default React.memo(PasswordChangePage);
