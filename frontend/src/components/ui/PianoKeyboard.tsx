/**
 * PianoKeyboard.tsx
 * SVGで描画するピアノ鍵盤コンポーネント（画像不使用・著作権フリー）。
 *
 * 色の凡例:
 *   indigo塗り                  → 地声のみ
 *   emerald塗り                 → 裏声のみ
 *   indigo塗り + emeraldの枠線  → 地声と裏声が重なっているキー
 *
 * 音名オクターブ対応（A始まり区切り、A4=442Hz日本カラオケ標準）:
 *   lowA〜lowG#   → MIDI 33〜44
 *   mid1A〜mid1G# → MIDI 45〜56
 *   mid2A〜mid2G# → MIDI 57〜68
 *   hiA〜hiG#     → MIDI 69〜80
 *   hihiA〜hihiG# → MIDI 81〜92
 */
import React from "react";

/**
 * カラオケ表記 → MIDIノート番号 変換テーブル。
 * A始まりのオクターブ区切り（日本カラオケ標準）をMIDI標準（C始まり）にマッピング。
 */
const LABEL_TO_MIDI: Record<string, number> = {
  // octave 1 末端 (lowlow系 G# まで) + lowA〜lowB
  "lowlowC": 24, "lowlowC#": 25, "lowlowD": 26, "lowlowD#": 27,
  "lowlowE": 28, "lowlowF": 29, "lowlowF#": 30, "lowlowG": 31,
  "lowlowG#": 32,
  "lowA": 33, "lowA#": 34, "lowB": 35,
  // octave 2 (lowC〜lowG#) + mid1A〜mid1B
  "lowC": 36, "lowC#": 37, "lowD": 38, "lowD#": 39,
  "lowE": 40, "lowF": 41, "lowF#": 42, "lowG": 43, "lowG#": 44,
  "mid1A": 45, "mid1A#": 46, "mid1B": 47,
  // octave 3 (mid1C〜mid1G#) + mid2A〜mid2B
  "mid1C": 48, "mid1C#": 49, "mid1D": 50, "mid1D#": 51,
  "mid1E": 52, "mid1F": 53, "mid1F#": 54, "mid1G": 55, "mid1G#": 56,
  "mid2A": 57, "mid2A#": 58, "mid2B": 59,
  // octave 4 (mid2C〜mid2G#) + hiA〜hiB
  "mid2C": 60, "mid2C#": 61, "mid2D": 62, "mid2D#": 63,
  "mid2E": 64, "mid2F": 65, "mid2F#": 66, "mid2G": 67, "mid2G#": 68,
  "hiA": 69, "hiA#": 70, "hiB": 71,
  // octave 5 (hiC〜hiG#) + hihiA〜hihiB
  "hiC": 72, "hiC#": 73, "hiD": 74, "hiD#": 75,
  "hiE": 76, "hiF": 77, "hiF#": 78, "hiG": 79, "hiG#": 80,
  "hihiA": 81, "hihiA#": 82, "hihiB": 83,
  // octave 6 (hihiC〜hihiG#) + hihihiA〜hihihiC
  "hihiC": 84, "hihiC#": 85, "hihiD": 86, "hihiD#": 87,
  "hihiE": 88, "hihiF": 89, "hihiF#": 90, "hihiG": 91, "hihiG#": 92,
  "hihihiA": 93, "hihihiA#": 94, "hihihiB": 95, "hihihiC": 96,
};

/** 表示範囲: lowC(MIDI 36)〜hihiC(MIDI 84) = 4オクターブ */
const MIN_MIDI = 36;
const MAX_MIDI = 84;

const WHITE_W = 18;
const WHITE_H = 78;
const BLACK_W = 11;
const BLACK_H = 48;

/** 黒鍵に対応するオクターブ内半音インデックスの集合 */
const BLACK_SET = new Set([1, 3, 6, 8, 10]);

/** @returns MIDIノートが黒鍵かどうか */
function isBlack(midi: number): boolean {
  return BLACK_SET.has(midi % 12);
}

/**
 * MIN_MIDI から midi の手前までの白鍵数を返す（白鍵の左端インデックス）。
 * @param midi - MIDIノート番号
 */
function whitesBefore(midi: number): number {
  let count = 0;
  for (let m = MIN_MIDI; m < midi; m++) {
    if (!isBlack(m)) count++;
  }
  return count;
}

/** オクターブ境界(C音)に表示するラベル */
const OCTAVE_LABELS: Record<number, string> = {
  36: "lowC",
  48: "mid1C",
  60: "mid2C",
  72: "hiC",
  84: "hihiC",
};

/** emerald のリング枠線色 */
const RING_COLOR = "#10b981"; // emerald-500

/** コンポーネントのプロパティ */
export interface PianoKeyboardProps {
  /** 地声最低音（カラオケ表記、例: "mid1C"） */
  chestMin?: string;
  /** 地声最高音（カラオケ表記、例: "hiA"） */
  chestMax?: string;
  /** 裏声最低音（カラオケ表記、例: "mid2G"） */
  falsettoMin?: string;
  /** 裏声最高音（カラオケ表記、例: "hihiD"） */
  falsettoMax?: string;
}

/**
 * SVGで描画するピアノ鍵盤コンポーネント。
 * lowC〜hihiC（4オクターブ）をSVG矩形で描画し、声域範囲をハイライトします。
 * 地声と裏声が重なるキーは indigo 塗り + emerald の枠線で両方を表現します。
 *
 * @param chestMin    - 地声最低音（カラオケ表記）
 * @param chestMax    - 地声最高音（カラオケ表記）
 * @param falsettoMin - 裏声最低音（カラオケ表記）
 * @param falsettoMax - 裏声最高音（カラオケ表記）
 */
