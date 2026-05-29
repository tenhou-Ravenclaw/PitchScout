"""
train_classifier.py — 地声/裏声 ML分類器の学習

使い方:
  1. まずラベル付きデータを作成:
     python labeler.py add chest chest_voice.wav
     python labeler.py add falsetto falsetto_voice.wav

  2. 学習実行:
     python train_classifier.py

  3. モデルが models/register_model.joblib に保存される
     → register_classifier.py が自動的にロードして使用

オプション:
  --no-cv          交差検証をスキップ
  --model TYPE     モデル種別 (rf / mlp / both)  デフォルト: both
"""

import os
import sys
import argparse
import numpy as np

# ml/ から実行時に親ディレクトリ (backend/) の analysis パッケージを見つける
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.pipeline import Pipeline
import joblib

from analysis.features import FEATURE_NAMES

DATA_DIR = os.path.join(os.path.dirname(__file__), "training_data")
DATASET_PATH = os.path.join(DATA_DIR, "dataset.npz")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "register_model.joblib")


def load_dataset():
    if not os.path.exists(DATASET_PATH):
        print(f"[ERROR] データセットが見つかりません: {DATASET_PATH}")
        print("  先に labeler.py add で音声データを登録してください。")
        sys.exit(1)

    data = np.load(DATASET_PATH)
    X, y = data["features"], data["labels"]

    n_chest = int(np.sum(y == 0))
    n_falsetto = int(np.sum(y == 1))
    print(f"=== データセット ===")
    print(f"  地声:   {n_chest} フレーム")
    print(f"  裏声:   {n_falsetto} フレーム")
    print(f"  合計:   {len(y)} フレーム")

    if n_chest < 50 or n_falsetto < 50:
        print(f"\n[WARN] データが少ないです（各クラス最低50フレーム推奨）")
        print(f"  地声の音声と裏声の音声をもっと追加してください。")
        if n_chest < 10 or n_falsetto < 10:
            print(f"[ERROR] 最低10フレーム/クラスが必要です")
            sys.exit(1)

    return X, y


def build_models():
    """学習候補モデルを返す"""
    return {
        "RandomForest": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                min_samples_leaf=5,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )),
        ]),
        "MLP": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", MLPClassifier(
                hidden_layer_sizes=(64, 32),
                activation="relu",
                max_iter=500,
                early_stopping=True,
                validation_fraction=0.15,
                random_state=42,
            )),
        ]),
    }


def cross_validate(X, y, models):
    """5-fold交差検証で各モデルを評価"""
    print(f"\n=== 5-Fold 交差検証 ===")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    results = {}

    for name, pipeline in models.items():
        scores = cross_val_score(pipeline, X, y, cv=cv, scoring="f1_weighted", n_jobs=-1)
        mean_score = float(np.mean(scores))
        std_score = float(np.std(scores))
        results[name] = mean_score
        print(f"  {name:15s}: F1={mean_score:.4f} ±{std_score:.4f}  {scores}")

    return results


def train_and_save(X, y, model_name, pipeline):
    """全データで学習してモデルを保存"""
    print(f"\n=== {model_name} を全データで学習中... ===")
    pipeline.fit(X, y)

    # 学習データでの性能（参考値）
    y_pred = pipeline.predict(X)
    labels = ["chest", "falsetto"]
    print(f"\n学習データでの性能:")
    print(classification_report(y, y_pred, target_names=labels))
    print("混同行列:")
    cm = confusion_matrix(y, y_pred)
    print(f"           予測: chest  falsetto")
    print(f"  実際 chest:   {cm[0, 0]:5d}   {cm[0, 1]:5d}")
    print(f"  実際 falsetto:{cm[1, 0]:5d}   {cm[1, 1]:5d}")

    # 特徴量の重要度（RandomForestの場合）
    clf = pipeline.named_steps.get("clf")
    if hasattr(clf, "feature_importances_"):
        print(f"\n特徴量の重要度:")
        importances = clf.feature_importances_
        for name, imp in sorted(zip(FEATURE_NAMES, importances), key=lambda x: -x[1]):
            bar = "█" * int(imp * 50)
            print(f"  {name:12s}: {imp:.4f} {bar}")

    # 保存
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    print(f"\n[OK] モデル保存: {MODEL_PATH}")
    print(f"     register_classifier.py がこのモデルを自動的にロードします。")


def main():
    parser = argparse.ArgumentParser(description="地声/裏声分類器の学習")
    parser.add_argument("--no-cv", action="store_true", help="交差検証をスキップ")
    parser.add_argument("--model", choices=["rf", "mlp", "both"], default="both",
                        help="使用するモデル種別")
    args = parser.parse_args()

    X, y = load_dataset()
    all_models = build_models()

    # モデル選択
    if args.model == "rf":
        models = {"RandomForest": all_models["RandomForest"]}
    elif args.model == "mlp":
        models = {"MLP": all_models["MLP"]}
    else:
        models = all_models

    # 交差検証
    if not args.no_cv and len(y) >= 20:
        cv_results = cross_validate(X, y, models)
        best_name = max(cv_results, key=cv_results.get)
        print(f"\n→ 最良モデル: {best_name} (F1={cv_results[best_name]:.4f})")
    else:
        if args.no_cv:
            print("[INFO] 交差検証スキップ")
        else:
            print("[INFO] データが少ないため交差検証スキップ")
        # データが少ない場合はRandomForestを選択（過学習しにくい）
        best_name = "RandomForest" if "RandomForest" in models else list(models.keys())[0]

    # 全データで学習＆保存
    train_and_save(X, y, best_name, models[best_name])


if __name__ == "__main__":
    main()