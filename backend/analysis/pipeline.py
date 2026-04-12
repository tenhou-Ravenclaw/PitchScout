"""
pipeline.py — WORLD Vocoder + RandomForest 推論パイプライン

処理フロー:
  1) 音声読み込み
  2) WORLD 特徴抽出 (F0/SP/AP)
  3) AP 主導で地声/裏声をフレーム分離
  4) RandomForest によるセグメント分類
  5) FastAPI 互換レスポンス整形
"""

from __future__ import annotations

import os
from typing import Any

import numpy as np
import soundfile as sf

import joblib

from analysis.classifier import HybridClassifier
from analysis.feature_extractor import (
    FrameAcousticFeatures,
    WorldFeatures,
    extract_frame_acoustic_features,
    extract_segment_features,
)
from analysis.scoring import analyze_singing_ability
from config import FALSETTO_MIN_CONSECUTIVE, VOICE_MAX_HZ, VOICE_MIN_HZ
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
        # 旧フォーマット互換: 直接モデルだけが保存されているケース
        _MODEL_CACHE = loaded
        _MODEL_META_CACHE = {
            "task": "legacy",
            "chest_label": 0,
            "chest_probability_threshold": 0.5,
        }

    # Hybrid WORLD 特徴（20次元）との整合を事前検証する。
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


def _safe_note_list(f0: np.ndarray) -> list[float]:
    """人声音域に収まる周波数のみリスト化する。"""
    if f0.size == 0:
        return []
    mask = (f0 >= VOICE_MIN_HZ) & (f0 <= VOICE_MAX_HZ)
    return f0[mask].astype(float).tolist()


def _add_range(result: dict[str, Any], notes: list[float], prefix: str) -> None:
    """周波数リストを音階ラベル付きレンジ情報へ変換する。"""
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


def _true_runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """True 区間を [start, end) の連続ランとして返す。"""
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for idx, value in enumerate(mask.astype(bool)):
        if value and start is None:
            start = idx
        elif (not value) and start is not None:
            runs.append((start, idx))
            start = None
    if start is not None:
        runs.append((start, int(mask.size)))
    return runs


def _pick_extreme(
    world: WorldFeatures,
    mask: np.ndarray,
    mode: str,
    min_consecutive_frames: int,
) -> dict[str, Any] | None:
    """連続フレーム条件を満たす区間のみから最小/最大の極値を選ぶ。"""
    if world.time_axis_sec is None or len(world.time_axis_sec) != len(world.f0):
        return None

    valid_mask = mask & world.voiced_mask & (world.f0 >= VOICE_MIN_HZ) & (world.f0 <= VOICE_MAX_HZ)
    if int(np.sum(valid_mask)) == 0:
        return None

    runs = _true_runs(valid_mask)
    sustained_runs = [r for r in runs if (r[1] - r[0]) >= min_consecutive_frames]
    if not sustained_runs:
        return None

    candidate_mask = np.zeros_like(valid_mask, dtype=bool)
    for start, end in sustained_runs:
        candidate_mask[start:end] = True

    candidate_indices = np.where(candidate_mask)[0]
    if candidate_indices.size == 0:
        return None

    candidate_f0 = world.f0[candidate_indices]
    if mode == "min":
        pick_local_idx = int(np.argmin(candidate_f0))
    else:
        pick_local_idx = int(np.argmax(candidate_f0))

    peak_idx = int(candidate_indices[pick_local_idx])
    peak_hz = float(world.f0[peak_idx])
    peak_label, peak_note_hz = hz_to_label_and_hz(peak_hz)

    run_start = peak_idx
    run_end = peak_idx + 1
    for start, end in runs:
        if start <= peak_idx < end:
            run_start = start
            run_end = end
            break

    return {
        "sec": float(world.time_axis_sec[peak_idx]),
        "hz_raw": peak_hz,
        "label": peak_label,
        "hz_note": float(peak_note_hz),
        "frames": int(run_end - run_start),
        "sustained_candidate_frames": int(np.sum(candidate_mask)),
    }


def _write_extreme_to_result(result: dict[str, Any], prefix: str, extreme: dict[str, Any] | None) -> None:
    """極値デバッグ情報を result に格納する。"""
    if extreme is None:
        return
    result[f"debug_{prefix}_sec"] = float(extreme["sec"])
    result[f"debug_{prefix}_hz_raw"] = float(extreme["hz_raw"])
    result[f"debug_{prefix}_label"] = str(extreme["label"])
    result[f"debug_{prefix}_hz_note"] = float(extreme["hz_note"])
    result[f"debug_{prefix}_frames"] = int(extreme["frames"])
    result[f"debug_{prefix}_candidate_frames"] = int(extreme["sustained_candidate_frames"])


