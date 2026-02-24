/**
 * 【AuthRequiredCard.tsx】
 * 役割：未ログイン時に表示する共通カード（タイトル、説明、ログイン導線）を提供します。
 */

import React, { ReactNode } from "react";
import CenteredCardShell from "./CenteredCardShell";

/** 未ログイン時カードのプロパティ */
interface AuthRequiredCardProps {
  /** 表示タイトル */
  title: string;
  /** 説明文 */
  message: string;
  /** アイコン表示（SVG / Heroicon など） */
  icon: ReactNode;
  /** ログインボタン押下時の処理 */
  onLoginClick: () => void;
  /** ボタンテキスト（省略時は "ログインする"） */
  buttonLabel?: string;
}

const AuthRequiredCard: React.FC<AuthRequiredCardProps> = ({
  title,
  message,
  icon,
  onLoginClick,
  buttonLabel = "ログインする",
}) => {
  return (
    <CenteredCardShell>
      <div className="mb-4 flex justify-center">{icon}</div>
      <h2 className="text-xl font-bold text-white mb-2">{title}</h2>
      <p className="text-slate-400 text-sm mb-6">{message}</p>
      <button
        onClick={onLoginClick}
        className="btn-primary-cyan w-full rounded-xl px-6 py-3 text-sm"
      >
        {buttonLabel}
      </button>
    </CenteredCardShell>
  );
};

export default React.memo(AuthRequiredCard);
