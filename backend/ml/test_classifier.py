"""
test_classifier.py — 声区判定 ML モデルのテストスイート

実行方法:
    cd backend
    pytest ml/test_classifier.py -v                        # 全テスト
    pytest ml/test_classifier.py -v -k "TestFeature"       # 特徴量抽出のみ
    pytest ml/test_classifier.py -v -k "TestModel"         # モデル精度のみ
    pytest ml/test_classifier.py -v --tb=short             # 短いトレースバック

テスト構成:
    TestFeatureExtractor    : 特徴量抽出の単体テスト（合成音声で入出力を検証）
    TestRegisterClassifier  : ルールベース判定のテスト（ハードルール・ノイズゲート）
    TestModelAccuracy       : 学習済みモデルの精度テスト（dataset.npz からホールドアウト）
    TestDatasetIntegrity    : dataset.npz の整合性テスト
"""

import os
import sys
import tempfile

import numpy as np
import pytest
import soundfile as sf

# ml/ から実行時に backend/ を PATH に追加して analysis パッケージ等を import できるようにする
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from analysis.features import N_FEATURES, extract_features
from config import CREPE_NOISE_GATE, FALSETTO_HARD_MIN_HZ

# ============================================================
# テスト用合成音声ヘルパー
# ============================================================

def _make_sawtooth(freq_hz: float = 220.0, sr: int = 16000,
                   n_samples: int = 2048, n_harmonics: int = 8) -> np.ndarray:
    """
    豊富な倍音を持つのこぎり波を生成（地声的な信号）。

    のこぎり波は 1/n 振幅で倍音が並ぶため:
      - h1_h2 が小さい (H1 ≈ H2 の 2 倍)
      - hcount が多い
      - hnr が高い（完全に周期的）
    """
    t = np.arange(n_samples) / sr
    sig = np.zeros(n_samples, dtype=np.float32)
    for n in range(1, n_harmonics + 1):
        sig += (1.0 / n) * np.sin(2 * np.pi * freq_hz * n * t)
    peak = np.max(np.abs(sig))
    if peak > 0:
        sig = sig / peak * 0.8
    return sig


def _make_sine(freq_hz: float = 440.0, sr: int = 16000,
               n_samples: int = 2048) -> np.ndarray:
    """
    純音（正弦波）を生成（裏声的な信号）。

    純音は第2倍音以上が理論上ゼロなため:
      - h1_h2 が大きい (H2 は雑音レベル)
      - hcount が少ない
    """
    t = np.arange(n_samples) / sr
    return (0.8 * np.sin(2 * np.pi * freq_hz * t)).astype(np.float32)


# ============================================================
# 1. 特徴量抽出の単体テスト
# ============================================================

