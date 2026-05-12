"""
config.py — 音域解析システムの共通定数

pipeline.py / classifier.py / feature_extractor.py で使用する閾値・パラメータを集約。
チューニング時はこのファイルのみ変更すればよい。
"""

# === 音高検出 ===
VOICE_MIN_HZ = 65.0       # 人声の絶対下限 (C2付近)
VOICE_MAX_HZ = 1324.0     # 人声の絶対上限 (E6付近)
CREPE_SR = 16000           # レガシー名: 現在は WORLD (16kHz) で使用
CREPE_HOP_LENGTH = 320     # レガシー名: 旧 CREPE 設定。現在の WORLD は frame_period=5ms

# === フィルタリング（レガシー: 旧パイプライン用） ===
# 現在の WORLD パイプラインでは使用しない。debug_falsetto_audio.py が参照。
UNREALISTIC_LOWER_OCT = 1.5    # 下限: medianから1.5オクターブ下
UNREALISTIC_UPPER_OCT = 1.75   # 上限: medianから1.75オクターブ上
FALSETTO_DISPLAY_MIN_HZ = 330.0  # 互換用: 表示系の下限（判定は FALSETTO_HARD_MIN_HZ を使用）

# === 信頼度フィルタリング（レガシー: 旧 CREPE パイプライン用） ===
# 現在の WORLD パイプラインでは voiced_mask (f0 > 0) で判定するため直接は使用しない。
CONF_THRESHOLDS = [0.5, 0.35, 0.2, 0.1, 0.05, 0.01]
CONF_MIN_FRAMES = 5

# === 外れ値除去（レガシー: 旧パイプライン用） ===
# 現在の WORLD パイプラインでは使用しない。
CHEST_OUTLIER_PERCENTILE = 97
CHEST_OUTLIER_GAP_ST = 3       # 半音
FALSETTO_OUTLIER_PERCENTILE = 95
FALSETTO_OUTLIER_GAP_ST = 2
NO_FALSETTO_OUTLIER_PERCENTILE = 95
NO_FALSETTO_OUTLIER_GAP_ST = 3

# === 最高音混在解消（レガシー: 旧パイプライン用） ===
CLEANUP_SEMITONES = 2  # 2半音分の幅で地声/裏声の混在を解消

# === 段階的信頼度要求（レガシー: 旧 CREPE パイプライン用） ===
# 現在の WORLD パイプラインでは使用しない（debug_falsetto_audio.py が参照）。
GRADUATED_CONF_FAR = 0.65    # medianから1.5oct以上
GRADUATED_CONF_MID = 0.50    # medianから1.0oct以上
GRADUATED_CONF_NEAR = 0.35   # その他

# === レジスター判定 (classifier.py / pipeline.py) ===
# AP/HNR ゲート + RF フォールバック + 20次元ベクトル RF の併用判定。
FALSETTO_HARD_MIN_HZ = 330.0       # mid2E: 判定ハード下限（これ未満は地声確定）
HIGH_REGISTER_MIN_HZ = 523.0       # C5: 高音域の閾値切替ポイント

# AP / HNR ゲート閾値
AP_THRESHOLD_HIGH = 0.28           # 高音域 f0 >= HIGH_REGISTER_MIN_HZ
AP_THRESHOLD_TRANSITION = 0.35     # 遷移帯域 FALSETTO_HARD_MIN_HZ <= f0 < HIGH_REGISTER_MIN_HZ
HNR_THRESHOLD_HIGH = 8.0           # 高音域
HNR_THRESHOLD_TRANSITION = 6.0     # 遷移帯域

# 曖昧フレーム（AP/HNR 片側のみ成立）に対する RF フォールバック閾値
RF_CHEST_THRESHOLD = 0.60

# === ピッチ安定性 ===
STABILITY_MIN_SEGMENT = 3       # 持続音セグメントの最小フレーム数
STABILITY_SCALING = 0.8         # スコア変換係数 (avg_std * scaling を100から引く)

# === DeepFilterNet ノイズ除去 ===
# ノイズ減衰上限 (dB)。値が小さいほど音質保護優先。
DFN_ATTENUATION_LIMIT_DB: int = 20

# === スペクトル解析 FFT ===
# features.py の倍音解析が使用する FFT サイズ。
FFT_SPECTRUM_SIZE = 8192

# === 最高音推定 最大信頼度フォールバック閾値（レガシー: 旧 CREPE パイプライン用） ===
# 現在の WORLD パイプラインでは使用しない。
CREPE_MAX_CONF_THRESHOLDS: list[float] = [0.3, 0.15, 0.05]

# === お気に入りアーティスト上限 ===
# db/users.py の add_favorite_artist と routers/users.py のエラーメッセージで使用。
FAVORITE_ARTIST_LIMIT = 10

# === デバッグ音声出力 ===
# routers/analysis.py の _save_debug_outputs が使用するクリップ窓幅 (秒)。
DEBUG_CLIP_WINDOW_SEC: float = 1.0

# === 楽曲フィルタ上限 ===
# routers/songs.py の filter_by_range モードで全件取得する最大曲数。
# ~5000 曲で十分だが、DB 拡張時のメモリ圧迫を防ぐ安全弁。
MAX_FILTER_SONGS: int = 20000

# === アップロード制限 ===
# main.py のリクエストボディサイズ上限 (50MB)。
MAX_UPLOAD_BYTES: int = 50 * 1024 * 1024

# === 推薦配分 ===
# recommender.py のおすすめ曲配分パラメータ。
DISCOVERY_SLOTS: int = 4       # お気に入り以外から確保する曲数
FAV_MAX_SLOTS: int = 6         # お気に入りアーティストに割り当てる最大曲数
MAX_PER_ARTIST: int = 2        # 同一アーティスト最大曲数（多様性フィルタ）

# === 安定音域判定 ===
# routers/users.py の安定音域計算で使用。直近N件中この回数以上出現したラベルを安定とみなす。
STABLE_THRESHOLD: int = 4

# === ログ制御 ===
import os
# REGISTER_LOG_LEVEL: 0=なし, 1=サマリーのみ(デフォルト)
_raw_log_level = os.getenv("REGISTER_LOG_LEVEL", "1")
try:
    REGISTER_LOG_LEVEL: int = int(_raw_log_level)
except (ValueError, TypeError):
    print(f"[WARN] REGISTER_LOG_LEVEL の値が不正です ('{_raw_log_level}')。デフォルト 1 を使用します")
    REGISTER_LOG_LEVEL = 1