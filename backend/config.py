"""
config.py — 音域解析システムの共通定数

analyzer.py と register_classifier.py で使用する閾値・パラメータを集約。
チューニング時はこのファイルのみ変更すればよい。
"""

# === 音高検出 ===
VOICE_MIN_HZ = 65.0       # 人声の絶対下限 (C2付近)
VOICE_MAX_HZ = 1324.0     # 人声の絶対上限 (E6付近)
CREPE_SR = 16000           # CREPEのサンプリングレート
CREPE_HOP_LENGTH = 320     # 20ms (高速化: フレーム数を1/4に削減)

# === フィルタリング ===
UNREALISTIC_LOWER_OCT = 1.5    # 下限: medianから1.5オクターブ下
UNREALISTIC_UPPER_OCT = 1.75   # 上限: medianから1.75オクターブ上
FALSETTO_DISPLAY_MIN_HZ = 330.0  # 互換用: 表示系の下限（判定は FALSETTO_HARD_MIN_HZ を使用）

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
# 中央値から遠い音程ほどノイズリスクが高いため、より高い信頼度を要求する。
# 1.5oct 以上離れた音(GRADUATED_CONF_FAR=0.65): 誤検出リスク大。CREPEの高信頼閾値。
# 1.0oct 以上(GRADUATED_CONF_MID=0.50): 中リスク。
# その他(GRADUATED_CONF_NEAR=0.35): CREPEのデフォルト信頼度ゲート。
GRADUATED_CONF_FAR = 0.65    # medianから1.5oct以上
GRADUATED_CONF_MID = 0.50    # medianから1.0oct以上
GRADUATED_CONF_NEAR = 0.35   # その他

# === レジスター判定 (register_classifier.py / pipeline.py) ===
# Gate-first Hybrid 判定の単一ソース定義。
FALSETTO_HARD_MIN_HZ = 330.0       # mid2E: 判定ハード下限（これ未満は地声確定）
HIGH_REGISTER_MIN_HZ = 523.0       # C5: 高音域の閾値切替ポイント

# AP / HNR ゲート（保守的初期値）
AP_THRESHOLD_HIGH = 0.28           # 高音域 f0 >= HIGH_REGISTER_MIN_HZ
AP_THRESHOLD_TRANSITION = 0.35     # 遷移帯域 FALSETTO_HARD_MIN_HZ <= f0 < HIGH_REGISTER_MIN_HZ
HNR_THRESHOLD_HIGH = 8.0           # 高音域
HNR_THRESHOLD_TRANSITION = 6.0     # 遷移帯域

# AP/HNR が片側のみ成立した曖昧フレームに対する RF フォールバック閾値
RF_CHEST_THRESHOLD = 0.60

ML_CONF_THRESHOLD_LOW_F0 = 0.75    # f0 < 500Hz (遷移帯域)
ML_CONF_THRESHOLD_HIGH = 0.75      # f0 >= 500Hz
ML_CONF_THRESHOLD_NOISY = 0.80     # CREPE信頼度低 + 高f0
ML_CONF_CHEST_HIGH_F0 = 0.90       # 地声確定の最低信頼度（f0問わず）: トレーニングデータが95%地声に偏っているため高めに設定
CREPE_NOISE_GATE = 0.35            # ピッチ推定ノイズゲート
# MLは地声補助用途に限定し、対象帯域のみ実行して負荷を抑える
ML_CHEST_ASSIST_MIN_HZ = 270.0
ML_CHEST_ASSIST_MAX_HZ = 430.0
ML_CHEST_ASSIST_MIN_CREPE_CONF = 0.55

# === ピッチ安定性 ===
STABILITY_MIN_SEGMENT = 3       # 持続音セグメントの最小フレーム数
STABILITY_SCALING = 0.8         # スコア変換係数 (avg_std * scaling を100から引く)

# === 最高音堅牢化 ===
MIN_SUSTAIN_FRAMES = 5          # 最高音として認定する最小フレーム数 (3→5: 60ms→100ms、瞬間ノイズ除外強化)
# 持続条件を満たす候補がない場合のフォールバック時に、上位ノイズを何%切るか。
# 旧運用の1%相当より強めに、3%トリムで単発スパイクを抑制する。
ROBUST_MAX_FALLBACK_TRIM_RATIO = 0.03

# === ルールベース判定 ===
# _classify_rules で falsetto_score/(chest+falsetto) がこの値を超えたら裏声と判定。
# 高音域(f0>500Hz)では裏声の発生確率が高いため判定閾値を低めに設定:
#   FALSETTO_RATIO_HIGH=0.46: 46%以上で裏声。倍音構造が変質しやすいDemucs出力対策。
#   FALSETTO_RATIO_MID=0.52:  遷移帯域。
#   FALSETTO_RATIO_DEFAULT=0.60: 低音域では誤判定防止のため高めに設定。
FALSETTO_RATIO_HIGH = 0.42    # f0 > 500Hz (高音域の裏声を取りこぼさないよう閾値を上げすぎない)
FALSETTO_RATIO_MID = 0.52     # f0 > 400Hz
FALSETTO_RATIO_DEFAULT = 0.60 # その他

