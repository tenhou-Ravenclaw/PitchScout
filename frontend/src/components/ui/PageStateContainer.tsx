/**
 * 【PageStateContainer.tsx】
 * 役割：ページ状態（読み込み・エラー・空状態）表示用の共通ラッパーです。
 * 特徴：中央寄せレイアウトと余白を統一し、ページごとの重複を削減します。
 */

import React from "react";

/**
 * PageStateContainer が受け取るプロパティ
 */
interface PageStateContainerProps {
  /** 内部に表示する要素 */
  children: React.ReactNode;
  /** 追加クラス */
  className?: string;
}

/**
 * 状態表示用の共通コンテナを描画します。
 */
const PageStateContainer: React.FC<PageStateContainerProps> = ({
  children,
  className = "",
}) => {
  return (
    <div className={`flex flex-col items-center justify-center min-h-[calc(100vh-80px)] bg-transparent p-8 ${className}`.trim()}>
      {children}
    </div>
  );
};

export default PageStateContainer;
