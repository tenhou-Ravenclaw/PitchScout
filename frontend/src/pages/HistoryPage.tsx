// frontend/src/HistoryPage.tsx
/**
 * 【HistoryPage.tsx】
 * 役割：過去の音声解析結果を一覧で表示し、管理（閲覧・削除）するためのページです。
 * 特徴：スマホでの「スワイプ削除」と、PCでの「削除ボタン」の両方に対応した高度なUIを備えています。
 */
import React, { useEffect, useState, useRef } from "react";
// API通信用の関数と型定義をインポート
import { collectionApi, AnalysisHistoryRecord, toUserMessage } from "../api";
import { useToast } from "../hooks/useToast";
import ErrorBanner from "../components/ui/ErrorBanner";
import LoadingState from "../components/ui/LoadingState";
import PageStateContainer from "../components/ui/PageStateContainer";
import Toast from "../components/ui/Toast";
import AuthRequiredCard from "../components/ui/cards/AuthRequiredCard";

/** 画面のプロパティ（設定） */
interface HistoryPageProps {
  /** ログイン中かどうか */
  isAuthenticated: boolean;
  onLoginClick: () => void; // ログインボタンが押された時の処理
  onSelectRecord: (record: AnalysisHistoryRecord) => void; // 履歴がクリックされた時の処理
}

/** スワイプ操作の状態を記録するための型 */
interface SwipeState {
  startX: number;
  currentX: number;
  startTime: number;
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
  const [swipedId, setSwipedId] = useState<string | null>(null);       // 現在スワイプ中のアイテムID
  const [deletingId, setDeletingId] = useState<string | null>(null);   // 現在削除アニメーション中のID
  const [swipeOffset, setSwipeOffset] = useState<number>(0);           // スワイプの移動距離
  const { toastMessage, showToast, hideToast } = useToast();
  const swipeStates = useRef<Record<string, SwipeState>>({});         // 各アイテムのスワイプ状態を保持

  /**
   * ── 効果 (Effect): 履歴データの取得 ──
   * ログインしている場合、サーバーから解析履歴を取得します。
   */
  useEffect(() => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }

