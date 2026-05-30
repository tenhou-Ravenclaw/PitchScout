"""
pipeline.py — AP/HNR ゲート + 20次元ベクトル RF 推論パイプライン

処理フロー:
  1) 音声読み込み・正規化
  2) WORLD 特徴抽出 (F0/SP/AP) → 20次元セグメント特徴
  3) RF モデルで chest probability を推定
  4) AP/HNR ゲート + RF フォールバックでフレーム分離
  5) フレーム比率 + RF を併用して最終判定
  6) FastAPI 互換レスポンス整形
"""

from __future__ import annotations

import os
from typing import Any

import numpy as np
import soundfile as sf

import joblib

from analysis.classifier import (
    HybridClassifier,
    classify_segment,
    print_classification_summary,
)
from analysis.feature_extractor import (
    FrameAcousticFeatures,
    WorldFeatures,
    extract_frame_acoustic_features,
    extract_segment_features,
)
from analysis.scoring import analyze_singing_ability
from config import (
    FALSETTO_HARD_MIN_HZ,
    REGISTER_LOG_LEVEL,
    SUSTAINED_CHEST_MIN_FRAMES,
    SUSTAINED_FALSETTO_MIN_FRAMES,
    SUSTAINED_LOW_MIN_FRAMES,
    VOICE_MAX_HZ,
    VOICE_MIN_HZ,
)
from note_converter import hz_to_label_and_hz

_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "ml", "models", "register_model.joblib"
)
_MODEL_CACHE: Any | None = None
_MODEL_META_CACHE: dict[str, Any] | None = None
_EXPECTED_FEATURE_DIM = 20


def _load_model() -> tuple[Any, dict[str, Any]]:
    """RandomForest モデルをロード（遅延ロード）。"""
    global _MODEL_CACHE, _MODEL_META_CACHE
    if _MODEL_CACHE is not None and _MODEL_META_CACHE is not None:
        return _MODEL_CACHE, _MODEL_META_CACHE

    if not os.path.exists(_MODEL_PATH):
        raise FileNotFoundError(
            f"分類モデルが見つかりません: {_MODEL_PATH}。先に backend/ml/train.py を実行してください。"
        )

    loaded = joblib.load(_MODEL_PATH)

    if isinstance(loaded, dict) and "model" in loaded:
        _MODEL_CACHE = loaded["model"]
        _MODEL_META_CACHE = {
            "task": loaded.get("task", "chest_detector"),
            "chest_label": int(loaded.get("chest_label", 1)),
            "chest_probability_threshold": float(loaded.get("chest_probability_threshold", 0.55)),
        }
    else:
        _MODEL_CACHE = loaded
        _MODEL_META_CACHE = {
            "task": "legacy",
            "chest_label": 0,
            "chest_probability_threshold": 0.5,
        }

    # 20次元との整合を事前検証する
    n_features_in = None
    scaler = getattr(_MODEL_CACHE, "named_steps", {}).get("scaler") if hasattr(_MODEL_CACHE, "named_steps") else None
    if scaler is not None:
        n_features_in = getattr(scaler, "n_features_in_", None)
    if n_features_in is None:
        n_features_in = getattr(_MODEL_CACHE, "n_features_in_", None)

    if n_features_in is not None and int(n_features_in) != _EXPECTED_FEATURE_DIM:
        raise RuntimeError(
            "学習済みモデルの特徴次元が不一致です。"
            f" expected={_EXPECTED_FEATURE_DIM}, model={int(n_features_in)}。"
            " backend/ml/train.py で再学習して register_model.joblib を更新してください。"
        )

    return _MODEL_CACHE, _MODEL_META_CACHE


def _predict_chest_confidence(features: np.ndarray) -> float:
    """
    20次元ベクトルから RF で chest 確率を推定する。

    predict_proba が利用可能ならクラス確率を使用し、
    なければ predict の結果を 0/1 に変換する。

    Args:
        features: 20次元のセグメント特徴量ベクトル。

    Returns:
        0-1 の chest 確率。
    """
    model, meta = _load_model()
    x = features.reshape(1, -1)

    if hasattr(model, "predict_proba"):
        prob = model.predict_proba(x)[0]
        classes = getattr(model, "classes_", None)
        if classes is not None:
            chest_label = meta["chest_label"]
            for i, cls in enumerate(classes):
                if int(cls) == chest_label:
                    return float(prob[i])
        return float(np.max(prob))

    pred = int(model.predict(x)[0])
    return 1.0 if pred == int(meta["chest_label"]) else 0.0


