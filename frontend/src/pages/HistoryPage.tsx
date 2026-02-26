// frontend/src/HistoryPage.tsx
/**
 * 【HistoryPage.tsx】
 * 役割：過去の音声解析結果を一覧で表示し、管理（閲覧・削除）するためのページです。
 * 特徴：スマホでの「スワイプ削除」と、PCでの「削除ボタン」の両方に対応した高度なUIを備えています。
 */
import React, { useState } from "react";
// API通信用の関数と型定義をインポート
import {
  getAnalysisHistory,
  AnalysisHistoryRecord,
  toUserMessage,
} from "../api";
import { useErrorToastNotifier } from "../hooks/useErrorToastNotifier";
import { useAuthenticatedDataLoader } from "../hooks/useAuthenticatedDataLoader";
import { useHistoryDelete } from "../hooks/useHistoryDelete";
import { useHistorySwipe } from "../hooks/useHistorySwipe";
import { HISTORY_AUTH_REQUIRED_CONTENT } from "../constants/authRequiredCardContent";
import { HISTORY_FETCH_ERROR_MESSAGE } from "../constants/historyConstants";
import EmptyState from "../components/ui/EmptyState";
import DataStateSwitch from "../components/ui/DataStateSwitch";
import HistoryRecordCard from "../components/features/HistoryRecordCard";
import Toast from "../components/ui/Toast";
import AuthRequiredCard from "../components/ui/cards/AuthRequiredCard";

/** 画面のプロパティ（設定） */
interface HistoryPageProps {
  /** ログイン中かどうか */
  isAuthenticated: boolean;
  onLoginClick: () => void; // ログインボタンが押された時の処理
  onSelectRecord: (record: AnalysisHistoryRecord) => void; // 履歴がクリックされた時の処理
}

const HistoryPage: React.FC<HistoryPageProps> = ({
  isAuthenticated,
  onLoginClick,
  onSelectRecord,
}) => {
  // ── 状態管理 (State) ──
  const [history, setHistory] = useState<AnalysisHistoryRecord[]>([]); // 履歴データ
  const [loading, setLoading] = useState(true);                        // 読み込み中フラグ
  const [error, setError] = useState<string | null>(null);             // エラーメッセージ
  const { toastMessage, hideToast, notifyError } = useErrorToastNotifier();

  const {
    deletingId,
    performDelete,
    handleDelete,
  } = useHistoryDelete({
    setHistory,
    notifyError,
  });

  useAuthenticatedDataLoader<AnalysisHistoryRecord[]>({
    isAuthenticated,
    fetchData: getAnalysisHistory,
    onSuccess: setHistory,
    onError: (err: unknown) => {
      setError(toUserMessage(err, HISTORY_FETCH_ERROR_MESSAGE));
    },
    setLoading,
  });

  const {
    swipedId,
    swipeOffset,
    handleTouchStart,
    handleTouchMove,
    handleTouchEnd,
    cancelSwipe,
    isSwiping,
  } = useHistorySwipe({
    onDelete: performDelete,
  });

  /** ── 未ログイン時の表示 ── */
  if (!isAuthenticated) {
    return (
      <AuthRequiredCard
        title={HISTORY_AUTH_REQUIRED_CONTENT.title}
        message={HISTORY_AUTH_REQUIRED_CONTENT.message}
        icon={HISTORY_AUTH_REQUIRED_CONTENT.icon}
        onLoginClick={onLoginClick}
      />
    );
  }

  /** ── メインの履歴リスト表示 ── */
  return (
    <div className="min-h-screen p-8 max-w-4xl mx-auto">
      {toastMessage && <Toast message={toastMessage} onClose={hideToast} />}

      {/* タイトルエリア */}
      <div className="flex flex-col mb-8 pb-4 border-b border-cyan-500/30">
        <h2 className="text-3xl sm:text-4xl font-black italic title-gradient-cyber drop-shadow-[0_0_15px_rgba(255,255,255,0.3)] tracking-wider">
          HISTORY
        </h2>
        <p className="sm:hidden mt-2 text-xs font-bold text-cyan-400/80 tracking-widest drop-shadow-sm">スワイプで削除</p>
      </div>

      <DataStateSwitch
        loading={loading}
        error={error}
        isEmpty={history.length === 0}
        stateContainerClassName="min-h-0 p-0"
        loadingClassName="text-slate-400"
        emptyContent={(
          <EmptyState
            title="履歴がありません。"
            message=""
            className="text-center text-slate-400 bg-slate-800/50 p-8 rounded-2xl"
            titleClassName="text-slate-400"
            messageClassName="hidden"
          />
        )}
      >
        <div className="space-y-3">
          {history.map((record) => (
            <HistoryRecordCard
              key={record.id}
              record={record}
              deleting={deletingId === record.id}
              swiped={swipedId === record.id}
              swipeOffset={swipeOffset}
              swiping={isSwiping(record.id)}
              onTouchStart={handleTouchStart}
              onTouchMove={handleTouchMove}
              onTouchEnd={handleTouchEnd}
              onDeleteClick={handleDelete}
              onCardClick={(clickedRecord) => {
                if (swipedId === clickedRecord.id) {
                  cancelSwipe();
                  return;
                }
                onSelectRecord(clickedRecord);
              }}
            />
          ))}
        </div>
      </DataStateSwitch>
    </div>
  );
};

export default React.memo(HistoryPage);