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

import joblib
import numpy as np
import soundfile as sf

from analysis.feature_extractor import WorldFeatures, extract_segment_features, split_register_by_aperiodicity
from analysis.scoring import analyze_singing_ability
from config import VOICE_MAX_HZ, VOICE_MIN_HZ
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


def _add_extreme_debug_info(result: dict[str, Any], world: WorldFeatures) -> None:
    """最低音・最高音の時刻とHzをデバッグ用に結果へ埋め込む。"""
    if world.time_axis_sec is None:
        return

    if len(world.time_axis_sec) != len(world.f0):
        return

    valid_mask = world.voiced_mask & (world.f0 >= VOICE_MIN_HZ) & (world.f0 <= VOICE_MAX_HZ)
    if int(np.sum(valid_mask)) == 0:
        return

    valid_indices = np.where(valid_mask)[0]
    valid_f0 = world.f0[valid_indices]

    min_idx_local = int(np.argmin(valid_f0))
    max_idx_local = int(np.argmax(valid_f0))
    min_idx = int(valid_indices[min_idx_local])
    max_idx = int(valid_indices[max_idx_local])

    min_hz = float(world.f0[min_idx])
    max_hz = float(world.f0[max_idx])
    min_label, min_note_hz = hz_to_label_and_hz(min_hz)
    max_label, max_note_hz = hz_to_label_and_hz(max_hz)

    result["debug_overall_min_sec"] = float(world.time_axis_sec[min_idx])
    result["debug_overall_max_sec"] = float(world.time_axis_sec[max_idx])
    result["debug_overall_min_hz_raw"] = min_hz
    result["debug_overall_max_hz_raw"] = max_hz
    result["debug_overall_min_label"] = min_label
    result["debug_overall_max_label"] = max_label
    result["debug_overall_min_hz_note"] = float(min_note_hz)
    result["debug_overall_max_hz_note"] = float(max_note_hz)


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


def _hybrid_segment_label(world: WorldFeatures, chest_confidence: float, no_falsetto: bool) -> tuple[str, float]:
    """ML(胸声) + ルール(AP裏声) でセグメントラベルを決定する。"""
    _, meta = _load_model()
    chest_threshold = float(meta["chest_probability_threshold"])

    if no_falsetto:
        return "chest", chest_confidence

    _, falsetto_mask = split_register_by_aperiodicity(world)
    voiced = np.maximum(int(np.sum(world.voiced_mask)), 1)
    falsetto_ratio = float(np.sum(falsetto_mask)) / voiced

    # AP規則優先: 裏声フレームが一定割合を超え、かつ胸声信頼度が低い場合は裏声。
    if falsetto_ratio >= 0.18 and chest_confidence < chest_threshold:
        return "falsetto", max(1.0 - chest_confidence, falsetto_ratio)

    return "chest", chest_confidence


def _build_result(
    world: WorldFeatures,
    segment_label: str,
    segment_confidence: float,
    no_falsetto: bool,
) -> dict[str, Any]:
    """FastAPI 互換のレスポンスを生成する。"""
    result: dict[str, Any] = {
        "register_label": segment_label,
        "register_confidence": round(segment_confidence, 4),
    }

    if no_falsetto:
        chest_mask = world.voiced_mask
        falsetto_mask = np.zeros_like(world.voiced_mask, dtype=bool)
    else:
        chest_mask, falsetto_mask = split_register_by_aperiodicity(world)

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
    _add_extreme_debug_info(result, world)

    _add_range(result, chest_notes, "chest")
    _add_range(result, falsetto_notes, "falsetto")

    total_frames = len(chest_notes) + len(falsetto_notes)
    chest_ratio = (len(chest_notes) / total_frames) * 100.0 if total_frames else 100.0
    falsetto_ratio = (len(falsetto_notes) / total_frames) * 100.0 if total_frames else 0.0

    result["chest_ratio"] = round(chest_ratio, 1)
    result["falsetto_ratio"] = round(falsetto_ratio, 1)
    result["chest_avg_hz"] = round(float(np.mean(chest_notes)), 1) if chest_notes else 0.0

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
        print(f"[DEBUG] 特徴次元: {len(segment_features)}")
        print(f"[DEBUG] 先頭特徴: {feature_names[:5]}")
    except Exception as exc:
        return {"error": f"WORLD 特徴抽出に失敗しました: {exc}"}

    try:
        chest_confidence = _predict_chest_confidence(segment_features)
        label, confidence = _hybrid_segment_label(
            world=world,
            chest_confidence=chest_confidence,
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
        segment_label=label,
        segment_confidence=confidence,
        no_falsetto=no_falsetto,
    )
    if "debug_overall_min_sec" in result and "debug_overall_max_sec" in result:
        print(
            "[DEBUG] 最低音/最高音: "
            f"{result.get('debug_overall_min_label')}({result.get('debug_overall_min_hz_raw', 0.0):.1f}Hz)@{result.get('debug_overall_min_sec', 0.0):.2f}s, "
            f"{result.get('debug_overall_max_label')}({result.get('debug_overall_max_hz_raw', 0.0):.1f}Hz)@{result.get('debug_overall_max_sec', 0.0):.2f}s"
        )
    return result