    const fetchHistory = async () => {
      try {
        const data = await collectionApi.analysisHistory.get();
        setHistory(data);
      } catch (err: unknown) {
        setError("履歴の取得に失敗しました。");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [isAuthenticated]);

  /** ── 削除処理（ボタンクリック時：確認あり） ── */
  const handleDelete = async (e: React.MouseEvent, recordId: string) => {
    e.stopPropagation(); // 親要素のクリックイベント（詳細画面への遷移）を阻止
    if (!window.confirm("この履歴を削除しますか？")) return;

    await performDelete(recordId);
  };

  /** ── 削除の実行ロジック ── */
  const performDelete = async (recordId: string) => {
    // 削除アニメーション（横に消えていく）を開始
    setDeletingId(recordId);
    setSwipedId(null);
    setSwipeOffset(0);

    // アニメーションが終わるまで少し待機
    await new Promise((resolve) => setTimeout(resolve, 300));

    try {
      // サーバー側のデータを削除
      await collectionApi.analysisHistory.remove(recordId);
      // 画面上のリストからも消す
      setHistory((prev) => prev.filter((record) => record.id !== recordId));
    } catch (err) {
      console.error(err);
      showToast(toUserMessage(err, "削除に失敗しました。"));
    } finally {
      setDeletingId(null);
    }
  };

  /** ── スワイプハンドラー: 開始 ── */
  const handleTouchStart = (e: React.TouchEvent, recordId: string) => {
    const touch = e.touches[0];
    swipeStates.current[recordId] = {
      startX: touch.clientX,
      currentX: touch.clientX,
      startTime: Date.now(),
    };
  };

  /** ── スワイプハンドラー: 移動中 ── */
  const handleTouchMove = (e: React.TouchEvent, recordId: string) => {
    const touch = e.touches[0];
    const state = swipeStates.current[recordId];
    if (!state) return;

    state.currentX = touch.clientX;
    const diff = state.startX - touch.clientX; // 左方向への移動量

    // リアルタイムでアイテムの表示位置を更新
    if (diff > 0) {
      const offset = Math.min(diff, 250); // 最大250pxまでスワイプ可能
      setSwipeOffset(offset);
      setSwipedId(recordId);
    } else {
      setSwipeOffset(0);
      setSwipedId(null);
    }
  };

  /** ── スワイプハンドラー: 終了 ── */
  const handleTouchEnd = async (recordId: string) => {
    const state = swipeStates.current[recordId];
    if (!state) return;

    const diff = state.startX - state.currentX;

    // スワイプの深さに応じて処理を分岐
    if (diff > 150) {
      // 150px以上：削除確定（確認なしで実行）
      delete swipeStates.current[recordId];
      await performDelete(recordId);
    } else if (diff > 60) {
      // 60-150px：削除ボタンが見える状態で止める
      setSwipedId(recordId);
      setSwipeOffset(120);
      delete swipeStates.current[recordId];
    } else {
      // 60px未満：元の位置に戻す
      setSwipedId(null);
      setSwipeOffset(0);
      delete swipeStates.current[recordId];
    }
  };

  // スワイプ状態を解除する
  const cancelSwipe = () => {
    setSwipedId(null);
    setSwipeOffset(0);
  };

  /** ── 未ログイン時の表示 ── */
  if (!isAuthenticated) {
    return (
      <AuthRequiredCard
        title="分析履歴"
        message="ログインすると過去の分析履歴を確認できます"
        icon={(
          <svg className="w-12 h-12 text-cyan-500/50" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )}
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

      {loading ? (
        <PageStateContainer className="min-h-0 p-0">
          <LoadingState className="text-slate-400" />
        </PageStateContainer>
      ) : error ? (
        <PageStateContainer className="min-h-0 p-0">
          <ErrorBanner message={error} />
        </PageStateContainer>
      ) : history.length === 0 ? (
        <PageStateContainer className="min-h-0 p-0">
          <div className="text-center text-slate-400 bg-slate-800/50 p-8 rounded-2xl">履歴がありません。</div>
        </PageStateContainer>
      ) : (
        <div className="space-y-3">
          {history.map((record) => (
            <div
              key={record.id}
              className={`relative overflow-hidden rounded-xl transition-all duration-300 ${deletingId === record.id ? "opacity-0 -translate-x-full max-h-0 my-0" : "opacity-100 translate-x-0 max-h-96"}`}
              onTouchStart={(e) => handleTouchStart(e, record.id)}
              onTouchMove={(e) => handleTouchMove(e, record.id)}
              onTouchEnd={() => handleTouchEnd(record.id)}
            >
              {/* === 背景：削除確定時に見える赤いエリア === */}
              <div className="absolute inset-0 bg-red-950 flex items-center justify-end pr-6 rounded-xl border border-red-500 shadow-[inset_0_0_30px_rgba(239,68,68,0.6)]">
                <button onClick={(e) => handleDelete(e, record.id)} className="flex items-center gap-2 text-red-100 font-bold text-sm drop-shadow-[0_0_5px_rgba(255,255,255,0.5)]">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  削除
                </button>
              </div>

              {/* === 前面：実際の履歴カード（スワイプで動く部分） === */}
              <div
                style={{
                  transform: swipedId === record.id ? `translateX(-${swipeOffset}px)` : "translateX(0)",
                  transition: swipeStates.current[record.id] ? "none" : "transform 0.2s ease-out",
                }}
                className="bg-slate-950/80 backdrop-blur-xl p-6 rounded-xl border border-cyan-500/80 shadow-[inset_0_0_15px_rgba(34,211,238,0.2),0_0_15px_rgba(34,211,238,0.4)] flex flex-col sm:flex-row justify-between sm:items-center gap-4 relative group cursor-pointer hover:-translate-y-1 hover:scale-[1.02] transition-all duration-300 overflow-hidden"
                onClick={() => {
                  if (swipedId === record.id) cancelSwipe();
                  else onSelectRecord(record); // レコードが選択されたら詳細を表示
                }}
              >
                {/* 装飾用のデジタルスキャンライン */}
                <div className="absolute inset-0 pointer-events-none bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(255,255,255,0.03)_2px,rgba(255,255,255,0.03)_4px)]"></div>

                {/* 左側：日時と解析タイプ */}
                <div className="relative z-10">
                  <p className="text-sm text-cyan-400/80 font-bold mb-1 tracking-widest">
                    {new Date(record.created_at).toLocaleString("ja-JP")}
                  </p>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-1 rounded font-bold ${record.source_type === "karaoke" ? "bg-purple-900 text-purple-300" : "bg-cyan-900 text-cyan-300"}`}>
                      {record.source_type === "karaoke" ? "カラオケ" : record.source_type === "microphone" ? "マイク" : "ファイル"}
                    </span>
                    {record.file_name && <span className="text-slate-300 truncate max-w-[200px]">{record.file_name}</span>}
                  </div>
                </div>

                {/* 右側：音域スコアと削除ボタン（PC用） */}
                <div className="relative z-10 flex items-center gap-4">
                  <div className="bg-transparent border border-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.3)] px-4 py-2 rounded-lg text-center min-w-[100px]">
                    <p className="text-xs text-cyan-400 font-bold mb-1 opacity-80">地声</p>
                    <p className="font-mono font-bold text-cyan-300 drop-shadow-[0_0_5px_rgba(34,211,238,0.8)]">
                      {record.vocal_range_min || "-"} ~ {record.vocal_range_max || "-"}
                    </p>
                  </div>
                  <div className="bg-transparent border border-pink-400 shadow-[0_0_8px_rgba(244,114,182,0.3)] px-4 py-2 rounded-lg text-center min-w-[80px]">
                    <p className="text-xs text-pink-400 font-bold mb-1 opacity-80">裏声最高</p>
                    <p className="font-mono font-bold text-pink-300 drop-shadow-[0_0_5px_rgba(244,114,182,0.8)]">
                      {record.falsetto_max || "-"}
                    </p>
                  </div>

                  {/* PCでのみ表示される削除ボタン */}
                  <button onClick={(e) => handleDelete(e, record.id)} className="hidden sm:block ml-2 px-6 py-2 bg-transparent border border-red-500 text-red-500 hover:bg-red-600 hover:text-white rounded-lg transition-all duration-300 text-sm font-bold tracking-widest">
                    削除
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default React.memo(HistoryPage);