const PianoKeyboard: React.FC<PianoKeyboardProps> = ({
  chestMin, chestMax, falsettoMin, falsettoMax,
}) => {
  const chestMinMidi    = chestMin    != null ? (LABEL_TO_MIDI[chestMin]    ?? null) : null;
  const chestMaxMidi    = chestMax    != null ? (LABEL_TO_MIDI[chestMax]    ?? null) : null;
  const falsettoMinMidi = falsettoMin != null ? (LABEL_TO_MIDI[falsettoMin] ?? null) : null;
  const falsettoMaxMidi = falsettoMax != null ? (LABEL_TO_MIDI[falsettoMax] ?? null) : null;

  /** @returns MIDIノートが地声範囲内かどうか */
  function inChest(midi: number): boolean {
    return chestMinMidi !== null && chestMaxMidi !== null
      && midi >= chestMinMidi && midi <= chestMaxMidi;
  }

  /**
   * @returns MIDIノートが裏声範囲内かどうか。
   * falsettoMin が未指定の場合は地声最高音の次の音を裏声最低音とみなす（範囲不明なので非表示）。
   * falsettoMax のみ指定された場合は1音のみ表示されてしまうため、
   * chestMax より上の全音を裏声範囲として扱う。
   */
  function inFalsetto(midi: number): boolean {
    if (falsettoMaxMidi === null) return false;
    if (falsettoMinMidi !== null) {
      return midi >= falsettoMinMidi && midi <= falsettoMaxMidi;
    }
    // falsettoMin 未指定: 地声最高音より上〜裏声最高音を裏声範囲として表示
    const rangeStart = chestMaxMidi !== null ? chestMaxMidi + 1 : falsettoMaxMidi;
    return midi >= rangeStart && midi <= falsettoMaxMidi;
  }

  /**
   * キーの塗りつぶし色を返す。
   * 重なりキーは地声色（indigoー枠線で裏声を表現するため）。
   * @param midi  - MIDIノート番号
   * @param black - 黒鍵かどうか
   */
  function getFill(midi: number, black: boolean): string {
    const c = inChest(midi);
    const f = inFalsetto(midi);
    if (c) return black ? "#4338ca" : "#a5b4fc";    // indigo-700 / indigo-300
    if (f) return black ? "#047857" : "#6ee7b7";    // emerald-700 / emerald-300
    return black ? "#1e293b" : "#f1f5f9";           // slate-800 / slate-100
  }

  // 白鍵リストを生成
  const whiteKeys: number[] = [];
  for (let m = MIN_MIDI; m <= MAX_MIDI; m++) {
    if (!isBlack(m)) whiteKeys.push(m);
  }
  const totalWidth = whiteKeys.length * WHITE_W;

  // 重なりキーの枠線（最後に重ねて描画するため別途収集）
  const rings: React.ReactNode[] = [];

  const whiteKeyRects = whiteKeys.map((midi) => {
    const x = whitesBefore(midi) * WHITE_W;
    if (inChest(midi) && inFalsetto(midi)) {
      rings.push(
        <rect
          key={`ring-${midi}`}
          x={x + 2}
          y={2}
          width={WHITE_W - 4}
          height={WHITE_H - 5}
          fill="none"
          stroke={RING_COLOR}
          strokeWidth={2}
          rx={1.5}
        />
      );
    }
    return (
      <rect
        key={midi}
        x={x + 0.5}
        y={0.5}
        width={WHITE_W - 1}
        height={WHITE_H - 1}
        fill={getFill(midi, false)}
        stroke="#334155"
        strokeWidth={1}
        rx={2}
      />
    );
  });

  const blackKeyRects = Array.from(
    { length: MAX_MIDI - MIN_MIDI + 1 },
    (_, i) => MIN_MIDI + i,
  )
    .filter(isBlack)
    .map((midi) => {
      // 直前の白鍵右端から中央寄せ
      const x = whitesBefore(midi - 1) * WHITE_W + WHITE_W - BLACK_W / 2;
      if (inChest(midi) && inFalsetto(midi)) {
        rings.push(
          <rect
            key={`ring-${midi}`}
            x={x + 1.5}
            y={1.5}
            width={BLACK_W - 3}
            height={BLACK_H - 3}
            fill="none"
            stroke={RING_COLOR}
            strokeWidth={1.5}
            rx={1}
          />
        );
      }
      return (
        <rect
          key={midi}
          x={x}
          y={0}
          width={BLACK_W}
          height={BLACK_H}
          fill={getFill(midi, true)}
          stroke="#0f172a"
          strokeWidth={0.5}
          rx={2}
        />
      );
    });

  return (
    <div className="w-full overflow-x-auto pb-1" role="img" aria-label="声域ピアノ鍵盤図">
      <svg
        width={totalWidth}
        height={WHITE_H + 18}
        style={{ display: "block" }}
      >
        {/* 1. 白鍵 → 2. 黒鍵 → 3. 重なりの枠線（最前面） */}
        {whiteKeyRects}
        {blackKeyRects}
        {rings}

        {/* オクターブラベル（各C音の下） */}
        {Object.entries(OCTAVE_LABELS).map(([midiStr, label]) => {
          const midi = Number(midiStr);
          return (
            <text
              key={midi}
              x={whitesBefore(midi) * WHITE_W + WHITE_W / 2}
              y={WHITE_H + 13}
              textAnchor="middle"
              fontSize={9}
              fill="#475569"
              fontFamily="monospace"
            >
              {label}
            </text>
          );
        })}
      </svg>
    </div>
  );
};

export default PianoKeyboard;
