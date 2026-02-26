import React from "react";
import { AnalysisHistoryRecord } from "../../api";

/** 履歴カードコンポーネントのプロパティ */
interface HistoryRecordCardProps {
  /** 履歴レコード */
  record: AnalysisHistoryRecord;
  /** 削除アニメーション中かどうか */
  deleting: boolean;
  /** 現在スワイプ表示対象かどうか */
  swiped: boolean;
  /** スワイプ移動量 */
  swipeOffset: number;
  /** 現在ドラッグ中かどうか */
  swiping: boolean;
  /** タッチ開始時ハンドラ */
  onTouchStart: (event: React.TouchEvent, recordId: string) => void;
  /** タッチ移動時ハンドラ */
  onTouchMove: (event: React.TouchEvent, recordId: string) => void;
  /** タッチ終了時ハンドラ */
  onTouchEnd: (recordId: string) => Promise<void>;
  /** 削除ボタン押下時ハンドラ */
  onDeleteClick: (event: React.MouseEvent, recordId: string) => Promise<void>;
  /** カード押下時ハンドラ */
  onCardClick: (record: AnalysisHistoryRecord) => void;
}

/**
 * 履歴一覧の1件分カードを表示するコンポーネントです。
 */
const HistoryRecordCard: React.FC<HistoryRecordCardProps> = ({
  record,
  deleting,
  swiped,
  swipeOffset,
  swiping,
  onTouchStart,
  onTouchMove,
  onTouchEnd,
  onDeleteClick,
  onCardClick,
}) => {
  return (
    <div
      className={`relative overflow-hidden rounded-xl transition-all duration-300 ${deleting ? "opacity-0 -translate-x-full max-h-0 my-0" : "opacity-100 translate-x-0 max-h-96"}`}
      onTouchStart={(event) => onTouchStart(event, record.id)}
      onTouchMove={(event) => onTouchMove(event, record.id)}
      onTouchEnd={() => onTouchEnd(record.id)}
    >
      <div className="absolute inset-0 bg-red-950 flex items-center justify-end pr-6 rounded-xl border border-red-500 shadow-[inset_0_0_30px_rgba(239,68,68,0.6)]">
        <button onClick={(event) => onDeleteClick(event, record.id)} className="flex items-center gap-2 text-red-100 font-bold text-sm drop-shadow-[0_0_5px_rgba(255,255,255,0.5)]">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
          削除
        </button>
      </div>

      <div
        style={{
          transform: swiped ? `translateX(-${swipeOffset}px)` : "translateX(0)",
          transition: swiping ? "none" : "transform 0.2s ease-out",
        }}
        className="bg-slate-950/80 backdrop-blur-xl p-6 rounded-xl border border-cyan-500/80 shadow-[inset_0_0_15px_rgba(34,211,238,0.2),0_0_15px_rgba(34,211,238,0.4)] flex flex-col sm:flex-row justify-between sm:items-center gap-4 relative group cursor-pointer hover:-translate-y-1 hover:scale-[1.02] transition-all duration-300 overflow-hidden"
        onClick={() => onCardClick(record)}
      >
        <div className="absolute inset-0 pointer-events-none bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(255,255,255,0.03)_2px,rgba(255,255,255,0.03)_4px)]"></div>

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

          <button onClick={(event) => onDeleteClick(event, record.id)} className="hidden sm:block ml-2 px-6 py-2 bg-transparent border border-red-500 text-red-500 hover:bg-red-600 hover:text-white rounded-lg transition-all duration-300 text-sm font-bold tracking-widest">
            削除
          </button>
        </div>
      </div>
    </div>
  );
};

export default React.memo(HistoryRecordCard);