# === 裏声ノイズフィルタ（demucs残留楽器対策） ===
# フィルタ1: 連続フレーム要件 - 孤立した裏声フレームはノイズ
# 10フレーム(=200ms@20ms/frame)未満の連続群は楽器の一時的な倍音と判断して除外。
# 15フレームでも実音源で裏声が落ちる場合があるため、さらに緩和。
FALSETTO_MIN_CONSECUTIVE = 10    # 連続10フレーム未満の裏声群は除外
# フィルタ2: 最小比率 - 裏声が少なすぎる場合は全て地声に再分類
# 4%未満を除外。アーティファクトは通常全体の1-3%程度しか残留しない。
FALSETTO_MIN_RATIO = 0.04        # 裏声が全体の4%未満なら全て地声扱い
# 浮動小数の丸め誤差で境界値が誤って全除外されるのを防ぐ
FALSETTO_MIN_RATIO_EPSILON = 0.001
# 最小比率フィルタの安全弁: 裏声音量が一定件数かつ十分な音程広がりなら全除外しない
FALSETTO_KEEP_MIN_FRAMES = 240
FALSETTO_KEEP_MIN_SPREAD_SEMITONES = 3.0
# フィルタ3: RMSパワー - 残留楽器はボーカルより音量が小さい
# 地声RMS中央値の25%未満 = 歌声の音量に対して極端に小さいフレームは楽器リークと判断。
# 15%では残留楽器（地声の20-25%程度の音量）が通過してしまうため強化。
FALSETTO_RMS_RATIO = 0.25        # 地声RMS中央値の25%未満の裏声フレームは除外
# フィルタ3-b: 最小比率フィルタで除外する際、地声P97から何半音以内なら地声に戻すか
# 2半音=全音。救済後フレームは外れ値除去を通過済みでないため、狭い範囲に抑える。
# 4半音(旧値)だと裏声フレームが地声に逆流して地声最高音が過大評価される原因になっていた。
FALSETTO_RESCUE_SEMITONES = 2    # P97+2半音以内は高音地声として救済

# === Silero VAD フィルタ ===
# 歌声検出の信頼度閾値 (0.0-1.0)。小さいほど感度高（歌声を残しやすい）。
# デフォルト0.5は話し声向けで歌声を落とし過ぎるため、0.3に設定。
# 0.25未満は楽器リークを通し過ぎ、0.35超は正当な裏声を落とすリスクあり。
SILERO_VAD_THRESHOLD: float = 0.3
# VAD フィルタが裏声フレームの MAX_VAD_REMOVAL_RATIO 以上を除去しようとする場合、
# 音程の広がり（半音単位の標準偏差）を確認して本物の裏声か楽器かを判定する。
# 0.70 = 70%超除去でセカンドチェックへ進む。
VAD_MAX_REMOVAL_RATIO: float = 0.70
# 上記チェック時に「音程広がりがこの値未満 = 単一音の楽器持続音」と判定してVADを適用する。
# 本物の裏声は複数音程にまたがるため 1.5 半音以上の広がりを持つはず。
# 楽器の持続音（アーティファクト）は同一音程に集中するため広がりが 0.5 半音以下になりやすい。
VAD_NARROW_CLUSTER_SEMITONES: float = 1.5

# === DeepFilterNet ノイズ除去 ===
# ノイズ減衰上限 (dB)。値が小さいほど音質保護優先。
# 20dB: 残留楽器音を除去しつつボーカルへの影響を最小化するデフォルト値。
DFN_ATTENUATION_LIMIT_DB: int = 20

# === スペクトル解析 FFT ===
# classifier.py の _classify_rules / check_octave_by_spectrum が共用する FFT サイズ。
# 変更時は両方の関数の動作に影響するため慎重に。
FFT_SPECTRUM_SIZE = 8192

# === 最高音推定 最大信頼度フォールバック閾値 ===
# get_min_max_from_crepe で conf>=閾値 の最大音を求める際のフォールバック順序。
# どの閾値でも 1 フレーム以上見つかれば処理を続行する。
CREPE_MAX_CONF_THRESHOLDS: list[float] = [0.3, 0.15, 0.05]

# === お気に入りアーティスト上限 ===
# db/users.py の add_favorite_artist と routers/users.py のエラーメッセージで使用。
FAVORITE_ARTIST_LIMIT = 10

# === ログ制御 ===
import os
# REGISTER_LOG_LEVEL: 0=なし, 1=サマリーのみ(デフォルト), 2=間引き, 3=全て
# ※ サマリーは print_register_summary() が出力。フレームログは level 2/3 のみ。
REGISTER_LOG_LEVEL = int(os.getenv("REGISTER_LOG_LEVEL", "1"))
# REGISTER_LOG_INTERVAL: 間引きモード(level=2)でログを出力するフレーム間隔。
# CREPE_HOP_LENGTH=320 / CREPE_SR=16000 より 1フレーム = 20ms。
# デフォルト100フレーム = 約2秒ごとにログ出力。
REGISTER_LOG_INTERVAL = int(os.getenv("REGISTER_LOG_INTERVAL", "100"))