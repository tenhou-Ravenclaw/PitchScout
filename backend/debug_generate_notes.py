"""
debug_generate_notes.py — 音階ごとのデバッグ用 WAV ファイル生成

NOTE_TABLE の各音階（lowlowC 〜 hihihiE）について、
対応する周波数の正弦波 WAV を生成する。
解析パイプラインへの入力テストや音域判定の検証に使用する。

使い方:
    python debug_generate_notes.py                    # 全音階を生成
    python debug_generate_notes.py mid1A mid2C hiA    # 指定した音階のみ生成
    python debug_generate_notes.py --duration 3.0     # 3秒間の音声を生成
    python debug_generate_notes.py --outdir my_notes  # 出力先を変更
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import soundfile as sf

from note_converter import NOTE_TABLE


def generate_note_wav(
    freq_hz: float,
    duration_sec: float = 2.0,
    sr: int = 16000,
    amplitude: float = 0.8,
) -> np.ndarray:
    """
    指定周波数の正弦波を生成する。

    自然な歌声に近づけるため、フェードイン/アウトとビブラートを付与する。

    Args:
        freq_hz: 基本周波数 (Hz)。
        duration_sec: 音声の長さ（秒）。
        sr: サンプリングレート。
        amplitude: 最大振幅 (0.0-1.0)。

    Returns:
        モノラル波形の numpy 配列。
    """
    t = np.arange(int(sr * duration_sec)) / sr

    # ビブラート（歌声らしさのため）: ±0.5% の周波数揺れ、5Hz 周期
    vibrato = freq_hz * 0.005 * np.sin(2.0 * np.pi * 5.0 * t)
    y = np.sin(2.0 * np.pi * (freq_hz + vibrato) * t)

    # 倍音を軽く追加（純音すぎるとピッチ検出が不安定になるため）
    y += 0.3 * np.sin(2.0 * np.pi * 2 * freq_hz * t)  # 2倍音
    y += 0.1 * np.sin(2.0 * np.pi * 3 * freq_hz * t)  # 3倍音

    # フェードイン/アウト（クリックノイズ防止）
    fade_len = int(sr * 0.05)
    fade_in = np.linspace(0.0, 1.0, fade_len)
    fade_out = np.linspace(1.0, 0.0, fade_len)
    y[:fade_len] *= fade_in
    y[-fade_len:] *= fade_out

    # 正規化
    peak = np.max(np.abs(y))
    if peak > 0:
        y = y / peak * amplitude

    return y.astype(np.float32)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="音階ごとのデバッグ用 WAV ファイルを生成する",
    )
    parser.add_argument(
        "notes",
        nargs="*",
        help="生成する音階ラベル（例: mid1A mid2C hiA）。省略時は全音階。",
    )
    parser.add_argument(
        "--duration", type=float, default=2.0,
        help="各ファイルの長さ（秒）。デフォルト: 2.0",
    )
    parser.add_argument(
        "--sr", type=int, default=16000,
        help="サンプリングレート。デフォルト: 16000",
    )
    parser.add_argument(
        "--outdir", type=str, default="debug_notes",
        help="出力ディレクトリ。デフォルト: debug_notes",
    )
    args = parser.parse_args()

    # 対象音階を決定
    label_map = {label: (sci, hz) for sci, label, hz in NOTE_TABLE}

    if args.notes:
        targets: list[tuple[str, str, float]] = []
        for name in args.notes:
            if name not in label_map:
                print(f"[WARN] 不明な音階: {name} （スキップ）")
                continue
            sci, hz = label_map[name]
            targets.append((sci, name, hz))
        if not targets:
            print("[ERROR] 有効な音階が指定されていません")
            sys.exit(1)
    else:
        targets = list(NOTE_TABLE)

    os.makedirs(args.outdir, exist_ok=True)

    print(f"出力先: {args.outdir}/")
    print(f"設定: {args.duration}秒, {args.sr}Hz, {len(targets)}音階")
    print("-" * 50)

    for sci_name, label, freq_hz in targets:
        y = generate_note_wav(freq_hz, duration_sec=args.duration, sr=args.sr)
        filename = f"{label}_{freq_hz:.1f}Hz.wav"
        filepath = os.path.join(args.outdir, filename)
        sf.write(filepath, y, args.sr)
        print(f"  {label:12s} ({sci_name:4s}) = {freq_hz:8.1f} Hz → {filename}")

    print("-" * 50)
    print(f"完了: {len(targets)} ファイルを {args.outdir}/ に生成しました")


if __name__ == "__main__":
    main()