def _split_by_gate(
    world: WorldFeatures,
    frame_features: FrameAcousticFeatures,
    rf_chest_probability: float,
    no_falsetto: bool,
) -> tuple[np.ndarray, np.ndarray]:
    """
    AP/HNR ゲート + RF フォールバックでフレーム単位に地声/裏声を分離する。

    Args:
        world: WORLD 特徴。
        frame_features: フレーム音響特徴（ap_mean, hnr を含む）。
        rf_chest_probability: 20次元ベクトル RF の chest 確率。
        no_falsetto: True なら裏声分離を無効化。

    Returns:
        (chest_mask, falsetto_mask)
    """
    voiced_mask = world.voiced_mask.copy()

    if no_falsetto:
        return voiced_mask, np.zeros_like(voiced_mask, dtype=bool)

    classifier = HybridClassifier()
    chest_mask = np.zeros_like(voiced_mask, dtype=bool)
    falsetto_mask = np.zeros_like(voiced_mask, dtype=bool)

    for idx in np.where(voiced_mask)[0]:
        label, _ = classifier.classify_frame(
            f0=float(frame_features.f0[idx]),
            ap_mean=float(frame_features.ap_mean[idx]),
            hnr=float(frame_features.hnr[idx]),
            rf_chest_proba=rf_chest_probability,
        )
        if label == "chest":
            chest_mask[idx] = True
        elif label == "falsetto":
            falsetto_mask[idx] = True

    return chest_mask, falsetto_mask


def _filter_unsustained_top(
    f0: np.ndarray,
    mask: np.ndarray,
    min_consecutive: int = SUSTAINED_CHEST_MIN_FRAMES,
) -> np.ndarray:
    """
    最高音ノートが min_consecutive フレーム以上連続していなければ除外する。

    繰り返し適用し、報告される最高音が必ず持続音であることを保証する。
    ノイズや楽器リークによる瞬間的な高音ピーク誤検出を排除する目的。

    Args:
        f0: 全フレームの基本周波数配列。
        mask: 対象フレームの boolean マスク（chest_mask / falsetto_mask）。
        min_consecutive: 最高音として認定する最小連続フレーム数。

    Returns:
        非持続の最高音フレームを除外した新しいマスク。
    """
    result_mask = mask.copy()

    # 有効範囲内のフレームのノートラベルを事前計算
    all_indices = np.where(mask)[0]
    labels: dict[int, str] = {}
    for idx in all_indices:
        hz_val = float(f0[idx])
        if VOICE_MIN_HZ <= hz_val <= VOICE_MAX_HZ:
            label, _ = hz_to_label_and_hz(hz_val)
            labels[idx] = label

    while True:
        # 現在有効なフレームを取得
        active = sorted(idx for idx in labels if result_mask[idx])
        if not active:
            break

        # 最高音のノートラベルを特定
        max_hz = max(f0[idx] for idx in active)
        max_label, _ = hz_to_label_and_hz(max_hz)

        # そのラベルに該当するフレームのインデックス（時系列順）
        top_indices = [idx for idx in active if labels[idx] == max_label]
        if not top_indices:
            break

        # 最大連続フレーム数を計算
        best_run = 1
        run = 1
        for i in range(1, len(top_indices)):
            if top_indices[i] == top_indices[i - 1] + 1:
                run += 1
                best_run = max(best_run, run)
            else:
                run = 1

        if best_run >= min_consecutive:
            break  # 最高音が持続音として確認された

        # 非持続の最高音フレームをマスクから除外
        removed_label = max_label
        for idx in top_indices:
            result_mask[idx] = False

        removed_count = len(top_indices)
        if removed_count > 0:
            print(
                f"[DEBUG] 持続音フィルタ: {removed_label} を除外 "
                f"({removed_count}フレーム, 最大連続{best_run}フレーム "
                f"< 閾値{min_consecutive})"
            )

    return result_mask


