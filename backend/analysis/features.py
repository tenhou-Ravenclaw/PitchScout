"""
features.py — 地声/裏声判定用の特徴量抽出

register_classifier.py の既存ロジックから6特徴量を抽出する共通モジュール。
ラベリング・学習・推論で同一の特徴量を使うことを保証する。

特徴量:
  0: h1_h2       H1-H2差 (dB)
  1: hcount      有効倍音本数 (0-10)
  2: slope       倍音減衰スロープ (dB/harmonic)
  3: hnr         調波対雑音比 (0-1)
  4: centroid_r  スペクトル重心 / f0
  5: f0          基本周波数 (Hz)
"""

import numpy as np
import librosa

FEATURE_NAMES = ["h1_h2", "hcount", "slope", "hnr", "centroid_r", "f0"]
N_FEATURES = len(FEATURE_NAMES)


def get_peak_db(fft: np.ndarray, freqs: np.ndarray,
                target_hz: float, sr: int) -> float:
    if target_hz <= 0 or target_hz >= sr / 2 * 0.95:
        return -120.0
    half_win = max(10.0, target_hz * 0.035)
    lo = max(1, np.searchsorted(freqs, target_hz - half_win))
    hi = min(len(fft) - 2, np.searchsorted(freqs, target_hz + half_win))
    if lo >= hi:
        return -120.0
    pk = lo + int(np.argmax(fft[lo:hi + 1]))
    a, b, c = fft[pk - 1], fft[pk], fft[pk + 1]
    denom = a - 2 * b + c
    if abs(denom) > 1e-12:
        offset = 0.5 * (a - c) / denom
        peak = b - 0.25 * (a - c) * offset
        if peak > b * 2.0 or peak < 0:
            peak = b
    else:
        peak = b
    return 20.0 * np.log10(max(peak, 1e-10))


def compute_hnr(y: np.ndarray, sr: int, f0: float) -> float:
    try:
        win = np.hanning(len(y))
        ac = np.correlate(y * win, y * win, mode='full')
        ac = ac[len(ac) // 2:]
        if ac[0] < 1e-10:
            return 0.5
        ac /= ac[0]
        lag = int(round(sr / f0))
        if lag < 5 or lag >= len(ac) - 5:
            return 0.5
        return float(np.clip(np.max(ac[lag - 3: lag + 4]), 0.0, 1.0))
    except Exception:
        return 0.5


def extract_features(y: np.ndarray, sr: int, f0: float) -> np.ndarray | None:
    """
    音声フレームから6特徴量を抽出。

    Args:
        y:  音声波形（1フレーム分、2048サンプル程度）
        sr: サンプリングレート
        f0: 基本周波数 (Hz)

    Returns:
        shape=(6,) の特徴量配列。抽出不能なら None。
    """
    if f0 <= 0 or len(y) < 512:
        return None

    # FFT
    n_fft = 8192
    win = np.hanning(len(y))
    y_pad = np.zeros(n_fft)
    y_pad[:len(y)] = y * win
    fft = np.abs(np.fft.rfft(y_pad))
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    noise_db = 20.0 * np.log10(float(np.percentile(fft, 5)) + 1e-12)

    H = [get_peak_db(fft, freqs, f0 * n, sr) for n in range(1, 11)]
    h1 = H[0]

    if h1 <= -60:
        return None

    h1_h2 = h1 - H[1]
    if h1_h2 < -20.0:
        return None

    # 有効倍音本数
    hcount = sum(1 for db in H[:10] if db > noise_db + 8.0)

    # 倍音減衰スロープ
    slope_pts = [(i + 1, H[i]) for i in range(8) if H[i] > noise_db + 8.0]
    if len(slope_pts) >= 3:
        xs = np.array([p[0] for p in slope_pts], dtype=float)
        ys = np.array([p[1] for p in slope_pts], dtype=float)
        slope = float(np.polyfit(xs, ys, 1)[0])
    else:
        slope = -6.0  # デフォルト（中間的な値）

    # HNR
    hnr = compute_hnr(y, sr, f0)

    # スペクトル重心 / f0
    centroid = float(librosa.feature.spectral_centroid(y=y, sr=sr)[0, 0])
    centroid_r = centroid / f0 if f0 > 0 else 0.0

    return np.array([h1_h2, hcount, slope, hnr, centroid_r, f0], dtype=np.float32)