class TestFeatureExtractor:
    """extract_features() の入出力検証。合成音声を使い、CREPE 不要で高速に実行できる。"""

    def test_returns_correct_shape(self):
        """有効なフレームを与えると shape=(6,) の配列が返ること"""
        y = _make_sawtooth(220)
        result = extract_features(y, 16000, 220.0)
        assert result is not None, "有効なフレームなのに None が返った"
        assert result.shape == (N_FEATURES,), f"shape={result.shape} が (6,) でない"
        assert result.dtype == np.float32

    def test_f0_feature_matches_input(self):
        """特徴量[5] (f0) が引数で渡した f0 と一致すること"""
        y = _make_sawtooth(300)
        result = extract_features(y, 16000, 300.0)
        assert result is not None
        assert result[5] == pytest.approx(300.0), f"f0 特徴量 {result[5]} が 300.0 でない"

    def test_zero_f0_returns_none(self):
        """f0=0 は不正値なので None を返すこと"""
        y = _make_sine(440)
        assert extract_features(y, 16000, 0.0) is None

    def test_negative_f0_returns_none(self):
        """f0 < 0 は不正値なので None を返すこと"""
        y = _make_sine(440)
        assert extract_features(y, 16000, -100.0) is None

    def test_too_short_frame_returns_none(self):
        """512 サンプル未満のフレームは None を返すこと"""
        y = np.random.randn(400).astype(np.float32) * 0.1
        assert extract_features(y, 16000, 220.0) is None

    def test_all_features_finite(self):
        """全特徴量が NaN / Inf でないこと"""
        y = _make_sawtooth(220)
        result = extract_features(y, 16000, 220.0)
        if result is None:
            pytest.skip("特徴量抽出失敗（環境依存）")
        assert np.all(np.isfinite(result)), f"NaN/Inf が含まれる: {result}"

    def test_feature_values_in_physical_range(self):
        """各特徴量が物理的に妥当な範囲内であること"""
        y = _make_sawtooth(220)
        feat = extract_features(y, 16000, 220.0)
        if feat is None:
            pytest.skip("特徴量抽出失敗")
        h1_h2, hcount, slope, hnr, centroid_r, f0 = feat
        assert -20.0 <= h1_h2 <= 120.0,  f"h1_h2={h1_h2:.2f} が範囲外"
        assert 0 <= hcount <= 10,         f"hcount={hcount} が範囲外"
        assert -40.0 <= slope <= 15.0,    f"slope={slope:.2f} が範囲外"
        assert 0.0 <= hnr <= 1.0,         f"hnr={hnr:.4f} が範囲外"
        assert centroid_r > 0,            f"centroid_r={centroid_r:.2f} が 0 以下"

    def test_sawtooth_has_multiple_harmonics(self):
        """のこぎり波は倍音が多いため hcount >= 3 であること"""
        y = _make_sawtooth(220, n_harmonics=8)
        feat = extract_features(y, 16000, 220.0)
        if feat is None:
            pytest.skip("特徴量抽出失敗")
        hcount = feat[1]
        assert hcount >= 3, f"のこぎり波の hcount={hcount} が少なすぎる"

    def test_sine_has_large_h1_h2(self):
        """純音は H2 がほぼ 0 なので h1_h2 が正の大きい値になること"""
        y = _make_sine(440)
        feat = extract_features(y, 16000, 440.0)
        if feat is None:
            pytest.skip("特徴量抽出失敗")
        h1_h2 = feat[0]
        assert h1_h2 > 0.0, f"純音の h1_h2={h1_h2:.2f} が正でない"

    def test_different_f0_values_work(self):
        """様々な f0 値でクラッシュしないこと"""
        for f0 in [100.0, 200.0, 350.0, 500.0, 700.0]:
            y = _make_sawtooth(f0)
            result = extract_features(y, 16000, f0)
            # None でも OK（短すぎ等）、クラッシュしなければよい

    def test_silent_frame_returns_none_or_array(self):
        """無音フレームは None か h1 が極小値で None になること（クラッシュしない）"""
        y = np.zeros(2048, dtype=np.float32)
        # クラッシュしないことだけ確認
        result = extract_features(y, 16000, 220.0)
        assert result is None or isinstance(result, np.ndarray)


# ============================================================
# 2. ルールベース判定のテスト
# ============================================================

