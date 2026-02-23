/**
 * 【HistoryPage.tsx】
 * 役割：過去の歌唱分析結果を一覧で表示し、詳細の確認や削除を行う画面です。
 * 💡 設計図（FRONTEND_STRUCTURE.md）に基づく移動案：
 * 1. 移動先: src/features/songs/pages/HistoryPage.tsx
 * 2. 改善点：スワイプの座標計算ロジックが長いため、「useSwipeToDelete」のような
 * カスタムフックに切り出すと、画面側のコードがスッキリして読みやすくなります。
 */

import React, { useEffect, useState, useRef } from "react";
// API通信用の関数をインポート
import {
  getAnalysisHistory,
  AnalysisHistoryRecord,
  deleteAnalysisHistory,
} from "./api";
import { useAuth } from "./contexts/AuthContext";

/** * 画面が受け取るデータ（Props）の定義
 */
interface HistoryPageProps {
  onLoginClick: () => void; // ログインボタンが押された時の処理
  onSelectRecord: (record: AnalysisHistoryRecord) => void; // 履歴が選ばれた時の処理
}

/** * スワイプの状態を管理するための型定義
 */
interface SwipeState {
  startX: number;   // タッチ開始位置
  currentX: number; // 現在の指の位置
  startTime: number; // タッチ開始時刻
}

