/**
 * VocalGrowthChart — 声域成長の折れ線グラフ
 *
 * 直近の分析履歴から地声・裏声の音域変化を可視化する。
 * 安定して出ている音域（直近 40 件中 4 回以上）はリファレンスラインで表示する。
 *
 * Y 軸は NOTE_TABLE のインデックスを基準とした疑似 MIDI 値（lowlowC = 24）を使用し、
 * 音楽的に意味のある等間隔スケールを実現する。
 */
import React, { useMemo } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from "recharts";
import type { TimelinePoint, StableRange } from "../../api/types";

// ============================================================
// NOTE_TABLE ラベル → 疑似 MIDI 値の変換テーブル
// NOTE_TABLE の先頭 C1 (lowlowC) = MIDI 24 として、1 半音 = 1 ずつ増加する。
// ============================================================

/** 音階ラベル → 疑似 MIDI 値（lowlowC = 24） */
const LABEL_TO_MIDI: Record<string, number> = {
  // Octave 1 (lowlow/low prefix) = MIDI 24–35
  lowlowC: 24, "lowlowC#": 25, lowlowD: 26, "lowlowD#": 27,
  lowlowE: 28, lowlowF: 29, "lowlowF#": 30, lowlowG: 31,
  "lowlowG#": 32, lowA: 33, "lowA#": 34, lowB: 35,
  // Octave 2 (low prefix) = MIDI 36–47
  lowC: 36, "lowC#": 37, lowD: 38, "lowD#": 39,
  lowE: 40, lowF: 41, "lowF#": 42, lowG: 43,
  "lowG#": 44, mid1A: 45, "mid1A#": 46, mid1B: 47,
  // Octave 3 (mid1 prefix) = MIDI 48–59
  mid1C: 48, "mid1C#": 49, mid1D: 50, "mid1D#": 51,
  mid1E: 52, mid1F: 53, "mid1F#": 54, mid1G: 55,
  "mid1G#": 56, mid2A: 57, "mid2A#": 58, mid2B: 59,
  // Octave 4 (mid2 prefix) = MIDI 60–71
  mid2C: 60, "mid2C#": 61, mid2D: 62, "mid2D#": 63,
  mid2E: 64, mid2F: 65, "mid2F#": 66, mid2G: 67,
  "mid2G#": 68, hiA: 69, "hiA#": 70, hiB: 71,
  // Octave 5 (hi prefix) = MIDI 72–83
  hiC: 72, "hiC#": 73, hiD: 74, "hiD#": 75,
  hiE: 76, hiF: 77, "hiF#": 78, hiG: 79,
  "hiG#": 80, hihiA: 81, "hihiA#": 82, hihiB: 83,
  // Octave 6 (hihi prefix) = MIDI 84–95
  hihiC: 84, "hihiC#": 85, hihiD: 86, "hihiD#": 87,
  hihiE: 88, hihiF: 89, "hihiF#": 90, hihiG: 91,
  "hihiG#": 92, hihihiA: 93, "hihihiA#": 94, hihihiB: 95,
  // Octave 7 (hihihi prefix) = MIDI 96–100
  hihihiC: 96, "hihihiC#": 97, hihihiD: 98, "hihihiD#": 99,
  hihihiE: 100,
};

/** 疑似 MIDI 値 → 音階ラベル（Y 軸ツールチップ表示用） */
const MIDI_TO_LABEL: Record<number, string> = Object.fromEntries(
  Object.entries(LABEL_TO_MIDI).map(([label, midi]) => [midi, label])
);

/**
 * 音階ラベルを疑似 MIDI 値に変換する。
 * @param label 音階ラベル（例: "mid2G"）または null
 * @returns MIDI 値、または null（ラベルが null または未知の場合）
 */
function labelToMidi(label: string | null): number | null {
  if (!label) return null;
  return LABEL_TO_MIDI[label] ?? null;
}

/**
 * 疑似 MIDI 値を音階ラベルに変換する（Y 軸の tick 表示用）。
 * @param midi MIDI 値
 * @returns 音階ラベル文字列
 */
function midiToLabel(midi: number): string {
  return MIDI_TO_LABEL[midi] ?? String(midi);
}

// ============================================================
// コンポーネント Props
// ============================================================

/** VocalGrowthChart コンポーネントの Props */
interface VocalGrowthChartProps {
  /** 古い順に並んだ分析タイムラインポイントの配列 */
  timeline: TimelinePoint[];
  /** 安定音域（直近 N 件中 4 回以上出現） */
  stableRange: StableRange;
}

// ============================================================
// VocalGrowthChart
// ============================================================

/**
 * 声域成長グラフコンポーネント。
 *
 * 地声最低音・最高音・裏声最高音の推移を折れ線グラフで表示し、
 * 安定音域をリファレンスラインとして重ねて描画する。
 */
