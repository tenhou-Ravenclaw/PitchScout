/**
 * 【AnalysisCardShell.tsx】
 * 役割：録音/アップロード画面の共通カードレイアウトを提供します。
 */

import React, { ReactNode } from "react";

/** 共通カードのプロパティ */
interface AnalysisCardShellProps {
  /** タイトル（未指定の場合は非表示） */
  title?: string;
  /** タイトル用の追加クラス */
  titleClassName?: string;
  /** コンテンツ */
  children: ReactNode;
}

const AnalysisCardShell: React.FC<AnalysisCardShellProps> = ({
  title,
  titleClassName = "",
  children,
}) => {
  return (
    <div className="max-w-3xl mx-auto bg-slate-900/80 backdrop-blur-xl p-8 sm:p-12 rounded-3xl shadow-[0_0_30px_rgba(0,0,0,0.8)] border border-slate-700/50 relative overflow-hidden">
      {/* 背景の光の装飾（グラデーション） */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-fuchsia-500/10 rounded-full blur-3xl pointer-events-none"></div>

      {title && (
        <h2 className={titleClassName}>{title}</h2>
      )}

      {children}
    </div>
  );
};

export default React.memo(AnalysisCardShell);