const HistoryPage: React.FC<HistoryPageProps> = ({
  onLoginClick,
  onSelectRecord,
}) => {
  const { isAuthenticated } = useAuth();
  
  // ── 状態管理 (State) ──
  const [history, setHistory] = useState<AnalysisHistoryRecord[]>([]); // 履歴リスト本体
  const [loading, setLoading] = useState(true); // 読み込み中フラグ
  const [error, setError] = useState<string | null>(null); // エラーメッセージ
  
  // スワイプ演出用の状態
  const [swipedId, setSwipedId] = useState<string | null>(null); // 現在スワイプされている項目のID
  const [deletingId, setDeletingId] = useState<string | null>(null); // 削除アニメーション中のID
  const [swipeOffset, setSwipeOffset] = useState<number>(0); // どのくらい横にずれているか(px)
  
  // 指の動きをリアルタイムに記録するための参照（再描画を発生させずに値を保持）
  const swipeStates = useRef<Record<string, SwipeState>>({});

  /**
   * 画面表示時に履歴データをサーバーから取得
   */
  useEffect(() => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }

    const fetchHistory = async () => {
      try {
        const data = await getAnalysisHistory();
        setHistory(data);
      } catch (err: any) {
        setError("履歴の取得に失敗しました。");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [isAuthenticated]);

  /**
   * 削除ボタン（PC用等）が押された時の処理
   */
  const handleDelete = async (e: React.MouseEvent, recordId: string) => {
    e.stopPropagation(); // 親要素のクリック（詳細画面へ飛ぶ）を防ぐ
    if (!window.confirm("この履歴を削除しますか？")) return;

    await performDelete(recordId);
  };

  /**
   * 実際の削除処理を実行する共通関数
   */
  const performDelete = async (recordId: string) => {
    // 1. 削除アニメーションを開始
    setDeletingId(recordId);
    setSwipedId(null);
    setSwipeOffset(0);

    // 2. アニメーション（0.3秒）が終わるのを待つ
    await new Promise((resolve) => setTimeout(resolve, 300));

    try {
      await deleteAnalysisHistory(recordId);
      // 3. 成功したらリストから取り除く（画面更新）
      setHistory((prev) => prev.filter((record) => record.id !== recordId));
    } catch (err) {
      alert("削除に失敗しました。");
      console.error(err);
    } finally {
      setDeletingId(null);
    }
  };

  // ── スワイプ操作の制御 (スマホ用) ──

  /** タッチ開始 */
  const handleTouchStart = (e: React.TouchEvent, recordId: string) => {
    const touch = e.touches[0];
    swipeStates.current[recordId] = {
      startX: touch.clientX,
      currentX: touch.clientX,
      startTime: Date.now(),
    };
  };

  /** 指を動かしている最中 */
  const handleTouchMove = (e: React.TouchEvent, recordId: string) => {
    const touch = e.touches[0];
    const state = swipeStates.current[recordId];
    if (!state) return;

    state.currentX = touch.clientX;
    const diff = state.startX - touch.clientX; // 左向きの移動距離

    if (diff > 0) {
      // 左へスワイプ：最大250pxまで動きに追従
      const offset = Math.min(diff, 250);
      setSwipeOffset(offset);
      setSwipedId(recordId);
    } else {
      // 右へ戻る：リセット
      setSwipeOffset(0);
      setSwipedId(null);
    }
  };

  /** 指を離した時：スワイプ距離に応じて「削除」か「戻す」か判定 */
  const handleTouchEnd = async (recordId: string) => {
    const state = swipeStates.current[recordId];
    if (!state) return;

    const diff = state.startX - state.currentX;

    if (diff > 150) {
      // 150px以上：勢いよくスワイプされたとみなして削除実行
      delete swipeStates.current[recordId];
      await performDelete(recordId);
    } else if (diff > 60) {
      // 60-150px：削除ボタンが見える位置で止める
      setSwipedId(recordId);
      setSwipeOffset(120);
      delete swipeStates.current[recordId];
    } else {
      // 60px未満：スワイプ不十分として元の位置に戻す
      setSwipedId(null);
      setSwipeOffset(0);
      delete swipeStates.current[recordId];
    }
  };

  /** キャンセル処理 */
  const cancelSwipe = () => {
    setSwipedId(null);
    setSwipeOffset(0);
  };

  // ── 条件付きレンダリング：未ログイン状態 ──
  if (!isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-80px)] bg-transparent p-8">
        <div className="w-full max-w-sm bg-slate-900/60 backdrop-blur-md rounded-2xl shadow-xl border border-white/10 p-8 text-center">
          <svg className="w-12 h-12 text-cyan-500/50 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h2 className="text-xl font-bold text-white mb-2">分析履歴</h2>
          <p className="text-slate-400 text-sm mb-6">ログインすると過去の分析履歴を確認できます</p>
          <button onClick={onLoginClick} className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-medium rounded-xl px-6 py-3 text-sm transition-colors shadow-lg shadow-cyan-500/20">
            ログインする
          </button>
        </div>
      </div>
    );
  }

  // ── メイン表示：履歴リスト ──
  return (
    <div className="min-h-screen p-8 max-w-4xl mx-auto">
      <div className="flex flex-col mb-8 pb-4 border-b border-cyan-500/30">
        <h2 className="text-3xl sm:text-4xl font-black italic text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-fuchsia-400 to-yellow-400 drop-shadow-[0_0_15px_rgba(255,255,255,0.3)] tracking-wider">
          HISTORY
        </h2>
        <p className="sm:hidden mt-2 text-xs font-bold text-cyan-400/80 tracking-widest drop-shadow-sm">スワイプで削除</p>
      </div>

      {loading ? (
        <div className="text-center text-slate-400">読み込み中...</div>
      ) : error ? (
        <div className="text-red-400 bg-red-900/20 p-4 rounded-lg">{error}</div>
      ) : history.length === 0 ? (
        <div className="text-center text-slate-400 bg-slate-800/50 p-8 rounded-2xl">
          履歴がありません。録音・アップロードして分析してみましょう。
        </div>
      ) : (
        <div className="space-y-3">
          {history.map((record) => (
            <div
              key={record.id}
              className={`relative overflow-hidden rounded-xl transition-all duration-300 ${deletingId === record.id
                ? "opacity-0 -translate-x-full max-h-0 my-0" // 削除時の消えるアニメーション
                : "opacity-100 translate-x-0 max-h-96"
                }`}
              onTouchStart={(e) => handleTouchStart(e, record.id)}
              onTouchMove={(e) => handleTouchMove(e, record.id)}
              onTouchEnd={() => handleTouchEnd(record.id)}
            >
              {/* === 背面レイヤー：削除ボタン (スワイプすると現れる) === */}
              <div className="absolute inset-0 bg-red-950 flex items-center justify-end pr-6 rounded-xl border border-red-500 shadow-[inset_0_0_30px_rgba(239,68,68,0.6)]">
                <button onClick={(e) => handleDelete(e, record.id)} className="flex items-center gap-2 text-red-100 font-bold text-sm">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  削除
                </button>
              </div>

              {/* === 前面レイヤー：履歴アイテムの内容 === */}
              <div
                style={{
                  transform: swipedId === record.id ? `translateX(-${swipeOffset}px)` : "translateX(0)",
                  transition: swipeStates.current[record.id] ? "none" : "transform 0.2s ease-out",
                }}
                className="bg-slate-950/80 backdrop-blur-xl p-6 rounded-xl border border-cyan-500/80 shadow-[inset_0_0_15px_rgba(34,211,238,0.2)] flex flex-col sm:flex-row justify-between sm:items-center gap-4 relative group cursor-pointer hover:border-cyan-400 transition-all duration-300 overflow-hidden"
                onClick={() => {
                  if (swipedId === record.id) cancelSwipe();
                  else onSelectRecord(record);
                }}
              >
                {/* 装飾用スキャンライン演出 */}
                <div className="absolute inset-0 pointer-events-none bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(255,255,255,0.03)_2px,rgba(255,255,255,0.03)_4px)] z-0"></div>

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

                <div className="relative z-10 flex items-center gap-4">
                  <div className="bg-transparent border border-cyan-400 px-4 py-2 rounded-lg text-center min-w-[100px]">
                    <p className="text-xs text-cyan-400 font-bold mb-1 opacity-80">地声</p>
                    <p className="font-mono font-bold text-cyan-300">{record.vocal_range_min || "-"} ~ {record.vocal_range_max || "-"}</p>
                  </div>
                  <div className="bg-transparent border border-pink-400 px-4 py-2 rounded-lg text-center min-w-[80px]">
                    <p className="text-xs text-pink-400 font-bold mb-1 opacity-80">裏声最高</p>
                    <p className="font-mono font-bold text-pink-300">{record.falsetto_max || "-"}</p>
                  </div>

                  {/* 削除ボタン（PC用：タッチデバイス以外で表示） */}
                  <button onClick={(e) => handleDelete(e, record.id)} className="hidden sm:block ml-2 px-6 py-2 border border-red-500 text-red-500 hover:bg-red-600 hover:text-white rounded-lg transition-all text-sm font-bold z-10">
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

// 無駄な再描画を防ぐためにReact.memoを使用
export default React.memo(HistoryPage);