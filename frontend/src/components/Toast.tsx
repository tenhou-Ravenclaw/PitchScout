/**
 * 【Toast.tsx】
 * 役割：画面上部に短時間表示する非モーダル通知コンポーネント。
 */
import React from "react";

/** トーストの表示種別 */
type ToastVariant = "error" | "info";

/** Toast の入力プロパティ */
interface ToastProps {
  message: string;
  onClose: () => void;
  variant?: ToastVariant;
}

const Toast: React.FC<ToastProps> = ({ message, onClose, variant = "error" }) => {
  const colorClass =
    variant === "error"
      ? "bg-red-950/90 border-red-500/50 text-red-300"
      : "bg-slate-900/90 border-cyan-500/40 text-cyan-200";

  return (
    <div className="fixed top-20 left-1/2 -translate-x-1/2 z-[100] w-[92%] max-w-lg">
      <div className={`backdrop-blur-md border rounded-xl px-4 py-3 shadow-xl ${colorClass}`}>
        <div className="flex items-start gap-3">
          <p className="text-sm font-semibold flex-1 leading-relaxed">{message}</p>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-300 hover:text-white transition-colors"
            aria-label="通知を閉じる"
          >
            ✕
          </button>
        </div>
      </div>
    </div>
  );
};

export default Toast;