class TestRegisterClassifier:
    """
    classify_register() のハードルール部分を検証。
    ML モデルの有無に関係なく常に成立すべき不変条件をテストする。
    """

    def setup_method(self):
        from analysis.classifier import classify_register, new_register_stats
        self._classify = classify_register
        self._new_stats = new_register_stats

    def test_hard_min_hz_always_chest(self):
        """FALSETTO_HARD_MIN_HZ (270Hz) 以下は必ず 'chest' を返すこと"""
        y = _make_sawtooth(200)
        stats = self._new_stats()
        result = self._classify(y, 16000, 200.0, 200.0, False, 0.9, stats)
        assert result == "chest", \
            f"f0=200Hz (< {FALSETTO_HARD_MIN_HZ}Hz) なのに '{result}' が返った"

    def test_hard_min_hz_boundary(self):
        """FALSETTO_HARD_MIN_HZ ちょうどは chest を返すこと"""
        y = _make_sawtooth(FALSETTO_HARD_MIN_HZ)
        stats = self._new_stats()
        result = self._classify(y, 16000, FALSETTO_HARD_MIN_HZ, 250.0, False, 0.9, stats)
        assert result == "chest", \
            f"f0={FALSETTO_HARD_MIN_HZ}Hz (境界値) なのに '{result}' が返った"

    def test_noise_gate_returns_unknown(self):
        """CREPE 信頼度が CREPE_NOISE_GATE 未満なら 'unknown' を返すこと"""
        y = _make_sawtooth(400)
        stats = self._new_stats()
        low_conf = CREPE_NOISE_GATE - 0.01
        result = self._classify(y, 16000, 400.0, 300.0, False, low_conf, stats)
        assert result == "unknown", \
            f"低信頼度 ({low_conf:.2f}) なのに 'unknown' 以外 ('{result}') が返った"

    def test_return_value_is_valid(self):
        """戻り値は 'chest', 'falsetto', 'unknown' のいずれかであること"""
        y = _make_sawtooth(350)
        stats = self._new_stats()
        for f0 in [150.0, 280.0, 350.0, 500.0, 700.0]:
            conf = 0.9 if f0 >= FALSETTO_HARD_MIN_HZ else 0.5
            result = self._classify(y, 16000, f0, 300.0, False, conf, stats)
            assert result in ("chest", "falsetto", "unknown"), \
                f"f0={f0}: 不正な戻り値 '{result}'"

    def test_does_not_crash_on_short_frame(self):
        """512 サンプル未満のフレームでもクラッシュしないこと（unknown を返す）"""
        y = np.zeros(400, dtype=np.float32)
        stats = self._new_stats()
        result = self._classify(y, 16000, 400.0, 300.0, False, 0.8, stats)
        assert result in ("chest", "falsetto", "unknown")

    def test_already_separated_flag_accepted(self):
        """already_separated=True でもクラッシュしないこと"""
        y = _make_sawtooth(350)
        stats = self._new_stats()
        result = self._classify(y, 16000, 350.0, 300.0, True, 0.8, stats)
        assert result in ("chest", "falsetto", "unknown")


