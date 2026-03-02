"""
config.py — 音域解析システムの共通定数

analyzer.py と register_classifier.py で使用する閾値・パラメータを集約。
チューニング時はこのファイルのみ変更すればよい。
"""

# === 音高検出 ===
VOICE_MIN_HZ = 65.0       # 人声の絶対下限 (C2付近)
VOICE_MAX_HZ = 1324.0     # 人声の絶対上限 (E6付近)
CREPE_SR = 16000           # CREPEのサンプリングレート
CREPE_HOP_LENGTH = 160     # 10ms (高速化: フレーム数半減)

# === フィルタリング ===
UNREALISTIC_LOWER_OCT = 1.5    # 下限: medianから1.5オクターブ下
UNREALISTIC_UPPER_OCT = 1.75   # 上限: medianから1.75オクターブ上
FALSETTO_DISPLAY_MIN_HZ = 330.0  # mid2E: 裏声の生理的下限 (表示フィルタ)

# === 信頼度フィルタリング ===
CONF_THRESHOLDS = [0.5, 0.35, 0.2, 0.1, 0.05, 0.01]  # 有効フレーム検出の閾値候補
CONF_MIN_FRAMES = 5  # 有効フレームの最小数

# === 外れ値除去 ===
CHEST_OUTLIER_PERCENTILE = 97
CHEST_OUTLIER_GAP_ST = 3       # 半音
FALSETTO_OUTLIER_PERCENTILE = 95
FALSETTO_OUTLIER_GAP_ST = 2
NO_FALSETTO_OUTLIER_PERCENTILE = 95
NO_FALSETTO_OUTLIER_GAP_ST = 3

# === 最高音混在解消 ===
CLEANUP_SEMITONES = 2  # 2半音分の幅で地声/裏声の混在を解消

# === 段階的信頼度要求 ===
GRADUATED_CONF_FAR = 0.65    # medianから1.5oct以上
GRADUATED_CONF_MID = 0.50    # medianから1.0oct以上
GRADUATED_CONF_NEAR = 0.35   # その他

# === レジスター判定 (register_classifier.py) ===
FALSETTO_HARD_MIN_HZ = 270.0       # これ以下は地声確定
ML_CONF_THRESHOLD_LOW_F0 = 0.75    # f0 < 500Hz (遷移帯域)
ML_CONF_THRESHOLD_HIGH = 0.75      # f0 >= 500Hz
ML_CONF_THRESHOLD_NOISY = 0.80     # CREPE信頼度低 + 高f0
ML_CONF_CHEST_HIGH_F0 = 0.85       # 地声 + f0 >= 400Hz
CREPE_NOISE_GATE = 0.35            # ピッチ推定ノイズゲート

# === ピッチ安定性 ===
STABILITY_MIN_SEGMENT = 3       # 持続音セグメントの最小フレーム数
STABILITY_SCALING = 0.8         # スコア変換係数 (avg_std * scaling を100から引く)

# === 最高音堅牢化 ===
MIN_SUSTAIN_FRAMES = 3          # 最高音として認定する最小フレーム数

# === ルールベース判定 ===
FALSETTO_RATIO_HIGH = 0.42    # f0 > 500Hz
FALSETTO_RATIO_MID = 0.48     # f0 > 400Hz
FALSETTO_RATIO_DEFAULT = 0.58 # その他

# === 裏声ノイズフィルタ（demucs残留楽器対策） ===
# フィルタ1: 連続フレーム要件 - 孤立した裏声フレームはノイズ
FALSETTO_MIN_CONSECUTIVE = 5     # 連続5フレーム未満の裏声群は除外
# フィルタ2: 最小比率 - 裏声が少なすぎる場合は全て地声に再分類
FALSETTO_MIN_RATIO = 0.05        # 裏声が全体の5%未満なら全て地声扱い
# フィルタ3: RMSパワー - 残留楽器はボーカルより音量が小さい
FALSETTO_RMS_RATIO = 0.15        # 地声RMS中央値の15%未満の裏声フレームは除外
# フィルタ3-b: 最小比率フィルタで除外する際、地声P97から何半音以内なら地声に戻すか
FALSETTO_RESCUE_SEMITONES = 4    # P97+4半音以内は高音地声として救済

# === ログ制御 ===
import os
# REGISTER_LOG_LEVEL: 0=なし, 1=サマリーのみ, 2=間引き(デフォルト), 3=全て
REGISTER_LOG_LEVEL = int(os.getenv("REGISTER_LOG_LEVEL", "1"))
REGISTER_LOG_INTERVAL = int(os.getenv("REGISTER_LOG_INTERVAL", "100"))  # 間引き間隔