"""
classifier.py  —  地声 / 裏声 判定

"""

import os
import time
from dataclasses import dataclass
import numpy as np
import librosa

from config import (
    FALSETTO_HARD_MIN_HZ,
    ML_CONF_THRESHOLD_LOW_F0, ML_CONF_THRESHOLD_HIGH,
    ML_CONF_THRESHOLD_NOISY, ML_CONF_CHEST_HIGH_F0,
    ML_CHEST_ASSIST_MIN_HZ, ML_CHEST_ASSIST_MAX_HZ, ML_CHEST_ASSIST_MIN_CREPE_CONF,
    CREPE_NOISE_GATE,
    REGISTER_LOG_LEVEL, REGISTER_LOG_INTERVAL,
    FFT_SPECTRUM_SIZE,
)

# ============================================================
# MLモデルのロード（ホットリロード対応）
# ============================================================
_ML_MODEL = None
_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ml", "models", "register_model.joblib")
_MODEL_MTIME = 0.0       # モデルファイルの更新日時を記録
_ML_STATUS_LOGGED = False  # MLモデルの初回状態ログ出力済みフラグ
_last_check_time: float = 0.0   # 最終ディスクチェック時刻（time.monotonic）
_CHECK_INTERVAL: float = 30.0   # モデル更新チェックの最小間隔（秒）
# フレームごとに os.path.exists / os.path.getmtime を呼ぶとI/O回数が多いため、
# モデルがロード済みの場合は _CHECK_INTERVAL 秒間チェックをスキップする。

@dataclass
class RegisterStats:
    log_counter: int = 0
    ml_success: int = 0
    ml_fallback: int = 0
    rule_only: int = 0
    chest: int = 0
    falsetto: int = 0


def new_register_stats() -> "RegisterStats":
    return RegisterStats()


def _load_model_if_needed():
    """モデルファイルが更新されていたら再ロード（学習後にサーバー再起動不要）"""
    global _ML_MODEL, _MODEL_MTIME, _last_check_time

    # 時間ベーススロットリング: モデルがロード済みで前回チェックから _CHECK_INTERVAL 秒未満なら
    # os.path.exists / os.path.getmtime の syscall をスキップする。
    # フレームごとに呼ばれるため数千回/解析ファイルになる可能性があり、I/O負荷を抑える。
    now = time.monotonic()
    if _ML_MODEL is not None and (now - _last_check_time) < _CHECK_INTERVAL:
        return

    _last_check_time = now

    if not os.path.exists(_MODEL_PATH):
        if _ML_MODEL is not None:
            _ML_MODEL = None
            _MODEL_MTIME = 0.0
        return

    current_mtime = os.path.getmtime(_MODEL_PATH)
    if current_mtime == _MODEL_MTIME and _ML_MODEL is not None:
        return  # 変更なし、キャッシュ済みモデルを使用

    try:
        import joblib
        _ML_MODEL = joblib.load(_MODEL_PATH)
        _MODEL_MTIME = current_mtime
        print(f"[INFO] MLモデルをロードしました: {_MODEL_PATH}")
    except Exception as e:
        print(f"[ERROR] MLモデルのロードに失敗しました ({_MODEL_PATH}): {e}")
        _ML_MODEL = None


# 起動時に1回チェック
_load_model_if_needed()


def _should_log_verbose(stats: "RegisterStats") -> bool:
    """詳細ログを出力すべきかを判定するヘルパー。
    繰り返し使われる条件式を 1 箇所に集約する。"""
    return REGISTER_LOG_LEVEL >= 3 or (
        REGISTER_LOG_LEVEL == 2 and stats.log_counter % REGISTER_LOG_INTERVAL == 0
    )


# ============================================================
# 共通特徴量抽出（analysis/features.py を使用）
# ============================================================
try:
    from analysis.features import extract_features, get_peak_db, compute_hnr
except ImportError:
    extract_features = None
    get_peak_db = None
    compute_hnr = None


