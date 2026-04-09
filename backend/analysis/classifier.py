"""classifier.py — ゲート先行ハイブリッド判定器

設計方針:
1. AP高 AND HNR低 を裏声の強条件とする。
2. AP高 XOR HNR低 は曖昧扱いとして RF 胸声モデルへフォールバックする。
3. 判定ハード下限より低い f0 は常に地声とする。
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from config import (
    AP_THRESHOLD_HIGH,
    AP_THRESHOLD_TRANSITION,
    CREPE_NOISE_GATE,
    FALSETTO_HARD_MIN_HZ,
    HIGH_REGISTER_MIN_HZ,
    HNR_THRESHOLD_HIGH,
    HNR_THRESHOLD_TRANSITION,
    REGISTER_LOG_INTERVAL,
    REGISTER_LOG_LEVEL,
    RF_CHEST_THRESHOLD,
)

try:
    from analysis.features import compute_hnr as compute_hnr_corr
    from analysis.features import extract_features
except ImportError:
    compute_hnr_corr = None
    extract_features = None


_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ml", "models", "register_model.joblib")
_MODEL_CACHE: Any | None = None
_MODEL_META_CACHE: dict[str, Any] | None = None
_MODEL_MTIME: float = 0.0
_LAST_CHECK_TIME: float = 0.0
_CHECK_INTERVAL_SEC: float = 30.0


@dataclass
class RegisterStats:
    """フレーム判定の統計情報。"""

    log_counter: int = 0
    chest: int = 0
    falsetto: int = 0
    unvoiced: int = 0
    gate_ap_hnr: int = 0
    rf_fallback: int = 0


@dataclass
class HybridClassifier:
    """AP/HNR ゲート先行 + RF フォールバック分類器。"""

    falsetto_hard_min_hz: float = FALSETTO_HARD_MIN_HZ
    high_register_min_hz: float = HIGH_REGISTER_MIN_HZ
    ap_threshold_high: float = AP_THRESHOLD_HIGH
    ap_threshold_transition: float = AP_THRESHOLD_TRANSITION
    hnr_threshold_high: float = HNR_THRESHOLD_HIGH
    hnr_threshold_transition: float = HNR_THRESHOLD_TRANSITION
    rf_chest_threshold: float = RF_CHEST_THRESHOLD

    def _band_thresholds(self, f0: float) -> tuple[float, float]:
        """f0 帯域に応じた AP/HNR 閾値を返す。"""
        if f0 >= self.high_register_min_hz:
            return self.ap_threshold_high, self.hnr_threshold_high
        return self.ap_threshold_transition, self.hnr_threshold_transition

    def classify_frame(
        self,
        f0: float,
        ap_mean: float,
        hnr: float,
        rf_chest_proba: float,
    ) -> tuple[str, str]:
        """1フレームを分類し、ラベルと判定理由を返す。"""
        if f0 == 0.0:
            return "unvoiced", "no_f0"
        if f0 < self.falsetto_hard_min_hz:
            return "chest", "below_hard_min"

        ap_thresh, hnr_thresh = self._band_thresholds(f0)
        ap_high = ap_mean > ap_thresh
        hnr_low = hnr < hnr_thresh

        if ap_high and hnr_low:
            return "falsetto", "gate_ap_hnr"
        if (not ap_high) and (not hnr_low):
            return "chest", "gate_ap_hnr"

        if rf_chest_proba > self.rf_chest_threshold:
            return "chest", "rf_fallback"
        return "falsetto", "rf_fallback"


def new_register_stats() -> RegisterStats:
    """統計オブジェクトを初期化する。"""
    return RegisterStats()


def _should_log_verbose(stats: RegisterStats) -> bool:
    """詳細ログの出力可否を判定する。"""
    return REGISTER_LOG_LEVEL >= 3 or (
        REGISTER_LOG_LEVEL == 2 and stats.log_counter % REGISTER_LOG_INTERVAL == 0
    )


def _load_model_if_needed() -> tuple[Any | None, dict[str, Any] | None]:
    """RF モデルを遅延ロードし、変更時に再ロードする。"""
    global _MODEL_CACHE, _MODEL_META_CACHE, _MODEL_MTIME, _LAST_CHECK_TIME

    now = time.monotonic()
    if _MODEL_CACHE is not None and (now - _LAST_CHECK_TIME) < _CHECK_INTERVAL_SEC:
        return _MODEL_CACHE, _MODEL_META_CACHE
    _LAST_CHECK_TIME = now

    if not os.path.exists(_MODEL_PATH):
        _MODEL_CACHE = None
        _MODEL_META_CACHE = None
        _MODEL_MTIME = 0.0
        return None, None

    current_mtime = os.path.getmtime(_MODEL_PATH)
    if _MODEL_CACHE is not None and current_mtime == _MODEL_MTIME:
        return _MODEL_CACHE, _MODEL_META_CACHE

    try:
        import joblib

        loaded = joblib.load(_MODEL_PATH)
        if isinstance(loaded, dict) and "model" in loaded:
            _MODEL_CACHE = loaded["model"]
            _MODEL_META_CACHE = {
                "chest_label": int(loaded.get("chest_label", 1)),
            }
        else:
            _MODEL_CACHE = loaded
            _MODEL_META_CACHE = {"chest_label": 0}
        _MODEL_MTIME = current_mtime
        print(f"[INFO] MLモデルをロードしました: {_MODEL_PATH}")
    except Exception as exc:
        print(f"[WARN] MLモデルのロードに失敗しました: {exc}")
        _MODEL_CACHE = None
        _MODEL_META_CACHE = None

    return _MODEL_CACHE, _MODEL_META_CACHE


def predict_rf_chest_probability(features: np.ndarray) -> float:
    """セグメント特徴から chest 確率を返す。"""
    model, meta = _load_model_if_needed()
    if model is None or meta is None:
        return 0.5

    x = features.reshape(1, -1)
    if hasattr(model, "predict_proba"):
        prob = model.predict_proba(x)[0]
        classes = getattr(model, "classes_", None)
        chest_label = int(meta.get("chest_label", 1))
        if classes is not None:
            for idx, cls in enumerate(classes):
                if int(cls) == chest_label:
                    return float(prob[idx])
        return float(np.max(prob))

    pred = int(model.predict(x)[0])
    return 1.0 if pred == int(meta.get("chest_label", 1)) else 0.0


def classify_register(
    y: np.ndarray,
    sr: int,
    f0: float,
    median_freq: float = 0.0,
    already_separated: bool = False,
    crepe_conf: float = 1.0,
    stats: RegisterStats | None = None,
) -> str:
    """互換 API: 1フレームを地声/裏声/unknown に分類する。"""
    del median_freq
    del already_separated

    local_stats = stats if stats is not None else RegisterStats()

    if f0 <= 0.0 or len(y) < 512:
        local_stats.unvoiced += 1
        return "unknown"

    if crepe_conf < CREPE_NOISE_GATE:
        local_stats.unvoiced += 1
        return "unknown"

    rf_proba = 0.5
    ap_mean = 0.0
    hnr_db = 0.0

    if extract_features is not None:
        feat = extract_features(y, sr, f0)
        if feat is not None:
            # 既存特徴の hnr は自己相関ベース(0-1)。
            hnr_corr = float(feat[3])
            hnr_corr = float(np.clip(hnr_corr, 1e-4, 0.9999))
            hnr_db = float(10.0 * np.log10(hnr_corr / (1.0 - hnr_corr)))
            ap_mean = float(np.clip(1.0 - hnr_corr, 0.0, 1.0))

            model, meta = _load_model_if_needed()
            if model is not None and meta is not None and hasattr(model, "predict_proba"):
                proba = model.predict_proba(feat.reshape(1, -1))[0]
                classes = getattr(model, "classes_", None)
                chest_label = int(meta.get("chest_label", 1))
                if classes is not None:
                    for idx, cls in enumerate(classes):
                        if int(cls) == chest_label:
                            rf_proba = float(proba[idx])
                            break

    classifier = HybridClassifier()
    label, reason = classifier.classify_frame(
        f0=float(f0),
        ap_mean=ap_mean,
        hnr=hnr_db,
        rf_chest_proba=rf_proba,
    )

    local_stats.log_counter += 1
    if label == "chest":
        local_stats.chest += 1
    elif label == "falsetto":
        local_stats.falsetto += 1
    else:
        local_stats.unvoiced += 1

    if reason == "gate_ap_hnr":
        local_stats.gate_ap_hnr += 1
    elif reason == "rf_fallback":
        local_stats.rf_fallback += 1

    if _should_log_verbose(local_stats):
        print(
            f"[REGISTER/GATE] f0={f0:.1f}Hz ap={ap_mean:.3f} hnr={hnr_db:.2f}dB "
            f"rf={rf_proba:.3f} -> {label} ({reason})"
        )

    return "unknown" if label == "unvoiced" else label


def print_register_summary(stats: RegisterStats) -> None:
    """判定サマリーを出力する。"""
    if REGISTER_LOG_LEVEL == 0:
        return

    total = stats.chest + stats.falsetto + stats.unvoiced
    if total == 0:
        return

    print("\n[REGISTER SUMMARY] 合計判定数: " f"{total}フレーム")
    print(f"  ├─ 地声: {stats.chest}フレーム")
    print(f"  ├─ 裏声: {stats.falsetto}フレーム")
    print(f"  ├─ 無声音/unknown: {stats.unvoiced}フレーム")
    print(f"  ├─ AP/HNRゲート確定: {stats.gate_ap_hnr}フレーム")
    print(f"  └─ RFフォールバック: {stats.rf_fallback}フレーム")
