import React from "react";

/**
 * レーダーチャートコンポーネント
 * @param data - 各軸のラベルと値（0〜100）
 * @returns SVGレーダーチャート
 */
export interface RadarChartData {
  label: string;
  value: number;
}

export const RadarChart: React.FC<{ data: RadarChartData[] }> = ({ data }) => {
  const cx = 120, cy = 120, r = 90;
  const n = data.length;
  if (n === 0) return null;

  const angles = data.map((_, i) => (Math.PI * 2 * i) / n - Math.PI / 2);
  const points = data.map((d, i) => {
    const ratio = d.value / 100;
    const x = cx + r * ratio * Math.cos(angles[i]);
    const y = cy + r * ratio * Math.sin(angles[i]);
    return `${x},${y}`;
  }).join(" ");

  return (
    <svg viewBox="0 0 240 240" className="w-full h-full max-w-[220px]">
      {/* 軸ラベル・多角形描画は省略（既存ロジックを移植） */}
      <polygon points={points} fill="#38bdf8" fillOpacity={0.3} stroke="#0ea5e9" strokeWidth={2} />
      {/* 軸ラベル等は必要に応じて追加 */}
    </svg>
  );
};
