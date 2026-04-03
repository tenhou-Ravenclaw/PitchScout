"""
train.py — VocalSet を用いた地声検出器（Hybrid 用）の学習

背景:
    VocalSet は chest/modal 系中心で、falsetto ラベルを十分に持たない。
    そのため本スクリプトは「胸声(chest)検出器」を学習し、
    裏声は推論時に WORLD の AP ルールで判定する。

出力:
    models/register_model.joblib
    - 胸声検出器モデル
    - しきい値や特徴名を含むメタデータ
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Iterable

import joblib
import librosa
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from analysis.feature_extractor import extract_segment_features

LABEL_CHEST = 1
LABEL_NON_CHEST = 0

MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODEL_DIR / "register_model.joblib"
FEATURE_CACHE_DIR = Path(__file__).resolve().parent / "training_data"
FEATURE_CACHE_PATH = FEATURE_CACHE_DIR / "world_dataset.npz"


def _collect_audio_files(dataset_root: Path) -> list[Path]:
    """データセット配下の音声ファイルを再帰収集する。"""
    exts = ("*.wav", "*.WAV", "*.flac", "*.FLAC", "*.mp3", "*.MP3", "*.m4a", "*.M4A")
    files: list[Path] = []
    for ext in exts:
        files.extend(dataset_root.rglob(ext))
    return sorted(set(files))


def _is_chest_like(file_path: Path) -> bool:
    """VocalSet の命名から胸声系テクニックを判定する。"""
    name = file_path.stem.lower()
    chest_keywords = ("chest", "modal", "belt", "forte", "straight", "vibrato")
    reject_keywords = ("falsetto", "head", "whistle", "vocal_fry", "spoken")

    if any(key in name for key in reject_keywords):
        return False

    return any(key in name for key in chest_keywords)


def _is_falsetto_like(file_path: Path) -> bool:
    """VocalSet の命名から裏声系テクニックを判定する。"""
    name = file_path.stem.lower()
    falsetto_keywords = ("falsetto", "head", "whistle")
    return any(key in name for key in falsetto_keywords)


def _load_manifest(manifest_path: Path) -> dict[str, int]:
    """
    CSV manifest を読み込む。

    期待フォーマット:
      relative_path,label
      singer/a.wav,chest
      singer/b.wav,falsetto
    """
    records: dict[str, int] = {}
    with manifest_path.open("r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            rel_path = (row.get("relative_path") or "").strip()
            label = (row.get("label") or "").strip().lower()
            if not rel_path:
                continue

            if label == "chest":
                records[rel_path] = LABEL_CHEST
            elif label in {"falsetto", "head", "whistle", "non_chest"}:
                records[rel_path] = LABEL_NON_CHEST
    return records


def _iter_labeled_files(
    dataset_root: Path,
    audio_files: Iterable[Path],
    manifest: dict[str, int] | None,
) -> Iterable[tuple[Path, int]]:
    """胸声検出学習に使う音声ファイルとラベルを列挙する。"""
    for file_path in audio_files:
        if manifest is not None:
            rel = str(file_path.relative_to(dataset_root)).replace("\\", "/")
            if rel not in manifest:
                continue
            yield file_path, manifest[rel]
            continue

        if _is_chest_like(file_path):
            yield file_path, LABEL_CHEST
        elif _is_falsetto_like(file_path):
            yield file_path, LABEL_NON_CHEST


def _build_synthetic_non_chest(
    chest_x: np.ndarray,
    feature_names: list[str],
    factor: float = 1.65,
) -> np.ndarray:
    """AP を強調した疑似 non-chest 特徴を作成する。"""
    x_neg = chest_x.copy()

    ap_idx = [i for i, name in enumerate(feature_names) if name.startswith("ap_")]
    voiced_ratio_idx = feature_names.index("voiced_ratio") if "voiced_ratio" in feature_names else None
    f0_std_idx = feature_names.index("f0_std") if "f0_std" in feature_names else None

    if ap_idx:
        x_neg[:, ap_idx] = np.clip(x_neg[:, ap_idx] * factor, 0.0, 1.0)

    if voiced_ratio_idx is not None:
        x_neg[:, voiced_ratio_idx] = np.clip(x_neg[:, voiced_ratio_idx] * 0.75, 0.0, 1.0)

    if f0_std_idx is not None:
        x_neg[:, f0_std_idx] = x_neg[:, f0_std_idx] * 1.2

    noise = np.random.normal(loc=0.0, scale=0.03, size=x_neg.shape).astype(np.float32)
    x_neg = (x_neg + noise).astype(np.float32)
    return x_neg


def build_dataset(
    dataset_root: Path,
    manifest_path: Path | None,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """VocalSet 音声から胸声検出用データセットを作成する。"""
    audio_files = _collect_audio_files(dataset_root)
    if not audio_files:
        raise FileNotFoundError(f"音声ファイルが見つかりません: {dataset_root}")

    manifest: dict[str, int] | None = None
    if manifest_path is not None:
        manifest = _load_manifest(manifest_path)
        if not manifest:
            raise ValueError(f"manifest が空、または不正です: {manifest_path}")

    chest_x_list: list[np.ndarray] = []
    non_chest_x_list: list[np.ndarray] = []
    names: list[str] = []

    for file_path, label in _iter_labeled_files(dataset_root, audio_files, manifest):
        try:
            y, sr = librosa.load(str(file_path), sr=None, mono=True)
            feat, names, _ = extract_segment_features(y=y, sr=sr)
            if label == LABEL_CHEST:
                chest_x_list.append(feat)
            else:
                non_chest_x_list.append(feat)
        except Exception as exc:
            print(f"[WARN] スキップ: {file_path} ({exc})")

    if not chest_x_list:
        raise ValueError("有効な学習サンプルが抽出できませんでした")

    chest_x = np.vstack(chest_x_list).astype(np.float32)

    if non_chest_x_list:
        non_chest_x = np.vstack(non_chest_x_list).astype(np.float32)
        print(f"[INFO] 実データの non_chest を使用: {len(non_chest_x)} samples")
    else:
        non_chest_x = _build_synthetic_non_chest(chest_x=chest_x, feature_names=names)
        print(f"[INFO] non_chest が不足しているため疑似データを生成: {len(non_chest_x)} samples")

    x = np.vstack([non_chest_x, chest_x]).astype(np.float32)
    y = np.array(
        [LABEL_NON_CHEST] * len(non_chest_x) + [LABEL_CHEST] * len(chest_x),
        dtype=np.int32,
    )

    return x, y, names


def build_model(random_state: int = 42) -> Pipeline:
    """RandomForest パイプラインを構築する。"""
    return Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "clf",
                RandomForestClassifier(
                    n_estimators=400,
                    max_depth=16,
                    min_samples_leaf=2,
                    class_weight="balanced",
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def evaluate_model(x: np.ndarray, y: np.ndarray, model: Pipeline) -> None:
    """交差検証と学習データ上の分類レポートを出力する。"""
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(model, x, y, cv=cv, scoring="f1_weighted", n_jobs=-1)

    print("=== 5-Fold CV ===")
    print(f"F1(weighted): {float(np.mean(scores)):.4f} ± {float(np.std(scores)):.4f}")
    print(f"scores: {scores}")

    model.fit(x, y)
    pred = model.predict(x)

    print("\n=== Train Report ===")
    print(classification_report(y, pred, target_names=["non_chest", "chest"]))
    print(confusion_matrix(y, pred))


def save_artifacts(x: np.ndarray, y: np.ndarray, model: Pipeline, feature_names: list[str]) -> None:
    """学習済みモデルと特徴キャッシュを保存する。"""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    FEATURE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    artifact: dict[str, object] = {
        "model": model,
        "feature_names": feature_names,
        "task": "chest_detector",
        "version": 1,
        "chest_label": LABEL_CHEST,
        "non_chest_label": LABEL_NON_CHEST,
        "chest_probability_threshold": 0.55,
    }

    joblib.dump(artifact, MODEL_PATH)
    np.savez(
        FEATURE_CACHE_PATH,
        features=x,
        labels=y,
        feature_names=np.array(feature_names, dtype=object),
    )

    print(f"[OK] model: {MODEL_PATH}")
    print(f"[OK] dataset cache: {FEATURE_CACHE_PATH}")


def parse_args() -> argparse.Namespace:
    """CLI 引数を解析する。"""
    parser = argparse.ArgumentParser(description="WORLD 特徴で胸声検出器（Hybrid 用）を学習")
    parser.add_argument(
        "--dataset-root",
        type=str,
        required=True,
        help="VocalSet ルートディレクトリ",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default=None,
        help="relative_path,label 形式の CSV。label は chest/falsetto/head/whistle/non_chest 対応",
    )
    return parser.parse_args()


def main() -> None:
    """学習処理のエントリーポイント。"""
    args = parse_args()

    dataset_root = Path(args.dataset_root).expanduser().resolve()
    if not dataset_root.exists():
        raise FileNotFoundError(f"dataset-root が存在しません: {dataset_root}")

    manifest_path = Path(args.manifest).expanduser().resolve() if args.manifest else None

    x, y, feature_names = build_dataset(dataset_root=dataset_root, manifest_path=manifest_path)

    n_chest = int(np.sum(y == LABEL_CHEST))
    n_non_chest = int(np.sum(y == LABEL_NON_CHEST))
    print("=== Dataset Summary ===")
    print("task: chest detector (hybrid)")
    print(f"chest: {n_chest}")
    print(f"non_chest(synthetic): {n_non_chest}")
    print(f"total: {len(y)}")
    print(f"feature_dim: {x.shape[1]}")

    if n_chest < 10:
        raise ValueError("chest サンプルが不足しています（最低10件必要）")

    model = build_model()
    evaluate_model(x=x, y=y, model=model)

    # evaluate_model 内で fit 済み。
    save_artifacts(x=x, y=y, model=model, feature_names=feature_names)


if __name__ == "__main__":
    main()