def _add_extreme_debug_info(
    result: dict[str, Any],
    world: WorldFeatures,
    chest_mask: np.ndarray,
    falsetto_mask: np.ndarray,
) -> None:
    """全体/地声/裏声の最低音・最高音デバッグ情報を付与する。"""
    min_frames = max(1, int(FALSETTO_MIN_CONSECUTIVE))

    overall_mask = chest_mask | falsetto_mask
    overall_min = _pick_extreme(world, overall_mask, "min", min_frames)
    overall_max = _pick_extreme(world, overall_mask, "max", min_frames)
    chest_min = _pick_extreme(world, chest_mask, "min", min_frames)
    chest_max = _pick_extreme(world, chest_mask, "max", min_frames)
    falsetto_min = _pick_extreme(world, falsetto_mask, "min", min_frames)
    falsetto_max = _pick_extreme(world, falsetto_mask, "max", min_frames)

    _write_extreme_to_result(result, "overall_min", overall_min)
    _write_extreme_to_result(result, "overall_max", overall_max)
    _write_extreme_to_result(result, "chest_min", chest_min)
    _write_extreme_to_result(result, "chest_max", chest_max)
    _write_extreme_to_result(result, "falsetto_min", falsetto_min)
    _write_extreme_to_result(result, "falsetto_max", falsetto_max)


def _predict_chest_confidence(features: np.ndarray) -> float:
    """学習済み RandomForest で胸声信頼度を推定する。"""
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