# ============================================================
# ML推論
# ============================================================
def _classify_ml(y: np.ndarray, sr: int, f0: float,
                  stats: RegisterStats,
                  crepe_conf: float = 1.0) -> str | None:
    """MLモデルで判定。モデルがないか特徴抽出に失敗したら None を返す"""
    _load_model_if_needed()  # モデル更新チェック（mtime比較のみ、軽量）

    if _ML_MODEL is None or extract_features is None:
        return None

    feat = extract_features(y, sr, f0)
    if feat is None:
        return None

    try:
        X = feat.reshape(1, -1)
        proba = _ML_MODEL.predict_proba(X)[0]
        pred = int(np.argmax(proba))
        label = "chest" if pred == 0 else "falsetto"
        confidence = float(proba[pred])

        # 遷移帯域（<500Hz）では地声/裏声の音響特徴が類似するため高い信頼度を要求
        if f0 < 500:
            threshold = ML_CONF_THRESHOLD_LOW_F0
        elif crepe_conf < 0.55:
            # CREPE信頼度低 + 高f0 → ノイズの可能性高い。ML確信を強く要求
            threshold = ML_CONF_THRESHOLD_NOISY
        else:
            threshold = ML_CONF_THRESHOLD_HIGH

        # 全音域で「地声」判定する場合は追加の信頼度要求
        # MLトレーニングデータは約95%が地声サンプルに偏っているため、
        # f0に関わらず地声判定には高い信頼度（90%）を要求する。
        # 裏声判定は通常閾値のままにし、高音の裏声検出を阻害しない。
        if label == "chest":
            threshold = max(threshold, ML_CONF_CHEST_HIGH_F0)

        if confidence < threshold:
            stats.ml_fallback += 1
            if _should_log_verbose(stats):
                print(f"[REGISTER/ML→RULE] f0={f0:.0f}Hz ML={label}({confidence:.3f}) < thresh={threshold:.2f} ")
            return None

        stats.ml_success += 1
        if label == "chest":
            stats.chest += 1
        else:
            stats.falsetto += 1
        if _should_log_verbose(stats):
            print(f"[REGISTER/ML] f0={f0:.0f}Hz label={label} conf={confidence:.3f} thresh={threshold:.2f} crepe={crepe_conf:.2f}")
        return label
    except Exception as e:
        print(f"[WARN] ML推論失敗: {e}")
        return None


def _classify_rules(y: np.ndarray, sr: int, f0: float, median_freq: float,
                    stats: RegisterStats,
                    crepe_conf: float = 1.0) -> str:
    """基礎的な音楽ロジックで地声/裏声を判定する。

    複雑な重み付けを避け、以下の原則で判定する:
    1. 音高帯域（低音=地声寄り、高音=裏声寄り）
    2. 基本スペクトル特徴（H1-H2、倍音本数、HNR、重心比）
    3. 遷移帯域では特徴シグナルの多数決
    """
    # FFT（config.FFT_SPECTRUM_SIZE を使用）
    n_fft    = FFT_SPECTRUM_SIZE
    win      = np.hanning(len(y))
    y_pad    = np.zeros(n_fft)
    y_pad[:len(y)] = y * win
    fft      = np.abs(np.fft.rfft(y_pad))
    freqs    = np.fft.rfftfreq(n_fft, 1.0 / sr)
    noise_db = 20.0 * np.log10(float(np.percentile(fft, 5)) + 1e-12)

    H  = [get_peak_db(fft, freqs, f0 * n, sr) for n in range(1, 11)]
    h1 = H[0]

    if h1 <= -60:
        return "unknown"

    h1_h2 = h1 - H[1]

    if h1_h2 < -20.0:
        return "unknown"

    hcount = sum(1 for db in H[:10] if db > noise_db + 8.0)
    hnr = compute_hnr(y, sr, f0)
    centroid = float(librosa.feature.spectral_centroid(y=y, sr=sr)[0, 0])
    cr = centroid / f0

    slope_pts = [(i + 1, H[i]) for i in range(8) if H[i] > noise_db + 8.0]
    if len(slope_pts) >= 3:
        xs = np.array([p[0] for p in slope_pts], dtype=float)
        ys = np.array([p[1] for p in slope_pts], dtype=float)
        slope = float(np.polyfit(xs, ys, 1)[0])
    else:
        slope = None

    # 低音域は地声を優先。複数の強い裏声根拠が揃う場合のみ裏声にする。
    if f0 < 300:
        strong_falsetto = (h1_h2 >= 8.0 and hcount <= 2 and hnr < 0.45)
        result = "falsetto" if strong_falsetto else "chest"
    # 高音域は裏声を優先。地声の根拠が強い場合のみ地声に戻す。
    elif f0 >= 520:
        strong_chest = (h1_h2 <= 0.5 and hcount >= 7 and hnr > 0.72 and cr > 6.5)
        result = "chest" if strong_chest else "falsetto"
    else:
        # 遷移帯域(300-520Hz): 基本特徴の多数決
        falsetto_signals = 0
        chest_signals = 0

        if h1_h2 >= 5.0:
            falsetto_signals += 1
        elif h1_h2 <= 1.0:
            chest_signals += 1

        if hcount <= 3:
            falsetto_signals += 1
        elif hcount >= 7:
            chest_signals += 1

        if hnr < 0.50:
            falsetto_signals += 1
        elif hnr > 0.70:
            chest_signals += 1

        if cr < 3.5:
            falsetto_signals += 1
        elif cr > 6.5:
            chest_signals += 1

        if slope is not None:
            if slope <= -8.0:
                falsetto_signals += 1
            elif slope >= -5.0:
                chest_signals += 1

        if crepe_conf < 0.55:
            chest_signals += 1

        if falsetto_signals > chest_signals:
            result = "falsetto"
        elif chest_signals > falsetto_signals:
            result = "chest"
        else:
            result = "falsetto" if f0 >= 420 else "chest"

    slope_str = f"{slope:.1f}" if slope is not None else "N/A"
    stats.rule_only += 1
    if result == "chest":
        stats.chest += 1
    else:
        stats.falsetto += 1
    if _should_log_verbose(stats):
        print(
            f"[REGISTER/RULE] f0={f0:.0f}Hz "
            f"H1-H2={h1_h2:.1f} hcount={hcount} "
            f"slope={slope_str} "
            f"HNR={hnr:.2f} cr={cr:.2f} "
            f"→ {result}"
        )
    return result


