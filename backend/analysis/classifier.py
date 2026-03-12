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
    CREPE_NOISE_GATE,
    FALSETTO_RATIO_HIGH, FALSETTO_RATIO_MID, FALSETTO_RATIO_DEFAULT,
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

    # 地声即決（低音域のみ: f0>400ではdemucsによるH1-H2変質があるためスコア判定へ回す）
    if h1_h2 < -2.0 and f0 <= 400:
        stats.rule_only += 1
        stats.chest += 1
        if _should_log_verbose(stats):
            print(f"[REGISTER/RULE] f0={f0:.0f}Hz H1-H2={h1_h2:.1f}dB → 地声確定(即決)")
        return "chest"

    # スコア判定
    chest_score    = 0.0
    falsetto_score = 0.0

    # CREPE信頼度ペナルティ: 低信頼度フレームはノイズの可能性が高く、
    # ノイズは裏声に偏りがち（低HNR、少ない倍音）なので地声方向に補正
    if crepe_conf < 0.55:
        chest_score += 1.5

    # H1-H2
    if h1_h2 >= 7:
        falsetto_score += 5.0
    elif h1_h2 >= 5:
        falsetto_score += 3.0
    elif h1_h2 >= 3:
        falsetto_score += 1.0
    elif h1_h2 <= 0:
        chest_score += 4.0
    elif h1_h2 <= 2:
        chest_score += 2.0

    # hcount
    # ★ 倍音数が少ない(hcount<=2)は裏声の特徴だが、アーティファクト（残留楽器）も
    # 倍音が少ない場合があるため、旧+6.0から+4.0に引き下げてアーティファクトを抑制。
    # ★ 高音域(f0>400Hz)では Demucs 分離後に hcount が過剰になる（最大10になりやすい）。
    # hcount≥8 の地声ボーナス(+6.0)が f0 バイアスを圧倒して裏声が地声に引き込まれるため
    # f0 に応じて減衰係数を掛ける。実音声の地声判断は他の特徴量に任せる。
    hcount = sum(1 for db in H[:10] if db > noise_db + 8.0)
    hcount_chest_mult = 0.35 if f0 > 500 else (0.60 if f0 > 400 else 1.0)
    if hcount <= 1:
        falsetto_score += 5.0
    elif hcount <= 2:
        falsetto_score += 4.0
    elif hcount <= 4:
        falsetto_score += 2.0
    elif hcount >= 8:
        chest_score += 6.0 * hcount_chest_mult
    elif hcount >= 6:
        chest_score += 3.0 * hcount_chest_mult

    # slope
    slope_pts = [(i + 1, H[i]) for i in range(8) if H[i] > noise_db + 8.0]
    if len(slope_pts) >= 3:
        xs    = np.array([p[0] for p in slope_pts], dtype=float)
        ys    = np.array([p[1] for p in slope_pts], dtype=float)
        slope = float(np.polyfit(xs, ys, 1)[0])
        if slope < -10:
            falsetto_score += 3.0
        elif slope < -7:
            falsetto_score += 1.5
        elif slope > -4:
            chest_score += 3.0
        elif slope > -6:
            chest_score += 1.5
    else:
        slope = None

    # HNR
    hnr = compute_hnr(y, sr, f0)
    if hnr < 0.35:
        falsetto_score += 4.0
    elif hnr < 0.50:
        falsetto_score += 2.0
    elif hnr > 0.80:
        chest_score += 3.0
    elif hnr > 0.65:
        chest_score += 1.5

    # centroid / f0
    centroid = float(librosa.feature.spectral_centroid(y=y, sr=sr)[0, 0])
    cr = centroid / f0
    if cr < 2.5:
        falsetto_score += 3.0
    elif cr < 4.0:
        falsetto_score += 1.5
    elif cr > 9.0:
        chest_score += 3.0
    elif cr > 6.5:
        chest_score += 1.5

    # f0補正: 高音域では強い裏声バイアスを適用
    # Demucs分離後の音源は倍音構造が変質しやすく hcount=10 が頻発するが、
    # 上の hcount_chest_mult 減衰と組み合わせることで正しい裏声判定を確保する。
    # hcount≥8(最大+6.0*0.35=+2.1)に対して、f0 バイアスで十分な裏声スコアを与える。
    if f0 > 600:
        falsetto_score += 8.0
    elif f0 > 500:
        falsetto_score += 6.0
    elif f0 > 400:
        falsetto_score += 4.0
    elif f0 <= 400 and f0 >= 350:
        # 遷移帯域上部（350-400Hz）: 裏声も十分あり得る音域のため弱い裏声バイアスを付与。
        # 旧コードではこの帯域にバイアスなし + FALSETTO_RATIO_DEFAULT=0.58 の組み合わせで
        # hcount≥8 など地声特徴1つで裏声が負けていた。
        falsetto_score += 1.5
    elif f0 < 220:
        chest_score += 3.0
    elif f0 < 295:
        chest_score += 1.5
    elif f0 < 350:
        chest_score += 0.5      # 下位遷移帯域: 地声寄り

    # 判定
    total = chest_score + falsetto_score
    if total < 1e-6:
        return "chest"

    falsetto_ratio = falsetto_score / total
    # 高音域では裏声判定の閾値を下げる
    # demucs分離後はhcount(倍音数)やslope(減衰)が常に地声寄りになるため、
    # 音響特徴だけでは裏声を検出しづらい。f0が高いこと自体が裏声の強い証拠。
    if f0 > 500:
        ratio_threshold = FALSETTO_RATIO_HIGH
    elif f0 > 400:
        ratio_threshold = FALSETTO_RATIO_MID
    else:
        ratio_threshold = FALSETTO_RATIO_DEFAULT
    result = "falsetto" if falsetto_ratio >= ratio_threshold else "chest"

    # [FIX] f-string内で条件式をフォーマット指定子に使うとValueError → 事前に文字列変換
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
            f"C={chest_score:.1f} F={falsetto_score:.1f} ratio={falsetto_ratio:.2f} "
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

    # ML判定を試行（crepe_confを伝搬）
    # モデルは地声サンプルに偏っているため、地声確定のみMLを信用する。
    # 裏声判定はルールベースに任せ、誤判定で裏声フレームを潰さないようにする。
    local_stats = stats or RegisterStats()
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