def _filter_unsustained_bottom(
    f0: np.ndarray,
    mask: np.ndarray,
    min_consecutive: int = SUSTAINED_LOW_MIN_FRAMES,
) -> np.ndarray:
    """
    最低音ノートが min_consecutive フレーム以上連続していなければ除外する。

    _filter_unsustained_top の最低音版。

    Args:
        f0: 全フレームの基本周波数配列。
        mask: 対象フレームの boolean マスク。
        min_consecutive: 最低音として認定する最小連続フレーム数。

    Returns:
        非持続の最低音フレームを除外した新しいマスク。
    """
    result_mask = mask.copy()

    all_indices = np.where(mask)[0]
    labels: dict[int, str] = {}
    for idx in all_indices:
        hz_val = float(f0[idx])
        if VOICE_MIN_HZ <= hz_val <= VOICE_MAX_HZ:
            label, _ = hz_to_label_and_hz(hz_val)
            labels[idx] = label

    while True:
        active = sorted(idx for idx in labels if result_mask[idx])
        if not active:
            break

        min_hz = min(f0[idx] for idx in active)
        min_label, _ = hz_to_label_and_hz(min_hz)

        bottom_indices = [idx for idx in active if labels[idx] == min_label]
        if not bottom_indices:
            break

        best_run = 1
        run = 1
        for i in range(1, len(bottom_indices)):
            if bottom_indices[i] == bottom_indices[i - 1] + 1:
                run += 1
                best_run = max(best_run, run)
            else:
                run = 1

        if best_run >= min_consecutive:
            break

        for idx in bottom_indices:
            result_mask[idx] = False

        removed_count = len(bottom_indices)
        if removed_count > 0:
            print(
                f"[DEBUG] 持続音フィルタ(低): {min_label} を除外 "
                f"({removed_count}フレーム, 最大連続{best_run}フレーム "
                f"< 閾値{min_consecutive})"
            )

    return result_mask


def _safe_note_list(f0: np.ndarray) -> list[float]:
    """
    人声音域に収まる周波数のみリスト化する。

    VOICE_MIN_HZ ～ VOICE_MAX_HZ の範囲外のフレームを除外する。

    Args:
        f0: 基本周波数の配列。

    Returns:
        有効な周波数のリスト。
    """
    if f0.size == 0:
        return []
    mask = (f0 >= VOICE_MIN_HZ) & (f0 <= VOICE_MAX_HZ)
    return f0[mask].astype(float).tolist()


def _add_range(result: dict[str, Any], notes: list[float], prefix: str) -> None:
    """
    周波数リストを音階ラベル付きレンジ情報へ変換し result に追加する。

    {prefix}_min, {prefix}_max, {prefix}_min_hz, {prefix}_max_hz, {prefix}_count を設定する。
    notes が空の場合は何も追加しない。

    Args:
        result: 結果辞書（直接変更される）。
        notes: 周波数のリスト (Hz)。
        prefix: キーの接頭辞（"chest" / "falsetto"）。
    """
    if not notes:
        return

    arr = np.array(notes, dtype=np.float64)
    lo_label, lo_hz = hz_to_label_and_hz(float(np.min(arr)))
    hi_label, hi_hz = hz_to_label_and_hz(float(np.max(arr)))

    result[f"{prefix}_min"] = lo_label
    result[f"{prefix}_max"] = hi_label
    result[f"{prefix}_min_hz"] = lo_hz
    result[f"{prefix}_max_hz"] = hi_hz
    result[f"{prefix}_count"] = int(arr.size)


