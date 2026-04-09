"""
feature_extractor.py — WORLD ベース特徴抽出

pyworld を利用して F0 / SP / AP を抽出し、
フレーム特徴をセグメント特徴へ集約する。
"""

from __future__ import annotations

from dataclasses import dataclass

import librosa
import numpy as np
import pyworld

from config import FALSETTO_HARD_MIN_HZ

WORLD_SAMPLE_RATE = 16000
WORLD_FRAME_PERIOD_MS = 5.0
EPS = 1e-8


@dataclass(frozen=True)
class WorldFeatures:
    """WORLD 抽出結果を保持するデータ構造。"""

    f0: np.ndarray
    sp: np.ndarray
    ap: np.ndarray
    voiced_mask: np.ndarray
    time_axis_sec: np.ndarray | None = None
    sample_rate: int = WORLD_SAMPLE_RATE


@dataclass(frozen=True)
class FrameAcousticFeatures:
    """ゲート判定に使うフレーム単位の音響特徴。"""

    f0: np.ndarray
    f0_std: np.ndarray
    ap_mean: np.ndarray
    ap_std: np.ndarray
    hnr: np.ndarray
    sp_tilt: np.ndarray
    h1_h2: np.ndarray
    hcount: np.ndarray
    harmonic_score: np.ndarray
    voiced_mask: np.ndarray


def apply_energy_vad(
    y: np.ndarray,
    sr: int,
    top_db: float = 35.0,
    min_segment_duration_sec: float = 0.08,
) -> np.ndarray:
    """
    エネルギーベース VAD で無音区間を除去する。

    Args:
        y: モノラル波形。
        sr: サンプリングレート。
        top_db: 無音判定の閾値。
        min_segment_duration_sec: 保持する最小区間長。

    Returns:
        無音を除去した波形。全除去された場合は原波形を返す。
    """
    if y.size == 0:
        return y

    intervals = librosa.effects.split(y=y, top_db=top_db)
    if len(intervals) == 0:
        return y

    min_samples = int(sr * min_segment_duration_sec)
    kept_segments: list[np.ndarray] = []
    for start, end in intervals:
        segment = y[start:end]
        if segment.size >= min_samples:
            kept_segments.append(segment)

    if not kept_segments:
        return y

    return np.concatenate(kept_segments)


def _ensure_world_rate(y: np.ndarray, sr: int) -> np.ndarray:
    """WORLD 用に 16kHz へリサンプルする。"""
    if sr == WORLD_SAMPLE_RATE:
        return y

    return librosa.resample(y=y, orig_sr=sr, target_sr=WORLD_SAMPLE_RATE)


def extract_world_features(y: np.ndarray, sr: int) -> WorldFeatures:
    """
    pyworld で F0/SP/AP を抽出する。

    Args:
        y: モノラル波形。
        sr: サンプリングレート。

    Returns:
        WorldFeatures。

    Raises:
        ValueError: 有効な有声音が抽出できない場合。
    """
    y_16k = _ensure_world_rate(y.astype(np.float64), sr)
    y_16k = apply_energy_vad(y=y_16k, sr=WORLD_SAMPLE_RATE)

    if y_16k.size < WORLD_SAMPLE_RATE // 4:
        raise ValueError("有効音声が短すぎます")

    f0_harvest, time_axis = pyworld.harvest(
        y_16k,
        fs=WORLD_SAMPLE_RATE,
        frame_period=WORLD_FRAME_PERIOD_MS,
        f0_floor=65.0,
        f0_ceil=1400.0,
    )
    f0 = pyworld.stonemask(y_16k, f0_harvest, time_axis, WORLD_SAMPLE_RATE)

    sp = pyworld.cheaptrick(
        y_16k,
        f0,
        time_axis,
        fs=WORLD_SAMPLE_RATE,
    )
    ap = pyworld.d4c(
        y_16k,
        f0,
        time_axis,
        fs=WORLD_SAMPLE_RATE,
    )

    voiced_mask = f0 > 0.0
    if int(np.sum(voiced_mask)) < 5:
        raise ValueError("有声音フレームが不足しています")

    return WorldFeatures(
        f0=f0,
        sp=sp,
        ap=ap,
        voiced_mask=voiced_mask,
        time_axis_sec=time_axis,
        sample_rate=WORLD_SAMPLE_RATE,
    )


