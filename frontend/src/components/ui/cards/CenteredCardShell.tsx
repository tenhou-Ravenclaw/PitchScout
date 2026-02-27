/**
 * 【CenteredCardShell.tsx】
 * 役割：中央配置の共通カードレイアウトを提供します。
 */

import React, { ReactNode } from "react";

/** 中央配置カードのプロパティ */
interface CenteredCardShellProps {
  /** カードの中身 */
  children: ReactNode;
  /** カードに追加するクラス */
  cardClassName?: string;
}

const CenteredCardShell: React.FC<CenteredCardShellProps> = ({
  children,
  cardClassName = "",
}) => {
  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-80px)] bg-transparent p-8">
      <div
        className={`w-full max-w-sm bg-slate-900/60 backdrop-blur-md rounded-2xl shadow-xl border border-white/10 p-8 text-center ${cardClassName}`.trim()}
      >
        {children}
      </div>
    </div>
  );
};

export default React.memo(CenteredCardShell);
