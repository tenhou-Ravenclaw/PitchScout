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

from config import FALSETTO_DISPLAY_MIN_HZ

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

    falsetto_mask = (
        voiced
        & (ap_mean_per_frame >= ap_threshold)
        & (world.f0 >= FALSETTO_DISPLAY_MIN_HZ)
    )
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