def _safe_stats(values: np.ndarray) -> tuple[float, float]:
    """配列の平均と標準偏差を返す（空配列安全）。"""
    if values.size == 0:
        return 0.0, 0.0
    return float(np.mean(values)), float(np.std(values))


def compute_hnr_from_world(sp_frame: np.ndarray, ap_frame: np.ndarray) -> float:
    """WORLD の SP/AP から HNR(dB) を計算する。"""
    harmonic_energy = float(np.sum(sp_frame * (1.0 - ap_frame)))
    noise_energy = float(np.sum(sp_frame * ap_frame))
    return float(10.0 * np.log10((harmonic_energy + EPS) / (noise_energy + EPS)))


def compute_harmonic_score(
    h1_h2: float,
    hcount: float,
    slope: float,
    w_h1h2: float = 0.3,
    w_hcount: float = 0.4,
    w_slope: float = 0.3,
) -> float:
    """補助ログ用途の倍音スコアを 0-1 で返す。"""
    h1h2_score = float(np.clip(1.0 - (h1_h2 / 12.0), 0.0, 1.0))
    hcount_score = float(np.clip(hcount / 10.0, 0.0, 1.0))
    slope_score = float(np.clip(-slope / 40.0, 0.0, 1.0))
    return float(w_h1h2 * h1h2_score + w_hcount * hcount_score + w_slope * slope_score)


def _rolling_std(values: np.ndarray, window: int = 5) -> np.ndarray:
    """短時間窓の移動標準偏差を計算する。"""
    if values.size == 0:
        return np.zeros(0, dtype=np.float32)

    pad = window // 2
    padded = np.pad(values, (pad, pad), mode="edge")
    out = np.zeros_like(values, dtype=np.float32)
    for idx in range(values.size):
        segment = padded[idx: idx + window]
        out[idx] = float(np.std(segment))
    return out


def _frame_sp_tilt(log_sp: np.ndarray) -> float:
    """log-SP に対する一次回帰傾きを返す。"""
    xs = np.arange(log_sp.size, dtype=np.float64)
    if log_sp.size < 3:
        return -6.0
    return float(np.polyfit(xs, log_sp, 1)[0])


def _frame_harmonic_stats(
    sp_frame: np.ndarray,
    f0: float,
    sample_rate: int,
    n_harmonics: int = 10,
) -> tuple[float, float]:
    """H1-H2 と有効倍音本数を算出する。"""
    if f0 <= 0.0:
        return 0.0, 0.0

    n_bins = sp_frame.size
    n_fft = max((n_bins - 1) * 2, 2)
    freq_res = float(sample_rate) / float(n_fft)
    if freq_res <= 0.0:
        return 0.0, 0.0

    sp_db = 10.0 * np.log10(np.maximum(sp_frame, EPS))
    noise_db = float(np.percentile(sp_db, 20))

    harmonic_levels: list[float] = []
    for order in range(1, n_harmonics + 1):
        target_hz = f0 * order
        bin_idx = int(round(target_hz / freq_res))
        if bin_idx <= 0 or bin_idx >= n_bins:
            harmonic_levels.append(noise_db)
            continue
        lo = max(0, bin_idx - 1)
        hi = min(n_bins, bin_idx + 2)
        harmonic_levels.append(float(np.max(sp_db[lo:hi])))

    h1_h2 = float(harmonic_levels[0] - harmonic_levels[1]) if len(harmonic_levels) >= 2 else 0.0
    hcount = float(sum(1 for level in harmonic_levels if level > noise_db + 8.0))
    return h1_h2, hcount