class TestGateFirstHybridRegression:
    """ゲート先行ハイブリッド設計の回帰テスト。"""

    def test_unvoiced_returns_unvoiced(self):
        """無声音フレームは unvoiced と判定されること。"""
        from analysis.classifier import HybridClassifier

        clf = HybridClassifier()
        label, reason = clf.classify_frame(
            f0=0.0,
            ap_mean=0.5,
            hnr=2.0,
            rf_chest_proba=0.5,
        )
        assert label == "unvoiced"
        assert reason == "no_f0"

    def test_low_f0_high_ap_forced_chest(self):
        """F0 がハード下限未満なら AP/HNR に関係なく chest を返すこと。"""
        from analysis.classifier import HybridClassifier

        clf = HybridClassifier()
        label, reason = clf.classify_frame(
            f0=FALSETTO_HARD_MIN_HZ - 5.0,
            ap_mean=0.95,
            hnr=-4.0,
            rf_chest_proba=0.1,
        )
        assert label == "chest"
        assert reason == "below_hard_min"

    def test_transition_boundary_no_label_bleed(self):
        """ひっくり返り相当の遷移で境界前後のラベルが崩れないこと。"""
        from analysis.classifier import HybridClassifier

        clf = HybridClassifier()
        f0s = [360.0, 380.0, 400.0, 430.0, 470.0, 530.0, 560.0]
        ap_vals = [0.20, 0.22, 0.25, 0.36, 0.38, 0.34, 0.33]
        hnr_vals = [9.5, 9.0, 8.8, 5.2, 4.8, 7.0, 6.8]

        labels: list[str] = []
        for f0, ap_mean, hnr in zip(f0s, ap_vals, hnr_vals):
            label, _ = clf.classify_frame(
                f0=f0,
                ap_mean=ap_mean,
                hnr=hnr,
                rf_chest_proba=0.45,
            )
            labels.append(label)

        assert labels[:3] == ["chest", "chest", "chest"]
        assert labels[3:] == ["falsetto", "falsetto", "falsetto", "falsetto"]

    def test_short_clip_no_crash(self, monkeypatch):
        """短尺音声(<1s)でもクラッシュせず結果辞書を返すこと。"""
        import analysis.pipeline as pipeline

        monkeypatch.setattr(pipeline, "_predict_chest_confidence", lambda _features: 0.7)

        sr = 16000
        duration_sec = 0.45
        t = np.arange(int(sr * duration_sec), dtype=np.float32) / float(sr)
        y = 0.4 * np.sin(2.0 * np.pi * 220.0 * t)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name

        try:
            sf.write(wav_path, y, sr)
            result = pipeline.analyze(wav_path=wav_path)
            assert isinstance(result, dict)
            assert "error" not in result
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)

    def test_normal_singing_like_split(self):
        """通常歌唱相当の値で chest/falsetto が分離されること。"""
        from analysis.classifier import HybridClassifier

        clf = HybridClassifier()
        # chest 相当
        chest_label, _ = clf.classify_frame(
            f0=410.0,
            ap_mean=0.22,
            hnr=9.0,
            rf_chest_proba=0.8,
        )
        # falsetto 相当
        falsetto_label, _ = clf.classify_frame(
            f0=560.0,
            ap_mean=0.35,
            hnr=6.5,
            rf_chest_proba=0.2,
        )

        assert chest_label == "chest"
        assert falsetto_label == "falsetto"

    def test_pure_chest_clip_has_no_falsetto_range(self, monkeypatch):
        """純粋な地声音源では裏声音域が結果に含まれないこと。"""
        import analysis.pipeline as pipeline

        monkeypatch.setattr(pipeline, "_predict_chest_confidence", lambda _features: 0.95)

        sr = 16000
        duration_sec = 1.2
        t = np.arange(int(sr * duration_sec), dtype=np.float32) / float(sr)
        y = 0.45 * np.sin(2.0 * np.pi * 220.0 * t)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name

        try:
            sf.write(wav_path, y, sr)
            result = pipeline.analyze(wav_path=wav_path)
            assert "error" not in result
            assert "falsetto_max_hz" not in result
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)


# ============================================================
# 3. 学習済みモデルの精度テスト
# ============================================================

_DATASET_PATH = os.path.join(os.path.dirname(__file__), "training_data", "dataset.npz")
_MODEL_PATH   = os.path.join(os.path.dirname(__file__), "models", "register_model.joblib")


@pytest.fixture(scope="module")
def dataset():
    """dataset.npz を読み込む（ないときはスキップ）"""
    if not os.path.exists(_DATASET_PATH):
        pytest.skip("dataset.npz が見つかりません。先に学習データを準備してください。")
    data = np.load(_DATASET_PATH)
    return data["features"], data["labels"]


@pytest.fixture(scope="module")
def trained_model():
    """学習済みモデルを読み込む（ないときはスキップ）"""
    if not os.path.exists(_MODEL_PATH):
        pytest.skip("register_model.joblib が見つかりません。先に train_classifier.py を実行してください。")
    import joblib
    return joblib.load(_MODEL_PATH)