def _build_note_distribution(
    chest_notes: list[float],
    falsetto_notes: list[float],
) -> list[dict[str, Any]]:
    """
    音階ごとのフレーム数を集計する。

    地声・裏声それぞれのフレーム数を音階ラベル別にまとめ、
    フロントエンドでの分布表示用データを返す。
    低音から高音順にソートされる。

    Args:
        chest_notes: 地声フレームの Hz リスト。
        falsetto_notes: 裏声フレームの Hz リスト。

    Returns:
        [{"label": "mid2C", "hz": 262.8, "chest": 45, "falsetto": 0, "total": 45}, ...]
    """
    from collections import Counter

    chest_labels = [hz_to_label_and_hz(hz)[0] for hz in chest_notes]
    falsetto_labels = [hz_to_label_and_hz(hz)[0] for hz in falsetto_notes]

    chest_counts = Counter(chest_labels)
    falsetto_counts = Counter(falsetto_labels)
    all_labels = set(chest_counts) | set(falsetto_counts)

    dist: list[dict[str, Any]] = []
    for label in all_labels:
        _, defined_hz = hz_to_label_and_hz(0)  # ダミー
        # label → Hz を逆引き
        for hz_val in chest_notes + falsetto_notes:
            lbl, dhz = hz_to_label_and_hz(hz_val)
            if lbl == label:
                defined_hz = dhz
                break

        c = chest_counts.get(label, 0)
        f = falsetto_counts.get(label, 0)
        dist.append({
            "label": label,
            "hz": defined_hz,
            "chest": c,
            "falsetto": f,
            "total": c + f,
        })

    dist.sort(key=lambda x: x["hz"])
    return dist


def _build_result(
    world: WorldFeatures,
    chest_mask: np.ndarray,
    falsetto_mask: np.ndarray,
    segment_label: str,
    segment_confidence: float,
    frame_features: FrameAcousticFeatures,
    rf_chest_probability: float,
) -> dict[str, Any]:
    """FastAPI 互換のレスポンスを生成する。"""
    result: dict[str, Any] = {
        "register_label": segment_label,
        "register_confidence": round(segment_confidence, 4),
        "rf_chest_probability": round(rf_chest_probability, 4),
    }

    # 瞬間的なピーク（ノイズ/楽器リーク）を除外
    chest_mask = _filter_unsustained_top(world.f0, chest_mask, SUSTAINED_CHEST_MIN_FRAMES)
    chest_mask = _filter_unsustained_bottom(world.f0, chest_mask, SUSTAINED_LOW_MIN_FRAMES)
    falsetto_mask = _filter_unsustained_top(world.f0, falsetto_mask, SUSTAINED_FALSETTO_MIN_FRAMES)

    chest_notes = _safe_note_list(world.f0[chest_mask])
    falsetto_notes = _safe_note_list(world.f0[falsetto_mask])

    if not chest_notes and not falsetto_notes:
        return {"error": "有効な有声音が検出できませんでした"}

    all_notes = chest_notes + falsetto_notes
    overall_min = float(np.min(all_notes))
    overall_max = float(np.max(all_notes))
    ovr_min_label, ovr_min_hz = hz_to_label_and_hz(overall_min)
    ovr_max_label, ovr_max_hz = hz_to_label_and_hz(overall_max)

    result["overall_min"] = ovr_min_label
    result["overall_max"] = ovr_max_label
    result["overall_min_hz"] = ovr_min_hz
    result["overall_max_hz"] = ovr_max_hz

    _add_range(result, chest_notes, "chest")
    _add_range(result, falsetto_notes, "falsetto")

    total_frames = len(chest_notes) + len(falsetto_notes)
    chest_ratio = (len(chest_notes) / total_frames) * 100.0 if total_frames else 100.0
    falsetto_ratio = (len(falsetto_notes) / total_frames) * 100.0 if total_frames else 0.0

    result["chest_ratio"] = round(chest_ratio, 1)
    result["falsetto_ratio"] = round(falsetto_ratio, 1)
    result["chest_avg_hz"] = round(float(np.mean(chest_notes)), 1) if chest_notes else 0.0

    # ノート分布（音階ごとのフレーム数）
    result["note_distribution"] = _build_note_distribution(chest_notes, falsetto_notes)

    # 倍音スコア平均（デバッグ用）
    voiced_mask = world.voiced_mask
    if int(np.sum(voiced_mask)) > 0:
        result["debug_harmonic_score_mean"] = round(
            float(np.mean(frame_features.harmonic_score[voiced_mask])), 4
        )

    # 歌唱力分析
    try:
        voiced_f0 = world.f0[world.voiced_mask]
        voiced_conf = np.ones_like(voiced_f0, dtype=np.float32)
        result["singing_analysis"] = analyze_singing_ability(
            f0_array=voiced_f0,
            conf_array=voiced_conf,
            chest_notes=chest_notes,
            falsetto_notes=falsetto_notes,
            overall_min_hz=overall_min,
            overall_max_hz=overall_max,
        )
    except Exception as exc:
        print(f"[WARN] 歌唱力分析をスキップ: {exc}")

    return result


