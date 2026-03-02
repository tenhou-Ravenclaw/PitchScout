/**
 * 【VocalRangeAnalysisCard.tsx】
 * 役割：Vocal Range Analysis の表示ブロックを共通化するカードコンポーネントです。
 * 特徴：総合音域・地声範囲・裏声最高音・声タイプを一貫したUIで表示します。
 */
import React from "react";
import { AnalysisResult, IntegratedVocalRange } from "../../../api";

/** VocalRangeAnalysisCard が受け取るプロパティ */
interface VocalRangeAnalysisCardProps {
  /** 表示対象の分析データ */
  data: AnalysisResult | IntegratedVocalRange;
  /** カード右上に表示する任意コンテンツ */
  topRightContent?: React.ReactNode;
}

const VocalRangeAnalysisCard: React.FC<VocalRangeAnalysisCardProps> = ({
  data,
  topRightContent,
}) => {
  const voiceType = data.voice_type ?? {};

  return (
    <div className="bg-slate-900/60 backdrop-blur-md rounded-3xl shadow-xl border border-white/10 p-6 sm:p-8">
      <div className="flex items-start justify-between gap-4 mb-6">
        <h2 className="text-sm font-bold text-slate-500 uppercase tracking-widest">Vocal Range Analysis</h2>
        {topRightContent}
      </div>

      <div className="flex items-baseline gap-4 mb-8">
        <span className="text-4xl sm:text-6xl font-black text-white tracking-tighter">
          {data.overall_min} <span className="text-slate-600 mx-1">~</span> {data.overall_max}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
        <div className="bg-indigo-900/30 p-4 rounded-2xl border border-indigo-500/30">
          <p className="text-xs font-bold text-indigo-400 mb-1">地声範囲 (Chest)</p>
          <p className="text-xl font-bold text-slate-100">
            {data.chest_min ?? data.overall_min} ~ {data.chest_max ?? data.overall_max}
          </p>
        </div>
        {data.falsetto_max && (
          <div className="bg-emerald-900/30 p-4 rounded-2xl border border-emerald-500/30">
            <p className="text-xs font-bold text-emerald-400 mb-1">裏声最高音 (Falsetto)</p>
            <p className="text-xl font-bold text-slate-100">{data.falsetto_max}</p>
          </div>
        )}
      </div>

      {voiceType && voiceType.voice_type && (
        <div className="p-5 bg-slate-800/50 rounded-2xl border border-slate-700/50">
          <p className="text-sm font-bold text-slate-200 mb-1">
            タイプ: <span className="text-cyan-400">{voiceType.voice_type}</span>
          </p>
          <p className="text-xs text-slate-400 leading-relaxed">{voiceType.description}</p>
        </div>
      )}
    </div>
  );
};

export default VocalRangeAnalysisCard;