def extract_frame_acoustic_features(world: WorldFeatures) -> FrameAcousticFeatures:
    """WORLD 結果からフレーム単位の AP/HNR/倍音特徴を抽出する。"""
    frame_count = world.f0.size
    ap_mean = np.mean(world.ap, axis=1).astype(np.float32)
    ap_std = np.std(world.ap, axis=1).astype(np.float32)
    hnr = np.zeros(frame_count, dtype=np.float32)
    sp_tilt = np.zeros(frame_count, dtype=np.float32)
    h1_h2 = np.zeros(frame_count, dtype=np.float32)
    hcount = np.zeros(frame_count, dtype=np.float32)
    harmonic_score = np.zeros(frame_count, dtype=np.float32)

    log_sp_all = np.log(np.maximum(world.sp, EPS))

    for idx in range(frame_count):
        if not bool(world.voiced_mask[idx]):
            continue

        f0 = float(world.f0[idx])
        hnr[idx] = compute_hnr_from_world(world.sp[idx], world.ap[idx])
        sp_tilt[idx] = _frame_sp_tilt(log_sp_all[idx])
        frame_h1_h2, frame_hcount = _frame_harmonic_stats(
            sp_frame=world.sp[idx],
            f0=f0,
            sample_rate=world.sample_rate,
        )
        h1_h2[idx] = frame_h1_h2
        hcount[idx] = frame_hcount
        harmonic_score[idx] = compute_harmonic_score(
            h1_h2=frame_h1_h2,
            hcount=frame_hcount,
            slope=float(sp_tilt[idx]),
        )

    voiced_f0 = world.f0[world.voiced_mask].astype(np.float32)
    voiced_f0_std = _rolling_std(voiced_f0, window=5)
    f0_std = np.zeros(frame_count, dtype=np.float32)
    f0_std[world.voiced_mask] = voiced_f0_std

    return FrameAcousticFeatures(
        f0=world.f0.astype(np.float32),
        f0_std=f0_std,
        ap_mean=ap_mean,
        ap_std=ap_std,
        hnr=hnr,
        sp_tilt=sp_tilt,
        h1_h2=h1_h2,
        hcount=hcount,
        harmonic_score=harmonic_score,
        voiced_mask=world.voiced_mask.copy(),
    )


