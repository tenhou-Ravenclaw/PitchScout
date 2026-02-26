import React from "react";
import ErrorBanner from "./ErrorBanner";
import LoadingState from "./LoadingState";
import PageStateContainer from "./PageStateContainer";

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