def analyze(wav_path: str, already_separated: bool = False, no_falsetto: bool = False) -> dict:
    """
    音声を解析して地声/裏声推定結果を返す。

    Args:
        wav_path: 入力 WAV パス。
        already_separated: 旧パイプラインとの互換引数。現在の WORLD パイプラインでは未使用だが、
                           routers/analysis.py が呼び出し時に渡すため署名を維持している。
        no_falsetto: True の場合は裏声分離を無効化。

    Returns:
        解析結果の辞書。エラー時は {"error": "..."} を返す。
    """
    del already_separated  # 互換維持のため署名に残すが使用しない

    print("\n============================================================")
    print(f"[INFO] AP/HNRゲート+RF解析開始: {wav_path}")
    print("============================================================")

    # 1) 音声読み込み
    try:
        y, sr = sf.read(wav_path)
        if y.ndim > 1:
            y = np.mean(y, axis=1)
        y = y.astype(np.float32)
    except Exception as exc:
        return {"error": f"WAV ファイルの読み込みに失敗しました: {exc}"}

    duration = len(y) / float(sr)
    if duration < 0.3:
        return {"error": "音声が短すぎます（0.3秒以上必要）。"}
    if float(np.max(np.abs(y))) < 1e-4:
        return {"error": "音が小さすぎます（ほぼ無音）。"}

    y = y / (float(np.max(np.abs(y))) + 1e-8) * 0.95

    # 2) WORLD 特徴抽出 → 20次元セグメント特徴
    try:
        segment_features, feature_names, world = extract_segment_features(y=y, sr=sr)
        frame_features = extract_frame_acoustic_features(world)
        if REGISTER_LOG_LEVEL >= 2:
            print(f"[DEBUG] 特徴次元: {len(segment_features)}")
    except Exception as exc:
        return {"error": f"WORLD 特徴抽出に失敗しました: {exc}"}

    # 3) RF モデルで chest probability を推定
    try:
        rf_chest_probability = _predict_chest_confidence(segment_features)
    except Exception as exc:
        print(f"[WARN] RFモデル推論失敗、デフォルト0.5を使用: {exc}")
        rf_chest_probability = 0.5

    # 4) AP/HNR ゲートでフレーム分離
    chest_mask, falsetto_mask = _split_by_gate(
        world=world,
        frame_features=frame_features,
        rf_chest_probability=rf_chest_probability,
        no_falsetto=no_falsetto,
    )

    # 5) セグメントラベル決定（フレーム比率 + RF 併用）
    chest_count = int(np.sum(chest_mask))
    falsetto_count = int(np.sum(falsetto_mask))
    unvoiced_count = int(np.sum(world.voiced_mask)) - chest_count - falsetto_count

    label, confidence = classify_segment(
        chest_frame_count=chest_count,
        falsetto_frame_count=falsetto_count,
        rf_chest_probability=rf_chest_probability,
    )

    print_classification_summary(
        chest_count=chest_count,
        falsetto_count=falsetto_count,
        unvoiced_count=unvoiced_count,
        rf_chest_probability=rf_chest_probability,
    )

    print(
        f"[INFO] 最終判定: label={label}, confidence={confidence:.3f}, "
        f"rf_chest={rf_chest_probability:.3f}"
    )

    # 6) レスポンス生成
    return _build_result(
        world=world,
        chest_mask=chest_mask,
        falsetto_mask=falsetto_mask,
        segment_label=label,
        segment_confidence=confidence,
        frame_features=frame_features,
        rf_chest_probability=rf_chest_probability,
    )
