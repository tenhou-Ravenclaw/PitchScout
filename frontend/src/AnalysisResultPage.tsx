/**
 * 【AnalysisResultPage.tsx】
 * 役割：解析結果のデータをきれいに画面に並べる「表示の主役」です。
 */

import React, { useState, useEffect } from "react";
// 💡 パス修正：同じ階層にある api.ts や components フォルダを正しく参照します
import {
  AnalysisResult,
  IntegratedVocalRange,
  getFavoriteArtists,
  addFavoriteArtist,
  removeFavoriteArtist,
  getIntegratedVocalRange,
} from "./api";
import { StarIcon as StarSolid } from "@heroicons/react/24/solid";
import { StarIcon as StarOutline } from "@heroicons/react/24/outline";
import { useAuth } from "./contexts/AuthContext";

/**
 * 💡 ここで「result」という名前でデータを受け取るように定義しています。
 * これにより「Property 'result' does not exist」というエラーが消えます。
 */
interface AnalysisResultPageProps {
  result: AnalysisResult | null;
}

/* ───── ヘルパー部品（キーバッジ・チャート） ───── */
const keyBadge = (key: number, fit?: string) => {
  const label = key === 0 ? "±0" : key > 0 ? `+${key}` : `${key}`;
  let color = fit === "perfect" ? "bg-emerald-900/30 text-emerald-400 border border-emerald-500/30" : "bg-slate-800 text-slate-500 border border-slate-700";
  return <span className={`inline-flex items-center justify-center min-w-[2.5rem] h-6 rounded-full text-xs font-bold ${color}`}>{label}</span>;
};

const RadarChart: React.FC<{ data: { label: string; value: number }[] }> = ({ data }) => {
  const cx = 120, cy = 120, r = 90;
  const points = data.map((d, i) => {
    const ratio = d.value / 100;
    const a = (Math.PI * 2 * i) / data.length - Math.PI / 2;
    return `${cx + r * ratio * Math.cos(a)},${cy + r * ratio * Math.sin(a)}`;
  }).join(" ");
  return (
    <svg viewBox="0 0 240 240" className="w-full h-full max-w-[220px]">
      <polygon points={points} fill="rgba(99, 102, 241, 0.2)" stroke="#6366f1" strokeWidth="2" />
    </svg>
  );
};

/* ───── メイン画面 ───── */
const AnalysisResultPage: React.FC<AnalysisResultPageProps> = ({ result }) => {
  const { isAuthenticated } = useAuth();
  const [favoriteIds, setFavoriteIds] = useState<number[]>([]);
  const [integratedRange, setIntegratedRange] = useState<IntegratedVocalRange | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      getIntegratedVocalRange(20).then(setIntegratedRange).catch(console.error);
    }
  }, [isAuthenticated]);

  // 表示するデータを選択（統合データがあればそちら、なければ今回の結果）
  const displayData = (isAuthenticated && integratedRange) ? integratedRange : result;

  if (!displayData) return <div className="p-20 text-center text-slate-400">分析データがありません。</div>;

  return (
    <div className="p-4 sm:p-8 text-slate-200">
       <h1 className="text-2xl font-bold mb-4">分析結果</h1>
       <div className="bg-slate-900/60 p-6 rounded-3xl border border-white/10">
         <p className="text-4xl font-black">{displayData.overall_min} ~ {displayData.overall_max}</p>
         {/* ...（中略：その他の表示ロジック）... */}
       </div>
    </div>
  );
};

// 💡 外部から AnalysisResultPage という名前で呼び出せるようにします
export default AnalysisResultPage;