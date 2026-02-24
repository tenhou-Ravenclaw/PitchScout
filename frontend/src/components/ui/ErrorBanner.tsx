/**
 * 【ErrorBanner.tsx】
 * 役割：ユーザー向けのエラーメッセージを画面内に一貫した見た目で表示する共通コンポーネント。
 */
import React from "react";

/** ErrorBanner の入力プロパティ */
interface ErrorBannerProps {
  message: string;
  className?: string;
}

const ErrorBanner: React.FC<ErrorBannerProps> = ({ message, className = "" }) => {
  return (
    <div className={`w-full bg-red-950/80 backdrop-blur-md border border-red-500/50 rounded-xl p-4 shadow-[0_0_15px_rgba(239,68,68,0.3)] ${className}`}>
      <p className="text-sm font-bold text-red-400 tracking-wide text-center">
        <span className="animate-pulse mr-2">⚠️</span>
        {message}
      </p>
    </div>
  );
};

export default ErrorBanner;