# ============================================================
# メインAPI（analysis/pipeline.py から呼ばれる）
# ============================================================
def classify_register(y: np.ndarray, sr: int, f0: float, median_freq: float = 0,
                      already_separated: bool = False,
                      crepe_conf: float = 1.0,
                      stats: RegisterStats | None = None) -> str:
    """
    地声/裏声を判定する。

    1. crepe_conf < CREPE_NOISE_GATE → unknown（ノイズゲート）
    2. f0 < FALSETTO_HARD_MIN_HZ → 地声確定
    """
    global _ML_STATUS_LOGGED

    # 初回のみMLモデル状態をログ出力
    if not _ML_STATUS_LOGGED:
        _load_model_if_needed()
        if _ML_MODEL is not None and extract_features is not None:
            print(f"[INFO] MLモデル使用中: {_MODEL_PATH}")
        else:
            if not os.path.exists(_MODEL_PATH):
                print(f"[WARN] MLモデルファイルが見つかりません: {_MODEL_PATH} → ルールベース判定にフォールバック")
            else:
                print(f"[WARN] MLモデルのロードに失敗しました: {_MODEL_PATH} → ルールベース判定にフォールバック")
        _ML_STATUS_LOGGED = True

    if f0 <= 0 or len(y) < 512:
        return "unknown"

    # CREPE信頼度ノイズゲート: ピッチ推定自体が不確かなフレームは判定しない
    if crepe_conf < CREPE_NOISE_GATE:
        return "unknown"

    if f0 < FALSETTO_HARD_MIN_HZ:
        return "chest"

    # ML判定は地声補助が必要な帯域だけに限定する。
    # 地声比率が高い学習データを活かしつつ、全フレーム推論の計算負荷を抑える。
    should_try_ml = (
        ML_CHEST_ASSIST_MIN_HZ <= f0 <= ML_CHEST_ASSIST_MAX_HZ
        and crepe_conf >= ML_CHEST_ASSIST_MIN_CREPE_CONF
    )

    local_stats = stats or RegisterStats()
    if should_try_ml:
        ml_result = _classify_ml(y, sr, f0, local_stats, crepe_conf=crepe_conf)
        if ml_result == "chest":
            local_stats.log_counter += 1
            return ml_result


    local_stats.log_counter += 1
    return _classify_rules(y, sr, f0, median_freq, local_stats, crepe_conf=crepe_conf)


# ============================================================
# ログ制御とサマリー
# ============================================================
def print_register_summary(stats: RegisterStats):
    """レジスター判定のサマリーを出力"""
    if REGISTER_LOG_LEVEL == 0:
        return

    total = stats.chest + stats.falsetto
    if total == 0:
        return

    print(f"\n[REGISTER SUMMARY] 合計判定数: {total}フレーム")
    print(f"  ├─ 地声: {stats.chest}フレーム ({stats.chest/total*100:.1f}%)")
    print(f"  └─ 裏声: {stats.falsetto}フレーム ({stats.falsetto/total*100:.1f}%)")

    if _ML_MODEL is not None:
        print(f"  判定方式:")
        print(f"    ├─ ML判定成功: {stats.ml_success}フレーム")
        print(f"    ├─ ML→ルール: {stats.ml_fallback}フレーム")
        print(f"    └─ ルールのみ: {stats.rule_only}フレーム")
