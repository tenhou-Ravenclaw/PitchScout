import React from "react";

/**
 * レーダーチャートの各軸データ
 */
export interface RadarChartData {
  /** 軸ラベル */
  label: string;
  /** 0〜100 のスコア */
  value: number;
}

/**
 * SVGレーダーチャートコンポーネント。
 * グリッド・軸線・データポリゴン・軸ラベルを描画します。
 *
 * @param data - 各軸のラベルと値（0〜100）
 */
export const RadarChart: React.FC<{ data: RadarChartData[] }> = ({ data }) => {
  const cx = 120, cy = 120, r = 80;
  const n = data.length;
  if (n === 0) return null;

  // 各軸の角度（上（-90°）を起点に時計回り）
  const angles = data.map((_, i) => (Math.PI * 2 * i) / n - Math.PI / 2);

  /**
   * グリッド多角形の頂点座標を生成します。
   * @param ratio - 半径に対する割合（0.25 / 0.5 / 0.75 / 1.0）
   */
  const gridPoints = (ratio: number) =>
    angles
      .map(a => `${cx + r * ratio * Math.cos(a)},${cy + r * ratio * Math.sin(a)}`)
      .join(" ");

  // データポリゴンの頂点座標
  const dataPoints = data
    .map((d, i) => {
      const ratio = d.value / 100;
      return `${cx + r * ratio * Math.cos(angles[i])},${cy + r * ratio * Math.sin(angles[i])}`;
    })
    .join(" ");

  // ラベルを軸の外側に配置する半径
  const labelR = r + 18;

  return (
    // overflow="visible" でラベルがビューボックス外にはみ出しても表示されるようにする
    <svg viewBox="0 0 240 240" className="w-full h-full max-w-[220px]" overflow="visible">

      {/* ── 軸線（中心から各頂点へ） ── */}
      {angles.map((angle, i) => (
        <line
          key={`axis-${i}`}
          x1={cx} y1={cy}
          x2={cx + r * Math.cos(angle)}
          y2={cy + r * Math.sin(angle)}
          stroke="#334155" strokeWidth={1}
        />
      ))}

      {/* ── グリッド多角形（25% / 50% / 75% / 100%） ── */}
      {[0.25, 0.5, 0.75, 1.0].map((ratio, i) => (
        <polygon
          key={`grid-${i}`}
          points={gridPoints(ratio)}
          fill="none"
          stroke="#334155"
          strokeWidth={ratio === 1.0 ? 1.5 : 1}
        />
      ))}

      {/* ── データポリゴン ── */}
      <polygon
        points={dataPoints}
        fill="#38bdf8"
        fillOpacity={0.3}
        stroke="#0ea5e9"
        strokeWidth={2}
      />

      {/* ── データポイント（各頂点の丸） ── */}
      {data.map((d, i) => {
        const ratio = d.value / 100;
        return (
          <circle
            key={`pt-${i}`}
            cx={cx + r * ratio * Math.cos(angles[i])}
            cy={cy + r * ratio * Math.sin(angles[i])}
            r={3}
            fill="#0ea5e9"
          />
        );
      })}

      {/* ── 軸ラベル ── */}
      {data.map((d, i) => {
        const angle = angles[i];
        const lx = cx + labelR * Math.cos(angle);
        const ly = cy + labelR * Math.sin(angle);
        const cos = Math.cos(angle);
        const sin = Math.sin(angle);
        // 水平方向の位置に応じてテキスト揃えを切り替え
        const anchor = Math.abs(cos) < 0.3 ? "middle" : cos > 0 ? "start" : "end";
        // 垂直方向の位置に応じて縦オフセットを調整
        const dy = Math.abs(sin) < 0.3 ? "0.35em" : sin > 0 ? "1em" : "0em";
        return (
          <text
            key={`lbl-${i}`}
            x={lx} y={ly}
            textAnchor={anchor}
            dy={dy}
            fill="#94a3b8"
            fontSize={10}
            fontWeight="bold"
          >
            {d.label}
          </text>
        );
      })}
    </svg>
  );
};