class TestModelAccuracy:
    """
    学習済みモデルを dataset.npz のホールドアウトセット (20%) で評価する。
    精度・F1・クラスコラプス・地声見逃し率・CV スコアを検証する。
    """

    def test_model_file_exists(self):
        """モデルファイルが存在すること"""
        assert os.path.exists(_MODEL_PATH), \
            f"モデルが見つかりません: {_MODEL_PATH}\n  → python ml/train_classifier.py を実行してください。"

    def test_accuracy_above_threshold(self, dataset, trained_model):
        """テストセット精度 ≥ 85% であること"""
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score

        X, y = dataset
        _, X_test, _, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y,
        )
        preds = trained_model.predict(X_test)
        acc = accuracy_score(y_test, preds)
        print(f"\n  精度: {acc:.4f}  (テストサイズ={len(X_test)})")
        assert acc >= 0.85, f"精度 {acc:.4f} が閾値 0.85 を下回っています"

    def test_f1_above_threshold(self, dataset, trained_model):
        """加重 F1 スコア ≥ 0.85 であること（クラス不均衡に強い指標）"""
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import f1_score

        X, y = dataset
        _, X_test, _, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y,
        )
        preds = trained_model.predict(X_test)
        f1 = f1_score(y_test, preds, average="weighted")
        print(f"\n  F1 (weighted): {f1:.4f}")
        assert f1 >= 0.85, f"F1={f1:.4f} が閾値 0.85 を下回っています"

    def test_no_class_collapse(self, dataset, trained_model):
        """モデルが片方のクラスしか予測しない（コラプス）状態でないこと"""
        from sklearn.model_selection import train_test_split

        X, y = dataset
        _, X_test, _, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y,
        )
        preds = trained_model.predict(X_test)
        unique_preds = set(preds.tolist())
        assert len(unique_preds) >= 2, \
            f"クラスコラプス: モデルが {unique_preds} しか予測しない"

    def test_chest_false_negative_rate(self, dataset, trained_model):
        """
        地声(0)の見逃し率(FNR) ≤ 20% であること。
        地声を裏声と誤判定すると、ユーザーの音域が狭く表示されてしまう。
        """
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import confusion_matrix

        X, y = dataset
        _, X_test, _, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y,
        )
        preds = trained_model.predict(X_test)
        # 地声 (label=0) に対する混同行列で FNR を計算
        chest_true  = y_test == 0
        chest_pred  = preds == 0
        fn = int(np.sum(chest_true & ~chest_pred))  # 地声 → 裏声 誤判定
        tp = int(np.sum(chest_true & chest_pred))
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
        print(f"\n  地声 FNR: {fnr:.4f}  (FN={fn}, TP={tp})")
        assert fnr <= 0.20, f"地声の見逃し率 {fnr:.4f} が 20% を超えています"

    def test_falsetto_false_negative_rate(self, dataset, trained_model):
        """
        裏声(1)の見逃し率(FNR) ≤ 25% であること。
        裏声を地声と誤判定すると、裏声音域が表示されなくなる。
        """
        from sklearn.model_selection import train_test_split

        X, y = dataset
        _, X_test, _, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y,
        )
        preds = trained_model.predict(X_test)
        falsetto_true = y_test == 1
        falsetto_pred = preds == 1
        fn = int(np.sum(falsetto_true & ~falsetto_pred))
        tp = int(np.sum(falsetto_true & falsetto_pred))
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
        print(f"\n  裏声 FNR: {fnr:.4f}  (FN={fn}, TP={tp})")
        assert fnr <= 0.25, f"裏声の見逃し率 {fnr:.4f} が 25% を超えています"

    def test_cross_validation_score(self, dataset, trained_model):
        """
        5 分割 CV の加重 F1 ≥ 0.82 であること（過学習・汎化性能チェック）。
        大規模データは 50,000 フレームにサブサンプリングして高速化する。
        """
        from sklearn.model_selection import StratifiedKFold, cross_val_score

        X, y = dataset
        # 時間短縮のため 5 万フレームに絞る
        if len(X) > 50_000:
            rng = np.random.default_rng(42)
            idx = rng.choice(len(X), 50_000, replace=False)
            X, y = X[idx], y[idx]

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        scores = cross_val_score(
            trained_model, X, y, cv=cv, scoring="f1_weighted", n_jobs=-1,
        )
        mean_f1 = scores.mean()
        print(f"\n  CV F1: {[f'{s:.4f}' for s in scores]}  mean={mean_f1:.4f}")
        assert mean_f1 >= 0.82, \
            f"CV F1={mean_f1:.4f} が閾値 0.82 を下回っています（過学習の疑い）"


