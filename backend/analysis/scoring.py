"""
scoring.py — 歌唱力スコアリング

WORLD 解析データから音域・安定性・表現力の3軸で歌唱力を数値化する。
recommender.py（推薦層）ではなく分析層に属するため analysis/ に配置。
"""

import math
import numpy as np
from config import STABILITY_MIN_SEGMENT, STABILITY_SCALING


def _semitones(hz1: float, hz2: float) -> float:
    """
    2 周波数間の半音数を返す（hz2 > hz1 で正）。

    Args:
        hz1: 基準周波数 (Hz)。
        hz2: 比較周波数 (Hz)。

    Returns:
        半音数。どちらかが 0 以下なら 0.0。
    """
    if hz1 <= 0 or hz2 <= 0:
        return 0.0
    return 12.0 * math.log2(hz2 / hz1)


def analyze_singing_ability(
    f0_array: np.ndarray,
    conf_array: np.ndarray,
    chest_notes: list[float],
    falsetto_notes: list[float],
    overall_min_hz: float,
    overall_max_hz: float,
) -> dict:
    """
    WORLD 解析データから歌唱力指標を算出する。

    Args:
        f0_array:       WORLD (pyworld) が出力した基本周波数の配列。
        conf_array:     信頼度の配列（WORLD では全有声フレーム = 1.0）。
        chest_notes:    地声フレームの周波数リスト (Hz)。
        falsetto_notes: 裏声フレームの周波数リスト (Hz)。
        overall_min_hz: 全体音域の最低音 (Hz)。
        overall_max_hz: 全体音域の最高音 (Hz)。

    Returns:
        {
            "range_semitones": 音域の広さ(半音),
            "range_score":     音域スコア(0-100),
            "stability_score": 安定性スコア(0-100),
            "expression_score":表現力スコア(0-100),
            "overall_score":   総合スコア(0-100),
        }
    """
    result = {}

    # --- 音域の広さ ---
    # 一般: 1-1.5oct(12-18st), 上手い: 2oct(24st), プロ級: 2.5+oct(30+st)
    range_st = _semitones(overall_min_hz, overall_max_hz)
    range_score = min(100.0, (range_st / 30.0) * 100.0)
    result["range_semitones"] = round(range_st, 1)
    result["range_score"] = round(range_score, 1)

    # --- ピッチ安定性 ---
    stability_score = _compute_stability(f0_array, conf_array)
    result["stability_score"] = round(stability_score, 1)

    # --- 表現力（声区の使い分け＋音域の活用度） ---
    expression_score = _compute_expression(
        chest_notes, falsetto_notes, overall_min_hz, overall_max_hz
    )
    result["expression_score"] = round(expression_score, 1)

    # --- 総合スコア ---
    overall = range_score * 0.30 + stability_score * 0.45 + expression_score * 0.25
    result["overall_score"] = round(overall, 1)

    return result


def _compute_stability(f0: np.ndarray, conf: np.ndarray) -> float:
    """
    ピッチ安定性スコア (0-100) を算出する。

    持続音セグメント内のピッチ偏差を計測する。
    隣接フレーム間のピッチ差が1半音以内なら同一音符とみなし、
    STABILITY_MIN_SEGMENT フレーム以上続くセグメントごとにセント標準偏差を算出、
    セグメント長で重み付き平均 → スコア化。

    Args:
        f0: 基本周波数の配列。
        conf: 信頼度の配列（WORLD では全有声フレーム = 1.0）。

    Returns:
        0-100 の安定性スコア。有効フレーム不足時は 50.0。
    """
    mask = (conf >= 0.3) & (f0 > 0)
    f0_valid = f0[mask]
    if len(f0_valid) < 10:
        return 50.0

    semitone_ratio = 2 ** (1 / 12)  # ≈1.0595
    segments = []
    current_seg = [f0_valid[0]]

    for i in range(1, len(f0_valid)):
        ratio = f0_valid[i] / f0_valid[i - 1]
        if 1 / semitone_ratio <= ratio <= semitone_ratio:
            current_seg.append(f0_valid[i])
        else:
            if len(current_seg) >= STABILITY_MIN_SEGMENT:
                segments.append(current_seg)
            current_seg = [f0_valid[i]]
    if len(current_seg) >= STABILITY_MIN_SEGMENT:
        segments.append(current_seg)

    if not segments:
        return 50.0

    weighted_sum = 0.0
    total_frames = 0
    for seg in segments:
        arr = np.array(seg)
        med = np.median(arr)
        cents = 1200.0 * np.log2(arr / med)
        weighted_sum += float(np.std(cents)) * len(seg)
        total_frames += len(seg)

    avg_std = weighted_sum / total_frames
    # 目安: 10cents=プロ(92), 25cents=上手い素人(80), 40cents=普通のカラオケ(68), 75+=40以下
    # STABILITY_SCALING は config.py で管理。0 を下限クランプして常に 100 になる誤設定を防ぐ。
    scaling = max(STABILITY_SCALING, 0.01)
    return max(0.0, min(100.0, 100.0 - avg_std * scaling))


def _compute_expression(
    chest_notes: list[float],
    falsetto_notes: list[float],
    overall_min_hz: float,
    overall_max_hz: float,
) -> float:
    """
    表現力スコア (0-100) を算出する。

    声区の使い分け（地声/裏声の多様性）と音域の活用度（IQR の広さ）を評価する。

    Args:
        chest_notes: 地声フレームの周波数リスト (Hz)。
        falsetto_notes: 裏声フレームの周波数リスト (Hz)。
        overall_min_hz: 全体音域の最低音 (Hz)。
        overall_max_hz: 全体音域の最高音 (Hz)。

    Returns:
        0-100 の表現力スコア。フレームがない場合は 0.0。
    """
    total = len(chest_notes) + len(falsetto_notes)
    if total == 0:
        return 0.0

    score = 30.0  # ベース

    if len(falsetto_notes) > 0 and len(chest_notes) > 0:
        minor = min(len(falsetto_notes), len(chest_notes))
        diversity = minor / total
        score += diversity * 80.0

    all_notes = chest_notes + falsetto_notes
    if len(all_notes) >= 5:
        arr = np.array(all_notes)
        iqr_st = _semitones(float(np.percentile(arr, 25)), float(np.percentile(arr, 75)))
        score += min(30.0, iqr_st * 3.0)

    return min(100.0, score)
