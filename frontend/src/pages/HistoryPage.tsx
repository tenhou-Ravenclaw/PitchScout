// frontend/src/HistoryPage.tsx
/**
 * 【HistoryPage.tsx】
 * 役割：過去の音声解析結果を一覧で表示し、管理（閲覧・削除）するためのページです。
 * 特徴：スマホでの「スワイプ削除」と、PCでの「削除ボタン」の両方に対応した高度なUIを備えています。
 */
import React, { useEffect, useState, useRef } from "react";
// API通信用の関数と型定義をインポート
import { listApi, AnalysisHistoryRecord, toUserMessage } from "../api";
import { useToast } from "../hooks/useToast";
import ErrorBanner from "../components/ui/ErrorBanner";
import LoadingState from "../components/ui/LoadingState";
import PageStateContainer from "../components/ui/PageStateContainer";
import Toast from "../components/ui/Toast";
import AuthRequiredCard from "../components/ui/cards/AuthRequiredCard";
import { PencilIcon, TrashIcon, CheckIcon, XMarkIcon } from "@heroicons/react/24/outline";

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
  const [editingId, setEditingId] = useState<string | null>(null);     // 編集中のアイテムID
  const [editValue, setEditValue] = useState<string>("");              // 編集中のファイル名（拡張子を除いた部分）
  const [editExt, setEditExt] = useState<string>("");                  // 編集中のファイルの拡張子（変更不可）
  const [swipeOffset, setSwipeOffset] = useState<number>(0);           // スワイプの移動距離（正：左スワイプ＝削除、負：右スワイプ＝編集）
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
        const data = await listApi.analysisHistory.get();
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

  /**
   * ファイル名を basename と拡張子に分割します。
   * "recording.mp3" → { baseName: "recording", ext: ".mp3" }
   * "名称未設定"    → { baseName: "名称未設定", ext: "" }
   */
  const splitFileName = (fileName: string): { baseName: string; ext: string } => {
    const dotIndex = fileName.lastIndexOf(".");
    return dotIndex > 0
      ? { baseName: fileName.slice(0, dotIndex), ext: fileName.slice(dotIndex) }
      : { baseName: fileName, ext: "" };
  };

  /** ── 編集開始 ── */
  const handleEdit = (e: React.MouseEvent, record: AnalysisHistoryRecord) => {
    e.stopPropagation();
    const { baseName, ext } = splitFileName(record.file_name || "");
    setEditingId(record.id);
    setEditValue(baseName);
    setEditExt(ext);
    setSwipedId(null);
    setSwipeOffset(0);
  };

  /** ── 編集保存 ── */
  const saveEdit = async (e: React.FormEvent | React.MouseEvent, recordId: string) => {
    e.stopPropagation();
    try {
      // 入力した basename に保持していた拡張子を結合して保存する
      const updated = await listApi.analysisHistory.update(recordId, { file_name: editValue + editExt });
      setHistory(prev => prev.map(r => r.id === recordId ? { ...r, file_name: updated.file_name } : r));
      setEditingId(null);
      showToast("ファイル名を更新しました。");
    } catch (err) {
      showToast(toUserMessage(err, "更新に失敗しました。"));
    }
  };

  /** ── 編集キャンセル ── */
  const cancelEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(null);
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
      await listApi.analysisHistory.remove(recordId);
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
    if (editingId) return; // 編集中の場合はスワイプ不可
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
    const diff = state.startX - touch.clientX; // 正：左（削除）、負：右（編集）

    setSwipeOffset(diff);
    setSwipedId(recordId);
  };

  /** ── スワイプハンドラー: 終了 ── */
  const handleTouchEnd = async (recordId: string) => {
    const state = swipeStates.current[recordId];
    if (!state) return;

    const diff = state.startX - state.currentX;

    if (diff > 150) {
      // 左に深くスワイプ：削除確定
      await performDelete(recordId);
    } else if (diff > 60) {
      // 左に少しスワイプ：削除ボタン表示
      setSwipedId(recordId);
      setSwipeOffset(100);
    } else if (diff < -150) {
      // 右に深くスワイプ：編集モード
      const record = history.find(r => r.id === recordId);
      if (record) {
        const { baseName, ext } = splitFileName(record.file_name || "");
        setEditingId(recordId);
        setEditValue(baseName);
        setEditExt(ext);
      }
      setSwipedId(null);
      setSwipeOffset(0);
    } else if (diff < -60) {
      // 右に少しスワイプ：編集ボタン表示
      setSwipedId(recordId);
      setSwipeOffset(-100);
    } else {
      setSwipedId(null);
      setSwipeOffset(0);
    }
    delete swipeStates.current[recordId];
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
        <p className="sm:hidden mt-2 text-[10px] font-bold text-cyan-400/80 tracking-widest drop-shadow-sm">
          ←スワイプで削除 / 編集スワイプ→
        </p>
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
              {/* === 背景：アクションレイヤー === */}
              <div className="absolute inset-0 flex justify-between items-center px-6 rounded-xl overflow-hidden">
                {/* 右スワイプで見える編集エリア（背景左側） */}
                <div className="absolute left-0 top-0 bottom-0 w-1/2 bg-blue-900 flex items-center justify-start pl-6 border border-blue-500 shadow-[inset_0_0_30px_rgba(59,130,246,0.6)]">
                  <button onClick={(e) => handleEdit(e, record)} className="flex items-center gap-2 text-blue-100 font-bold text-sm drop-shadow-[0_0_5px_rgba(255,255,255,0.5)]">
                    <PencilIcon className="w-5 h-5" />
                    編集
                  </button>
                </div>
                {/* 左スワイプで見える削除エリア（背景右側） */}
                <div className="absolute right-0 top-0 bottom-0 w-1/2 bg-red-950 flex items-center justify-end pr-6 border border-red-500 shadow-[inset_0_0_30px_rgba(239,68,68,0.6)]">
                  <button onClick={(e) => handleDelete(e, record.id)} className="flex items-center gap-2 text-red-100 font-bold text-sm drop-shadow-[0_0_5px_rgba(255,255,255,0.5)]">
                    <TrashIcon className="w-5 h-5" />
                    削除
                  </button>
                </div>
              </div>

              {/* === 前面：実際の履歴カード === */}
              <div
                style={{
                  transform: swipedId === record.id ? `translateX(-${swipeOffset}px)` : "translateX(0)",
                  transition: swipeStates.current[record.id] ? "none" : "transform 0.2s ease-out",
                }}
                className={`bg-slate-950/80 backdrop-blur-xl p-6 rounded-xl border ${editingId === record.id ? 'border-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.4)]' : 'border-cyan-500/80 shadow-[inset_0_0_15px_rgba(34,211,238,0.2),0_0_15px_rgba(34,211,238,0.4)]'} flex flex-col sm:flex-row justify-between sm:items-center gap-4 relative group cursor-pointer hover:-translate-y-1 hover:scale-[1.02] transition-all duration-300 overflow-hidden`}
                onClick={() => {
                  if (editingId === record.id) return;
                  if (swipedId === record.id) cancelSwipe();
                  else onSelectRecord(record);
                }}
              >
                {/* 装飾用のデジタルスキャンライン */}
                <div className="absolute inset-0 pointer-events-none bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(255,255,255,0.03)_2px,rgba(255,255,255,0.03)_4px)]"></div>

                {/* 左側：日時と解析タイプ（および編集入力） */}
                <div className="relative z-10 flex-1 min-w-0">
                  <p className="text-[10px] text-cyan-400/80 font-bold mb-1 tracking-widest">
                    {new Date(record.created_at).toLocaleString("ja-JP")}
                  </p>
                  
                  {editingId === record.id ? (
                    <div className="flex items-center gap-2 mt-1" onClick={e => e.stopPropagation()}>
                      {/* 拡張子より前の部分のみ編集可能 */}
                      <div className="flex items-center border border-blue-500 rounded overflow-hidden bg-slate-900 focus-within:ring-1 focus-within:ring-blue-400">
                        <input
                          autoFocus
                          type="text"
                          value={editValue}
                          onChange={e => setEditValue(e.target.value)}
                          onKeyDown={e => e.key === "Enter" && saveEdit(e, record.id)}
                          className="bg-transparent text-white text-sm px-2 py-1 focus:outline-none w-full max-w-[150px]"
                        />
                        {/* 拡張子は変更不可として固定表示 */}
                        {editExt && (
                          <span className="text-slate-400 text-sm px-2 py-1 border-l border-slate-600 bg-slate-800 select-none">
                            {editExt}
                          </span>
                        )}
                      </div>
                      <button onClick={e => saveEdit(e, record.id)} className="p-1 text-green-400 hover:text-green-300">
                        <CheckIcon className="w-5 h-5" />
                      </button>
                      <button onClick={cancelEdit} className="p-1 text-red-400 hover:text-red-300">
                        <XMarkIcon className="w-5 h-5" />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${record.source_type === "karaoke" ? "bg-purple-900 text-purple-300" : "bg-cyan-900 text-cyan-300"}`}>
                        {record.source_type === "karaoke" ? "カラオケ" : record.source_type === "microphone" ? "マイク" : "ファイル"}
                      </span>
                      <span className="text-slate-200 font-medium truncate max-w-[200px]">
                        {record.file_name || "名称未設定"}
                      </span>
                    </div>
                  )}
                </div>

                {/* 右側：音域スコアとアクションボタン（PC用） */}
                <div className="relative z-10 flex items-center gap-3 sm:gap-4 ml-auto">
                  <div className="bg-transparent border border-cyan-400/40 px-3 py-1.5 rounded-lg text-center min-w-[90px]">
                    <p className="text-[9px] text-cyan-400 font-bold opacity-60">地声</p>
                    <p className="text-xs font-mono font-bold text-cyan-300">
                      {record.vocal_range_min || "-"}~{record.vocal_range_max || "-"}
                    </p>
                  </div>
                  <div className="bg-transparent border border-pink-400/40 px-3 py-1.5 rounded-lg text-center min-w-[70px]">
                    <p className="text-[9px] text-pink-400 font-bold opacity-60">裏声最高</p>
                    <p className="text-xs font-mono font-bold text-pink-300">
                      {record.falsetto_max || "-"}
                    </p>
                  </div>

                  {/* PCでのみ表示されるアクションボタン */}
                  <div className="hidden sm:flex items-center gap-2 ml-2">
                    <button 
                      onClick={(e) => handleEdit(e, record)} 
                      className="p-2 bg-slate-800 border border-blue-500 text-blue-400 hover:bg-blue-600 hover:text-white rounded-lg transition-all duration-300"
                      title="名前を編集"
                    >
                      <PencilIcon className="w-4 h-4" />
                    </button>
                    <button 
                      onClick={(e) => handleDelete(e, record.id)} 
                      className="p-2 bg-slate-800 border border-red-500 text-red-500 hover:bg-red-600 hover:text-white rounded-lg transition-all duration-300"
                      title="削除"
                    >
                      <TrashIcon className="w-4 h-4" />
                    </button>
                  </div>
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