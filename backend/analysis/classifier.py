"""classifier.py — AP/HNR ゲート + RF フォールバック + 20次元ベクトル併用判定器

設計方針:
1. AP高 AND HNR低 → 裏声確定（ゲート）
2. AP低 AND HNR高 → 地声確定（ゲート）
3. 片側のみ成立（曖昧）→ RF chest probability でフォールバック
4. f0 < FALSETTO_HARD_MIN_HZ は物理的に裏声不可なので常に地声
5. セグメントレベルでは 20次元ベクトル RF の確率とフレーム比率を併用
"""

from __future__ import annotations

from dataclasses import dataclass

from config import (
    AP_THRESHOLD_HIGH,
    AP_THRESHOLD_TRANSITION,
    FALSETTO_HARD_MIN_HZ,
    HIGH_REGISTER_MIN_HZ,
    HNR_THRESHOLD_HIGH,
    HNR_THRESHOLD_TRANSITION,
    REGISTER_LOG_LEVEL,
    RF_CHEST_THRESHOLD,
)


@dataclass
class HybridClassifier:
    """
    AP/HNR ゲート先行 + RF フォールバック分類器。

    判定フロー:
      1. f0 < falsetto_hard_min_hz → 地声確定（物理的制約）
      2. AP高 AND HNR低 → 裏声確定（ゲート）
      3. AP低 AND HNR高 → 地声確定（ゲート）
      4. 片側のみ成立（曖昧）→ RF の chest probability でフォールバック
    """

    falsetto_hard_min_hz: float = FALSETTO_HARD_MIN_HZ      # この Hz 未満は地声確定
    high_register_min_hz: float = HIGH_REGISTER_MIN_HZ      # 高音域の閾値切替ポイント (C5)
    ap_threshold_high: float = AP_THRESHOLD_HIGH            # 高音域の AP 閾値
    ap_threshold_transition: float = AP_THRESHOLD_TRANSITION  # 遷移帯域の AP 閾値
    hnr_threshold_high: float = HNR_THRESHOLD_HIGH          # 高音域の HNR 閾値 (dB)
    hnr_threshold_transition: float = HNR_THRESHOLD_TRANSITION  # 遷移帯域の HNR 閾値 (dB)
    rf_chest_threshold: float = RF_CHEST_THRESHOLD          # 曖昧フレームの RF 判定閾値

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
        """
        1フレームを分類し、ラベルと判定理由を返す。

        Args:
            f0: 基本周波数 (Hz)。0 なら無声音。
            ap_mean: 非周期性の平均 (0-1)。高いほど裏声的。
            hnr: 調波対雑音比 (dB)。低いほど裏声的。
            rf_chest_proba: RF モデルの chest 確率 (0-1)。

        Returns:
            (ラベル, 判定理由) のタプル。
        """
        if f0 == 0.0:
            return "unvoiced", "no_f0"
        if f0 < self.falsetto_hard_min_hz:
            return "chest", "below_hard_min"

        ap_thresh, hnr_thresh = self._band_thresholds(f0)
        ap_high = ap_mean > ap_thresh
        hnr_low = hnr < hnr_thresh

        # 両方成立 → 確定
        if ap_high and hnr_low:
            return "falsetto", "gate_ap_hnr"
        if (not ap_high) and (not hnr_low):
            return "chest", "gate_ap_hnr"

        # 片側のみ → RF フォールバック
        if rf_chest_proba > self.rf_chest_threshold:
            return "chest", "rf_fallback"
        return "falsetto", "rf_fallback"


def classify_segment(
    chest_frame_count: int,
    falsetto_frame_count: int,
    rf_chest_probability: float,
) -> tuple[str, float]:
    """
    フレーム判定結果と RF 信頼度からセグメントラベルを決定する。

    Args:
        chest_frame_count: 地声フレーム数。
        falsetto_frame_count: 裏声フレーム数。
        rf_chest_probability: 20次元ベクトル RF の chest 確率 (0-1)。

    Returns:
        (ラベル, 信頼度) のタプル。
    """
    total = chest_frame_count + falsetto_frame_count
    if total == 0:
        return "chest", rf_chest_probability

    # フレーム比率
    frame_chest_ratio = chest_frame_count / total

    # フレーム比率と RF を平均して最終信頼度とする
    combined_chest = (frame_chest_ratio + rf_chest_probability) / 2.0

    if combined_chest >= 0.5:
        return "chest", combined_chest
    return "falsetto", 1.0 - combined_chest


def print_classification_summary(
    chest_count: int,
    falsetto_count: int,
    unvoiced_count: int,
    rf_chest_probability: float,
) -> None:
    """判定サマリーを出力する。"""
    if REGISTER_LOG_LEVEL == 0:
        return

    total = chest_count + falsetto_count + unvoiced_count
    if total == 0:
        return

    print("\n[REGISTER SUMMARY] AP/HNRゲート + RF + 20次元ベクトル併用判定")
    print(f"  ├─ 地声: {chest_count}フレーム")
    print(f"  ├─ 裏声: {falsetto_count}フレーム")
    print(f"  ├─ 無声音: {unvoiced_count}フレーム")
    print(f"  └─ RF chest確率: {rf_chest_probability:.3f}")