def _ap_band_features(ap_voiced: np.ndarray) -> list[float]:
    """AP 由来の特徴を作る（裏声指標を重視）。"""
    if ap_voiced.size == 0:
        return [0.0] * 8

    n_bins = ap_voiced.shape[1]
    low_end = max(1, n_bins // 4)
    mid_end = max(low_end + 1, n_bins // 2)

    ap_global_mean, ap_global_std = _safe_stats(ap_voiced)
    low_ap_mean, low_ap_std = _safe_stats(ap_voiced[:, :low_end])
    mid_ap_mean, mid_ap_std = _safe_stats(ap_voiced[:, low_end:mid_end])
    high_ap_mean, high_ap_std = _safe_stats(ap_voiced[:, mid_end:])

    return [
        ap_global_mean,
        ap_global_std,
        low_ap_mean,
        low_ap_std,
        mid_ap_mean,
        mid_ap_std,
        high_ap_mean,
        high_ap_std,
    ]


def _sp_shape_features(sp_voiced: np.ndarray) -> list[float]:
    """SP 由来の形状特徴（音色の補助指標）を作る。"""
    if sp_voiced.size == 0:
        return [0.0] * 6

    power = np.maximum(sp_voiced, EPS)
    norm = power / np.maximum(np.sum(power, axis=1, keepdims=True), EPS)

    bins = np.arange(norm.shape[1], dtype=np.float64)
    centroid = np.sum(norm * bins[None, :], axis=1)

    rolloff = np.zeros(norm.shape[0], dtype=np.float64)
    cumsum = np.cumsum(norm, axis=1)
    for i in range(norm.shape[0]):
        rolloff[i] = float(np.searchsorted(cumsum[i], 0.85))

    geometric = np.exp(np.mean(np.log(power), axis=1))
    arithmetic = np.mean(power, axis=1)
    flatness = geometric / np.maximum(arithmetic, EPS)

    c_mean, c_std = _safe_stats(centroid)
    r_mean, r_std = _safe_stats(rolloff)
    f_mean, f_std = _safe_stats(flatness)

    return [c_mean, c_std, r_mean, r_std, f_mean, f_std]


def aggregate_world_features(world: WorldFeatures) -> tuple[np.ndarray, list[str]]:
    """
    WORLD フレーム特徴をセグメント特徴へ集約する。

    Returns:
        (features, feature_names)
    """
    voiced = world.voiced_mask
    f0_voiced = world.f0[voiced]
    sp_voiced = world.sp[voiced]
    ap_voiced = world.ap[voiced]

    log_f0 = np.log(np.maximum(f0_voiced, EPS))
    f0_mean, f0_std = _safe_stats(f0_voiced)
    logf0_mean, logf0_std = _safe_stats(log_f0)

    features: list[float] = [
        f0_mean,
        f0_std,
        logf0_mean,
        logf0_std,
        float(np.max(f0_voiced) - np.min(f0_voiced)),
        float(np.sum(voiced) / len(world.f0)),
    ]
    names: list[str] = [
        "f0_mean",
        "f0_std",
        "logf0_mean",
        "logf0_std",
        "f0_range",
        "voiced_ratio",
    ]

    ap_values = _ap_band_features(ap_voiced)
    ap_names = [
        "ap_global_mean",
        "ap_global_std",
        "ap_low_mean",
        "ap_low_std",
        "ap_mid_mean",
        "ap_mid_std",
        "ap_high_mean",
        "ap_high_std",
    ]

    sp_values = _sp_shape_features(sp_voiced)
    sp_names = [
        "sp_centroid_mean",
        "sp_centroid_std",
        "sp_rolloff_mean",
        "sp_rolloff_std",
        "sp_flatness_mean",
        "sp_flatness_std",
    ]

    features.extend(ap_values)
    names.extend(ap_names)
    features.extend(sp_values)
    names.extend(sp_names)

    return np.array(features, dtype=np.float32), names


def split_register_by_aperiodicity(world: WorldFeatures) -> tuple[np.ndarray, np.ndarray]:
    """
    AP を主指標に地声/裏声フレームを分離する。

    Returns:
        (chest_mask, falsetto_mask)
    """
    voiced = world.voiced_mask
    if int(np.sum(voiced)) == 0:
        empty = np.zeros_like(voiced, dtype=bool)
        return empty, empty

    ap_mean_per_frame = np.mean(world.ap, axis=1)
    voiced_ap = ap_mean_per_frame[voiced]

    ap_threshold = float(np.median(voiced_ap) + 0.35 * np.std(voiced_ap))
    ap_threshold = float(np.clip(ap_threshold, 0.35, 0.75))

    falsetto_mask = voiced & (ap_mean_per_frame >= ap_threshold) & (world.f0 >= FALSETTO_HARD_MIN_HZ)
    chest_mask = voiced & (~falsetto_mask)

    # 過剰分離を防ぐため、どちらかが極端に少ない場合は全有声音を地声扱いに戻す。
    if np.sum(chest_mask) < 3 or np.sum(falsetto_mask) < 3:
        chest_mask = voiced.copy()
        falsetto_mask = np.zeros_like(voiced, dtype=bool)

    return chest_mask, falsetto_mask


def extract_segment_features(y: np.ndarray, sr: int) -> tuple[np.ndarray, list[str], WorldFeatures]:
    """音声波形から学習・推論用のセグメント特徴を抽出する。"""
    world = extract_world_features(y=y, sr=sr)
    features, names = aggregate_world_features(world)
    return features, names, world
