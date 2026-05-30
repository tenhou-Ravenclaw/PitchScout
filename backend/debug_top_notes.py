#!/usr/bin/env python3
"""
debug_top_notes.py — 最高音から半オクターブ分のフレームを切り出すデバッグツール

音声ファイルを WORLD で解析し、検出された最高音から6半音下までの
フレームだけを抽出して WAV に書き出す。
「明らかに高すぎる音が判定されている」ときの原因調査に使う。

使い方:
    python debug_top_notes.py path/to/vocals.wav
    python debug_top_notes.py vocals.wav --semitones 8   # 8半音分切り出し
    python debug_top_notes.py vocals.wav --outdir debug   # 出力先指定

出力:
    top_notes_<ラベル>_to_<ラベル>.wav  — 該当フレームの音声
    top_notes_detail.csv              — 各フレームの時刻・周波数・音階
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import sys

import numpy as np
import pyworld
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import WORLD_SAMPLE_RATE, WORLD_FRAME_PERIOD_MS
from note_converter import hz_to_label_and_hz


def _extract_top_frames(
    wav_path: str,
    semitones: float = 6.0,
    outdir: str = "debug_top",
) -> None:
    """
    最高音から指定半音数分のフレームを切り出す。

    Args:
        wav_path: 入力 WAV ファイルパス。
        semitones: 最高音から何半音下まで含めるか（デフォルト: 6 = 半オクターブ）。
        outdir: 出力ディレクトリ。
    """
    # --- 1) 読み込み ---
    y, sr_orig = sf.read(wav_path)
    if y.ndim > 1:
        y = np.mean(y, axis=1)
    y = y.astype(np.float64)

    # 16kHz にリサンプル（WORLD 用）
    if sr_orig != WORLD_SAMPLE_RATE:
        import librosa
        y = librosa.resample(y, orig_sr=sr_orig, target_sr=WORLD_SAMPLE_RATE)
    sr = WORLD_SAMPLE_RATE

    # --- 2) WORLD で F0 検出 ---
    print(f"[INFO] WORLD 解析中: {wav_path}")
    f0_harvest, time_axis = pyworld.harvest(
        y, fs=sr,
        frame_period=WORLD_FRAME_PERIOD_MS,
        f0_floor=65.0,
        f0_ceil=1400.0,
    )
    f0 = pyworld.stonemask(y, f0_harvest, time_axis, sr)

    voiced_mask = f0 > 0.0
    voiced_f0 = f0[voiced_mask]
    if len(voiced_f0) < 5:
        print("[ERROR] 有声音フレームが少なすぎます")
        return

    # --- 3) 最高音と閾値を計算 ---
    max_hz = float(np.max(voiced_f0))
    # 半音 = 12 * log2(f2/f1) → f_low = f_high / 2^(semitones/12)
    cutoff_hz = max_hz / (2.0 ** (semitones / 12.0))

    max_label, max_defined = hz_to_label_and_hz(max_hz)
    cut_label, cut_defined = hz_to_label_and_hz(cutoff_hz)

    print(f"[INFO] 最高音:   {max_label} ({max_hz:.1f} Hz)")
    print(f"[INFO] 下限:     {cut_label} ({cutoff_hz:.1f} Hz)")
    print(f"[INFO] 範囲:     {semitones:.0f} 半音")

    # --- 4) 該当フレームを特定 ---
    hop = int(sr * WORLD_FRAME_PERIOD_MS / 1000.0)
    frame_len = hop * 4  # フレームあたりのサンプル数（前後にマージン）

    target_frames: list[dict] = []
    for i in range(len(f0)):
        if f0[i] >= cutoff_hz:
            label, defined_hz = hz_to_label_and_hz(f0[i])
            target_frames.append({
                "index": i,
                "time_sec": float(time_axis[i]),
                "f0_hz": float(f0[i]),
                "label": label,
                "defined_hz": defined_hz,
            })

    if not target_frames:
        print("[WARN] 該当するフレームがありません")
        return

    print(f"[INFO] 該当フレーム: {len(target_frames)} / {int(np.sum(voiced_mask))} (有声音)")

    # --- 5) 音声を切り出し ---
    os.makedirs(outdir, exist_ok=True)

    # 連続フレームをグループ化（100ms 以上離れたら分割）
    groups: list[list[dict]] = []
    current_group: list[dict] = [target_frames[0]]
    for frame in target_frames[1:]:
        if frame["time_sec"] - current_group[-1]["time_sec"] > 0.1:
            groups.append(current_group)
            current_group = [frame]
        else:
            current_group.append(frame)
    groups.append(current_group)

    # 全フレームを1ファイルにまとめる（区切りに 50ms 無音を挿入）
    gap_samples = int(sr * 0.05)
    segments: list[np.ndarray] = []

    for group in groups:
        start_sample = max(0, int(group[0]["time_sec"] * sr) - hop)
        end_sample = min(len(y), int(group[-1]["time_sec"] * sr) + frame_len)
        segment = y[start_sample:end_sample]
        if len(segment) > 0:
            segments.append(segment.astype(np.float32))
            segments.append(np.zeros(gap_samples, dtype=np.float32))

    if not segments:
        print("[WARN] 切り出せる音声がありません")
        return

    combined = np.concatenate(segments)
    out_wav = os.path.join(outdir, f"top_notes_{cut_label}_to_{max_label}.wav")
    sf.write(out_wav, combined, sr)
    duration = len(combined) / sr
    print(f"[INFO] WAV 出力: {out_wav} ({duration:.2f}秒, {len(groups)}セグメント)")

    # --- 6) CSV に詳細を出力 ---
    csv_path = os.path.join(outdir, "top_notes_detail.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["index", "time_sec", "f0_hz", "label", "defined_hz"])
        writer.writeheader()
        writer.writerows(target_frames)
    print(f"[INFO] CSV 出力: {csv_path} ({len(target_frames)}行)")

    # --- 7) 分布サマリー ---
    print(f"\n{'='*50}")
    print("音階別フレーム数:")
    from collections import Counter
    counts = Counter(f["label"] for f in target_frames)
    for label, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        hz_val = next(f["defined_hz"] for f in target_frames if f["label"] == label)
        bar = "█" * min(count, 40)
        print(f"  {label:12s} ({hz_val:7.1f} Hz): {count:4d} {bar}")
    print(f"{'='*50}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="最高音から半オクターブ分のフレームを切り出す",
    )
    parser.add_argument("wav", help="入力 WAV ファイルパス")
    parser.add_argument(
        "--semitones", type=float, default=6.0,
        help="最高音から何半音下まで含めるか（デフォルト: 6 = 半オクターブ）",
    )
    parser.add_argument(
        "--outdir", type=str, default="debug_top",
        help="出力ディレクトリ（デフォルト: debug_top）",
    )
    args = parser.parse_args()

    if not os.path.exists(args.wav):
        print(f"[ERROR] ファイルが見つかりません: {args.wav}")
        sys.exit(1)

    _extract_top_frames(args.wav, semitones=args.semitones, outdir=args.outdir)


if __name__ == "__main__":
    main()