const VocalGrowthChart: React.FC<VocalGrowthChartProps> = ({ timeline, stableRange }) => {
  /** タイムラインポイントを Recharts 用データに変換 */
  const data = useMemo(
    () =>
      timeline.map((pt, i) => ({
        index: i + 1,
        date: new Date(pt.date).toLocaleDateString("ja-JP", {
          month: "numeric",
          day: "numeric",
        }),
        chest_max_midi: labelToMidi(pt.chest_max),
        chest_min_midi: labelToMidi(pt.chest_min),
        falsetto_max_midi: labelToMidi(pt.falsetto_max),
      })),
    [timeline]
  );

  /** Y 軸の tick 位置（オクターブの C 音、すなわち 12 半音ごと） */
  const yTicks = useMemo(() => {
    const allMidi = data.flatMap((d) => [
      d.chest_max_midi,
      d.chest_min_midi,
      d.falsetto_max_midi,
    ]).filter((v): v is number => v !== null && v !== undefined);

    if (allMidi.length === 0) return [];

    const minMidi = Math.min(...allMidi);
    const maxMidi = Math.max(...allMidi);

    // C 音 (MIDI % 12 === 0) を 12 半音ごとに抽出
    const ticks: number[] = [];
    const startOctave = Math.floor(minMidi / 12) * 12;
    for (let midi = startOctave; midi <= maxMidi + 1; midi += 12) {
      if (midi >= 24) ticks.push(midi);
    }
    return ticks;
  }, [data]);

  const stableChestMaxMidi = labelToMidi(stableRange.chest_max);
  const stableFalsettoMidi = labelToMidi(stableRange.falsetto_max);

  return (
    <div>
      {/* グラフヘッダー */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 mb-3">
        <h3 className="text-sm font-bold text-slate-200 tracking-wider">声域の成長グラフ</h3>
        {(stableRange.chest_max || stableRange.falsetto_max) && (
          <div className="flex flex-wrap gap-3 text-[10px] text-slate-400">
            {stableRange.chest_max && (
              <span>
                <span className="inline-block w-3 h-0.5 bg-indigo-400 mr-1 align-middle" />
                安定地声最高音：
                <span className="text-indigo-300 font-bold">{stableRange.chest_max}</span>
              </span>
            )}
            {stableRange.falsetto_max && (
              <span>
                <span className="inline-block w-3 h-0.5 bg-emerald-400 mr-1 align-middle" />
                安定裏声最高音：
                <span className="text-emerald-300 font-bold">{stableRange.falsetto_max}</span>
              </span>
            )}
          </div>
        )}
      </div>

      {/* Recharts 折れ線グラフ */}
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 4, right: 16, left: 4, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />

          <XAxis
            dataKey="date"
            tick={{ fill: "#94a3b8", fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
          />

          <YAxis
            ticks={yTicks}
            tickFormatter={midiToLabel}
            tick={{ fill: "#94a3b8", fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
            width={52}
          />

          <Tooltip
            formatter={(value: number | undefined, name: string | undefined) => [
              value !== undefined ? midiToLabel(value) : "-",
              name ?? "",
            ]}
            contentStyle={{
              background: "#0f172a",
              border: "1px solid #334155",
              borderRadius: "8px",
              fontSize: "11px",
            }}
            labelStyle={{ color: "#94a3b8", fontSize: "10px" }}
          />

          <Legend
            wrapperStyle={{ fontSize: "11px", color: "#94a3b8", paddingTop: "8px" }}
          />

          <Line
            dataKey="chest_max_midi"
            name="地声最高音"
            stroke="#818cf8"
            dot={false}
            strokeWidth={2}
            connectNulls
          />
          <Line
            dataKey="chest_min_midi"
            name="地声最低音"
            stroke="#60a5fa"
            dot={false}
            strokeWidth={2}
            connectNulls
          />
          <Line
            dataKey="falsetto_max_midi"
            name="裏声最高音"
            stroke="#34d399"
            dot={false}
            strokeWidth={2}
            connectNulls
          />

          {/* 安定地声最高音リファレンスライン */}
          {stableChestMaxMidi !== null && (
            <ReferenceLine
              y={stableChestMaxMidi}
              stroke="#818cf8"
              strokeDasharray="6 3"
              strokeOpacity={0.7}
              label={{
                value: `安定 ${stableRange.chest_max}`,
                fill: "#818cf8",
                fontSize: 10,
                position: "insideTopRight",
              }}
            />
          )}

          {/* 安定裏声最高音リファレンスライン */}
          {stableFalsettoMidi !== null && (
            <ReferenceLine
              y={stableFalsettoMidi}
              stroke="#34d399"
              strokeDasharray="6 3"
              strokeOpacity={0.7}
              label={{
                value: `安定 ${stableRange.falsetto_max}`,
                fill: "#34d399",
                fontSize: 10,
                position: "insideTopRight",
              }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default VocalGrowthChart;
