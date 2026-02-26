import React from "react";
import ErrorBanner from "./ErrorBanner";
import LoadingState from "./LoadingState";

/** 状態表示コンテナのプロパティ */
interface PageStateContainerProps {
  /** 内部に表示する要素 */
  children: React.ReactNode;
  /** 追加クラス */
  className?: string;
}

/** データ状態切り替えコンポーネントのプロパティ */
interface DataStateSwitchProps {
  /** 読み込み中かどうか */
  loading: boolean;
  /** エラーメッセージ */
  error: string | null;
  /** データが空かどうか */
  isEmpty: boolean;
  /** 空状態で表示する要素 */
  emptyContent: React.ReactNode;
  /** 正常時に表示する要素 */
  children: React.ReactNode;
  /** 状態表示ラッパーに適用するクラス名 */
  stateContainerClassName?: string;
  /** ローディング表示に適用するクラス名 */
  loadingClassName?: string;
}

/**
 * 状態表示用の共通コンテナを描画します。
 */
const PageStateContainer: React.FC<PageStateContainerProps> = ({
  children,
  className = "",
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center min-h-[calc(100vh-80px)] bg-transparent p-8 ${className}`.trim()}
    >
      {children}
    </div>
  );
};

/**
 * loading / error / empty / content の表示を切り替える共通コンポーネントです。
 */
const DataStateSwitch: React.FC<DataStateSwitchProps> = ({
  loading,
  error,
  isEmpty,
  emptyContent,
  children,
  stateContainerClassName,
  loadingClassName,
}) => {
  if (loading) {
    return (
      <PageStateContainer className={stateContainerClassName}>
        <LoadingState className={loadingClassName} />
      </PageStateContainer>
    );
  }

  if (error) {
    return (
      <PageStateContainer className={stateContainerClassName}>
        <ErrorBanner message={error} />
      </PageStateContainer>
    );
  }

  if (isEmpty) {
    return (
      <PageStateContainer className={stateContainerClassName}>
        {emptyContent}
      </PageStateContainer>
    );
  }

  return <>{children}</>;
};

export default React.memo(DataStateSwitch);
