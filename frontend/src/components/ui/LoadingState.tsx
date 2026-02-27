/**
 * 【LoadingState.tsx】
 * 役割：ページ内のシンプルなローディング表示を共通化するUIコンポーネントです。
 * 特徴：表示メッセージとスタイルを最小限のPropsで切り替えできます。
 */

import React from "react";

/**
 * LoadingState が受け取るプロパティ
 */
interface LoadingStateProps {
  /** 表示メッセージ */
  message?: string;
  /** 追加クラス */
  className?: string;
}

/**
 * シンプルなローディング表示を描画します。
 */
const LoadingState: React.FC<LoadingStateProps> = ({
  message = "読み込み中...",
  className = "mt-6 text-slate-500",
}) => {
  return <p className={className}>{message}</p>;
};

export default LoadingState;