# ============================================================
# 4. データセット整合性テスト
# ============================================================

class TestDatasetIntegrity:
    """
    dataset.npz そのものの健全性を検証する。
    精度テストの前提条件となる基本的な検査。
    """

    @pytest.fixture(scope="class")
    def npz(self):
        if not os.path.exists(_DATASET_PATH):
            pytest.skip("dataset.npz が存在しません")
        return np.load(_DATASET_PATH)

    def test_has_required_keys(self, npz):
        """'features' と 'labels' キーが存在すること"""
        assert "features" in npz, "features キーがありません"
        assert "labels"   in npz, "labels キーがありません"

    def test_shapes_consistent(self, npz):
        """features と labels のサンプル数が一致すること"""
        X, y = npz["features"], npz["labels"]
        assert X.shape[0] == y.shape[0], \
            f"サンプル数不一致: features={X.shape[0]}, labels={y.shape[0]}"

    def test_feature_dimension(self, npz):
        """特徴量の次元が N_FEATURES (6) であること"""
        X = npz["features"]
        assert X.shape[1] == N_FEATURES, \
            f"特徴量次元 {X.shape[1]} が {N_FEATURES} でない"

    def test_has_both_classes(self, npz):
        """chest(0) と falsetto(1) の両クラスが存在すること"""
        y = npz["labels"]
        assert 0 in y, "chest (label=0) がデータセットに含まれていません"
        assert 1 in y, "falsetto (label=1) がデータセットに含まれていません"

    def test_minimum_frames_per_class(self, npz):
        """各クラスが最低 100 フレーム以上あること"""
        y = npz["labels"]
        n_chest    = int(np.sum(y == 0))
        n_falsetto = int(np.sum(y == 1))
        print(f"\n  chest={n_chest}, falsetto={n_falsetto}")
        assert n_chest    >= 100, f"chest フレーム数 {n_chest} が少なすぎます"
        assert n_falsetto >= 100, f"falsetto フレーム数 {n_falsetto} が少なすぎます"

    def test_no_nan_in_features(self, npz):
        """特徴量に NaN が含まれないこと"""
        X = npz["features"]
        n_nan = int(np.sum(np.isnan(X)))
        assert n_nan == 0, f"{n_nan} 個の NaN が特徴量に含まれています"

    def test_no_inf_in_features(self, npz):
        """特徴量に Inf が含まれないこと"""
        X = npz["features"]
        n_inf = int(np.sum(np.isinf(X)))
        assert n_inf == 0, f"{n_inf} 個の Inf が特徴量に含まれています"

    def test_class_imbalance_within_bounds(self, npz):
        """クラス比率が 3:1 以内であること（極端な不均衡チェック）"""
        y = npz["labels"]
        n_chest    = int(np.sum(y == 0))
        n_falsetto = int(np.sum(y == 1))
        ratio = max(n_chest, n_falsetto) / max(min(n_chest, n_falsetto), 1)
        print(f"\n  クラス比率 (多/少): {ratio:.2f}")
        assert ratio <= 3.0, \
            f"クラス比率 {ratio:.2f} が 3:1 を超えています。再サンプリングを推奨。"

    def test_feature_variance_nonzero(self, npz):
        """全特徴量の分散が 0 でないこと（定数特徴量の検出）"""
        X = npz["features"]
        variances = np.var(X, axis=0)
        zero_var_features = [i for i, v in enumerate(variances) if v == 0]
        assert len(zero_var_features) == 0, \
            f"特徴量 {zero_var_features} の分散が 0（定数値になっている）"
