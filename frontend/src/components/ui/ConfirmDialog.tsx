/**
 * 【ConfirmDialog.tsx】
 * 役割：「確認しますか？」のような二択確認ダイアログを表示する汎用モーダルコンポーネント。
 * 特徴：背景にブラーオーバーレイを表示し、確認・キャンセルの2択をユーザーに提示します。
 *
 * @param message   - ダイアログ本文（例:「ログアウトしますか？」）
 * @param onConfirm - 確認ボタン押下時のコールバック
 * @param onCancel  - キャンセルボタン押下時・背景クリック時のコールバック
 * @param confirmLabel  - 確認ボタンのラベル（デフォルト:「確認」）
 * @param cancelLabel   - キャンセルボタンのラベル（デフォルト:「キャンセル」）
 * @param isDangerous   - true の場合、確認ボタンをローズ（危険操作）色にする
 */

import React, { useEffect } from "react";

interface ConfirmDialogProps {
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  confirmLabel?: string;
  cancelLabel?: string;
  isDangerous?: boolean;
}

const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  message,
  onConfirm,
  onCancel,
  confirmLabel = "確認",
  cancelLabel = "キャンセル",
  isDangerous = false,
}) => {
  /** Escape キーでキャンセルできるようにする */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onCancel]);

  return (
    /** 背景オーバーレイ：クリックでキャンセル */
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onCancel}
      aria-modal="true"
      role="dialog"
    >
      {/* ダイアログ本体：クリックイベントの伝播を止めて背景クリックと区別する */}
      <div
        className="bg-slate-900/90 border border-white/10 rounded-2xl shadow-2xl p-6 w-[90%] max-w-sm"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="text-slate-200 text-sm font-medium leading-relaxed mb-6 text-center">
          {message}
        </p>

        <div className="flex gap-3">
          {/* キャンセルボタン */}
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 py-2.5 rounded-xl text-sm font-medium text-slate-400 bg-slate-800 hover:bg-slate-700 hover:text-slate-200 transition-colors border border-slate-700"
          >
            {cancelLabel}
          </button>

          {/* 確認ボタン（危険操作はローズ色） */}
          <button
            type="button"
            onClick={onConfirm}
            className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition-colors ${
              isDangerous
                ? "bg-rose-600/80 hover:bg-rose-500 text-white border border-rose-500/50"
                : "bg-cyan-600/80 hover:bg-cyan-500 text-white border border-cyan-500/50"
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmDialog;