def _split_register_with_gates(
    world: WorldFeatures,
    frame_features: FrameAcousticFeatures,
    rf_chest_probability: float,
    no_falsetto: bool,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """フレーム単位ゲート判定から chest/falsetto マスクを生成する。"""
    voiced_mask = world.voiced_mask.copy()
    if no_falsetto:
        return voiced_mask, np.zeros_like(voiced_mask, dtype=bool), {"forced_no_falsetto": int(np.sum(voiced_mask))}

    classifier = HybridClassifier()
    labels = np.full(world.f0.shape, "unvoiced", dtype=object)
    reasons = np.full(world.f0.shape, "no_f0", dtype=object)

    for idx in np.where(voiced_mask)[0]:
        label, reason = classifier.classify_frame(
            f0=float(frame_features.f0[idx]),
            ap_mean=float(frame_features.ap_mean[idx]),
            hnr=float(frame_features.hnr[idx]),
            rf_chest_proba=rf_chest_probability,
        )
        labels[idx] = label
        reasons[idx] = reason

    chest_mask = voiced_mask & (labels == "chest")
    falsetto_mask = voiced_mask & (labels == "falsetto")

    reason_counts: dict[str, int] = {}
    for reason in reasons[voiced_mask]:
        key = str(reason)
        reason_counts[key] = reason_counts.get(key, 0) + 1

    return chest_mask, falsetto_mask, reason_counts


def _hybrid_segment_label(
    chest_mask: np.ndarray,
    falsetto_mask: np.ndarray,
    rf_chest_probability: float,
    no_falsetto: bool,
) -> tuple[str, float]:
    """フレーム分類結果からセグメントラベルを決定する。"""
    if no_falsetto:
        return "chest", rf_chest_probability

    voiced = max(int(np.sum(chest_mask) + np.sum(falsetto_mask)), 1)
    falsetto_ratio = float(np.sum(falsetto_mask)) / float(voiced)
    chest_ratio = 1.0 - falsetto_ratio

    if falsetto_ratio > chest_ratio:
        return "falsetto", falsetto_ratio
    return "chest", max(chest_ratio, rf_chest_probability)


def _build_result(
    world: WorldFeatures,
    chest_mask: np.ndarray,
    falsetto_mask: np.ndarray,
    segment_label: str,
    segment_confidence: float,
    gate_reason_counts: dict[str, int],
    frame_features: FrameAcousticFeatures,
    no_falsetto: bool,
) -> dict[str, Any]:
    """FastAPI 互換のレスポンスを生成する。"""
    result: dict[str, Any] = {
        "register_label": segment_label,
        "register_confidence": round(segment_confidence, 4),
        "debug_gate_reason_counts": gate_reason_counts,
    }

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
    _add_extreme_debug_info(result, world, chest_mask, falsetto_mask)

    _add_range(result, chest_notes, "chest")
    _add_range(result, falsetto_notes, "falsetto")

    total_frames = len(chest_notes) + len(falsetto_notes)
    chest_ratio = (len(chest_notes) / total_frames) * 100.0 if total_frames else 100.0
    falsetto_ratio = (len(falsetto_notes) / total_frames) * 100.0 if total_frames else 0.0

    result["chest_ratio"] = round(chest_ratio, 1)
    result["falsetto_ratio"] = round(falsetto_ratio, 1)
    result["chest_avg_hz"] = round(float(np.mean(chest_notes)), 1) if chest_notes else 0.0
    voiced_mask = world.voiced_mask
    if int(np.sum(voiced_mask)) > 0:
        result["debug_harmonic_score_mean"] = round(float(np.mean(frame_features.harmonic_score[voiced_mask])), 4)

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
        already_separated: 互換引数（ログ用途）。
        no_falsetto: True の場合は裏声分離を無効化。
    """
    del already_separated

    print("\n============================================================")
    print(f"[INFO] WORLD 解析開始: {wav_path}")
    print("============================================================")

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

    try:
        segment_features, feature_names, world = extract_segment_features(y=y, sr=sr)
        frame_features = extract_frame_acoustic_features(world)
        print(f"[DEBUG] 特徴次元: {len(segment_features)}")
        print(f"[DEBUG] 先頭特徴: {feature_names[:5]}")
    except Exception as exc:
        return {"error": f"WORLD 特徴抽出に失敗しました: {exc}"}

    try:
        chest_confidence = _predict_chest_confidence(segment_features)
        chest_mask, falsetto_mask, gate_reason_counts = _split_register_with_gates(
            world=world,
            frame_features=frame_features,
            rf_chest_probability=chest_confidence,
            no_falsetto=no_falsetto,
        )
        label, confidence = _hybrid_segment_label(
            chest_mask=chest_mask,
            falsetto_mask=falsetto_mask,
            rf_chest_probability=chest_confidence,
            no_falsetto=no_falsetto,
        )
    except Exception as exc:
        return {"error": f"分類器推論に失敗しました: {exc}"}

    print(
        "[INFO] Hybrid推論結果: "
        f"label={label}, chest_confidence={chest_confidence:.3f}, confidence={confidence:.3f}"
    )
    result = _build_result(
        world=world,
        chest_mask=chest_mask,
        falsetto_mask=falsetto_mask,
        segment_label=label,
        segment_confidence=confidence,
        gate_reason_counts=gate_reason_counts,
        frame_features=frame_features,
        no_falsetto=no_falsetto,
    )
    if "debug_overall_min_sec" in result and "debug_overall_max_sec" in result:
        print(
            "[DEBUG] 最低音/最高音: "
            f"{result.get('debug_overall_min_label')}({result.get('debug_overall_min_hz_raw', 0.0):.1f}Hz)@{result.get('debug_overall_min_sec', 0.0):.2f}s, "
            f"{result.get('debug_overall_max_label')}({result.get('debug_overall_max_hz_raw', 0.0):.1f}Hz)@{result.get('debug_overall_max_sec', 0.0):.2f}s"
        )
    if "debug_chest_min_sec" in result and "debug_chest_max_sec" in result:
        print(
            "[DEBUG] 地声極値: "
            f"最低={result.get('debug_chest_min_label')}({result.get('debug_chest_min_hz_raw', 0.0):.1f}Hz, "
            f"{result.get('debug_chest_min_frames', 0)}フレーム)@{result.get('debug_chest_min_sec', 0.0):.2f}s, "
            f"最高={result.get('debug_chest_max_label')}({result.get('debug_chest_max_hz_raw', 0.0):.1f}Hz, "
            f"{result.get('debug_chest_max_frames', 0)}フレーム)@{result.get('debug_chest_max_sec', 0.0):.2f}s"
        )
    else:
        print(f"[DEBUG] 地声極値: 連続{int(FALSETTO_MIN_CONSECUTIVE)}フレーム条件を満たす候補なし")
    if "debug_falsetto_min_sec" in result and "debug_falsetto_max_sec" in result:
        print(
            "[DEBUG] 裏声極値: "
            f"最低={result.get('debug_falsetto_min_label')}({result.get('debug_falsetto_min_hz_raw', 0.0):.1f}Hz, "
            f"{result.get('debug_falsetto_min_frames', 0)}フレーム)@{result.get('debug_falsetto_min_sec', 0.0):.2f}s, "
            f"最高={result.get('debug_falsetto_max_label')}({result.get('debug_falsetto_max_hz_raw', 0.0):.1f}Hz, "
            f"{result.get('debug_falsetto_max_frames', 0)}フレーム)@{result.get('debug_falsetto_max_sec', 0.0):.2f}s"
        )
    else:
        print(f"[DEBUG] 裏声極値: 連続{int(FALSETTO_MIN_CONSECUTIVE)}フレーム条件を満たす候補なし")
    return result
