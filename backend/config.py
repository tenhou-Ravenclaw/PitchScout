"""
config.py — 音域解析システムの共通定数

pipeline.py / classifier.py / feature_extractor.py で使用する閾値・パラメータを集約。
チューニング時はこのファイルのみ変更すればよい。
"""

import os


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    """環境変数から整数を読み込む。無効値なら default を返す。"""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
        return value if value >= minimum else default
    except (TypeError, ValueError):
        print(f"[WARN] {name} の値が不正です ('{raw}')。デフォルト {default} を使用します")
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    """環境変数から真偽値を読み込む。"""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


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

# === WORLD 解析パラメータ ===
WORLD_SAMPLE_RATE: int = 16000       # WORLD (pyworld) の解析サンプリングレート
WORLD_FRAME_PERIOD_MS: float = 5.0   # WORLD のフレーム周期 (ミリ秒)

# === 音声変換サンプリングレート ===
CONVERTER_MONO_SR: int = 16000       # マイク録音: 16kHz モノラル
CONVERTER_HQ_SR: int = 44100         # カラオケ: 44.1kHz ステレオ

# === Silero VAD ===
VAD_CHUNK_SIZE: int = 512            # チャンクサイズ (16kHz で 32ms)

# === 倍音解析ノイズフロア ===
HARMONIC_NOISE_FLOOR_DB: float = 8.0  # 有効倍音判定の閾値 (ノイズフロア + この値)

# === レジスター判定: セグメント決定 ===
SEGMENT_DECISION_THRESHOLD: float = 0.5  # フレーム比率 + RF 合成値の地声/裏声境界

# === 推薦スコアリング ===
RECOMMEND_LOW_PENALTY_WEIGHT: float = 6.0   # 最低音超過ペナルティ重み
RECOMMEND_HIGH_PENALTY_WEIGHT: float = 8.0  # 最高音超過ペナルティ重み
RECOMMEND_CENTER_DIFF_WEIGHT: float = 2.0   # 中心音ずれペナルティ重み
RECOMMEND_PERFECT_BONUS: float = 5.0        # 完全一致ボーナス
RECOMMEND_MIN_SCORE: float = 30.0           # 推薦対象の最低スコア

# === チャレンジ曲推薦 ===
CHALLENGE_SCORE_MIN: float = 5.0            # チャレンジ曲の最低スコア
CHALLENGE_SCORE_MAX: float = 30.0           # チャレンジ曲の最高スコア
CHALLENGE_LOW_PENALTY_MAX: float = 3.0      # 低音ペナルティ上限（半音）
CHALLENGE_HIGH_PENALTY_MAX: float = 5.0     # 高音ペナルティ上限（半音）

# === 解析時間警告 ===
ANALYSIS_TIME_WARNING_SEC: int = 240        # 処理時間警告閾値 (秒)

# === 解析同時実行制限 ===
# 重い音声解析で API worker を詰まらせないためのプロセス内上限。
# 複数 worker 構成では worker ごとにこの上限が適用される。
MAX_CONCURRENT_VOICE_ANALYSES: int = _env_int("MAX_CONCURRENT_VOICE_ANALYSES", 2)
MAX_CONCURRENT_KARAOKE_ANALYSES: int = _env_int("MAX_CONCURRENT_KARAOKE_ANALYSES", 1)

# === デバッグ音声保存 ===
# ユーザー音声を含むため、本番では既定で保存しない。必要な時だけ明示的に有効化する。
SAVE_DEBUG_AUDIO: bool = _env_bool("PITCHSCOUT_SAVE_DEBUG_AUDIO", False)

# === ログ制御 ===
# REGISTER_LOG_LEVEL: 0=なし, 1=サマリーのみ(デフォルト)
_raw_log_level = os.getenv("REGISTER_LOG_LEVEL", "1")
try:
    REGISTER_LOG_LEVEL: int = int(_raw_log_level)
except (ValueError, TypeError):
    print(f"[WARN] REGISTER_LOG_LEVEL の値が不正です ('{_raw_log_level}')。デフォルト 1 を使用します")
    REGISTER_LOG_LEVEL = 1
