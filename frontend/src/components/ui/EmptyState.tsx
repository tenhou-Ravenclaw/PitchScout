import React from "react";

/** 空状態表示コンポーネントのプロパティ */
interface EmptyStateProps {
  /** タイトル */
  title: string;
  /** 補足メッセージ */
  message: string;
  /** 任意のアイコン */
  icon?: React.ReactNode;
  /** ラッパーに適用するクラス名 */
  className?: string;
  /** タイトルに適用するクラス名 */
  titleClassName?: string;
  /** メッセージに適用するクラス名 */
  messageClassName?: string;
}

/**
 * データ0件時の共通表示コンポーネントです。
 */
const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  message,
  icon,
  className,
  titleClassName,
  messageClassName,
}) => {
  return (
    <div className={className ?? "text-center"}>
      {icon}
      <h2 className={titleClassName ?? "text-xl font-bold text-white mb-2"}>{title}</h2>
      <p className={messageClassName ?? "text-slate-400 text-sm"}>{message}</p>
    </div>
  );
};

export default React.memo(EmptyState);
