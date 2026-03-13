import numpy as np
import soundfile as sf
import torch
import torchcrepe
import librosa
from analysis.classifier import classify_register, new_register_stats, print_register_summary
from analysis.scoring import analyze_singing_ability
from audio.noise import score_frame_vad
from note_converter import hz_to_label_and_hz
from config import (
    VOICE_MIN_HZ, VOICE_MAX_HZ, CREPE_SR, CREPE_HOP_LENGTH,
    FALSETTO_DISPLAY_MIN_HZ, CONF_THRESHOLDS, CONF_MIN_FRAMES,
    CHEST_OUTLIER_PERCENTILE, CHEST_OUTLIER_GAP_ST,
    FALSETTO_OUTLIER_PERCENTILE, FALSETTO_OUTLIER_GAP_ST,
    NO_FALSETTO_OUTLIER_PERCENTILE, NO_FALSETTO_OUTLIER_GAP_ST,
    CLEANUP_SEMITONES,
    GRADUATED_CONF_FAR, GRADUATED_CONF_MID, GRADUATED_CONF_NEAR,
    UNREALISTIC_LOWER_OCT, UNREALISTIC_UPPER_OCT,
    MIN_SUSTAIN_FRAMES,
    FALSETTO_MIN_CONSECUTIVE, FALSETTO_MIN_RATIO, FALSETTO_RMS_RATIO,
    FALSETTO_RESCUE_SEMITONES,
    SILERO_VAD_THRESHOLD, VAD_MAX_REMOVAL_RATIO, VAD_NARROW_CLUSTER_SEMITONES,
    FFT_SPECTRUM_SIZE,
    CREPE_MAX_CONF_THRESHOLDS,
)


# ============================================================
# fix_octave_errors
# レジスター判定・中央値計算用のオクターブ修正
# ★ min/maxには使わない（中央値に引き寄せて正しい最高音を削ってしまうため）
# ============================================================
def fix_octave_errors(f0: np.ndarray, conf: np.ndarray) -> np.ndarray:
    if len(f0) < 5:
        return f0.copy()
    f0_fixed  = f0.copy()
    hc        = conf >= 0.5
    reference = np.median(f0[hc]) if hc.sum() >= 5 else np.median(f0)

    for i, freq in enumerate(f0_fixed):
        if freq <= 0:
            continue
        # 高音保護: 中央値の1.5倍以上かつ人声範囲内かつ高信頼度 → 正当な高音跳躍なので補正しない
        # ノイズフレーム(conf<0.5)は保護せずオクターブ補正の対象に残す
        if freq > reference * 1.5 and VOICE_MIN_HZ <= freq <= VOICE_MAX_HZ and conf[i] >= 0.5:
            continue
        doubled, halved = freq * 2, freq / 2
        can_up   = VOICE_MIN_HZ <= doubled <= VOICE_MAX_HZ
        can_down = VOICE_MIN_HZ <= halved  <= VOICE_MAX_HZ
        d_orig   = abs(freq    - reference)
        d_up     = abs(doubled - reference) if can_up   else float('inf')
        d_down   = abs(halved  - reference) if can_down else float('inf')
        if can_up   and d_up   < d_orig and d_up   < d_down: f0_fixed[i] = doubled
        elif can_down and d_down < d_orig and d_down < d_up:  f0_fixed[i] = halved
    return f0_fixed


# ============================================================
# remove_unrealistic_range
# 非対称フィルタ: 下限は厳格（サブハーモニクス除去）、上限は緩和（高音保持）
# ============================================================
def remove_unrealistic_range(f0: np.ndarray, conf: np.ndarray) -> tuple:
    if len(f0) < 5:
        return f0.copy(), conf.copy()
    hc     = conf >= 0.3
    median = np.median(f0[hc]) if hc.sum() >= 3 else np.median(f0)
    lower_factor = 2 ** UNREALISTIC_LOWER_OCT
    upper_factor = 2 ** UNREALISTIC_UPPER_OCT
    mask = (f0 >= median / lower_factor) & (f0 <= median * upper_factor)
    return f0[mask], conf[mask]


# ============================================================
# remove_isolated_extremes
# 孤立した極端な高音フレームを除去（ノイズ対策の最終防衛線）
# ============================================================
def remove_isolated_extremes(notes, min_neighbors=4):
    """孤立した極端値を除去。1半音以内にmin_neighbors未満のフレームは除外"""
    if len(notes) < min_neighbors:
        return notes
    arr = np.array(notes)
    median_val = np.median(arr)
    # 中央値の1.2倍以上のフレームをチェック（楽器音・ガイドボーカルを捕捉するため緩和）
    high_threshold = median_val * 1.2
    semitone = 2 ** (1 / 12)  # ≈1.0595
    result = []
    removed = 0
    for f in notes:
        if f < high_threshold:
            result.append(f)
            continue
        # 1半音以内の近傍フレーム数をカウント
        neighbors = sum(1 for x in notes if f / semitone <= x <= f * semitone)
        if neighbors >= min_neighbors:
            result.append(f)
        else:
            removed += 1
    if removed > 0:
        print(f"[DEBUG] 孤立フレーム除去: {removed}フレーム削除 (閾値={high_threshold:.1f}Hz以上, 近傍{min_neighbors}未満)")
    return result if result else notes  # 全除去を防止


# ============================================================
# remove_statistical_outliers
# パーセンタイルベースの外れ値除去（ノイズ・伴奏混入の安全ネット）
# ============================================================
def remove_statistical_outliers(notes, percentile=97, max_semitones_gap=6):
    """主要分布から大きく離れたフレームを除去。
    P{percentile}から{max_semitones_gap}半音以上離れたフレームを外れ値とする。"""
    if len(notes) < 10:
        return notes
    arr = np.array(notes)
    ref = np.percentile(arr, percentile)
    threshold = ref * (2 ** (max_semitones_gap / 12))
    result = [f for f in notes if f <= threshold]
    removed = len(notes) - len(result)
    if removed > 0:
        print(f"[DEBUG] 統計外れ値除去: {removed}フレーム削除 "
              f"(参照P{percentile}={ref:.1f}Hz, 閾値={threshold:.1f}Hz)")
    return result if result else notes  # 全除去を防止


# ============================================================
# _get_robust_max
# 最高音候補の最小持続フレーム要件（一瞬のノイズを除外）
# ============================================================
def _get_robust_max(notes, min_sustain=None):
    """最高音候補が min_sustain フレーム以上存在することを要求。
    1半音以内のフレーム数でカウント。不足なら段階的に下げる。"""
    if min_sustain is None:
        min_sustain = MIN_SUSTAIN_FRAMES
    if not notes:
        return None
    arr = sorted(notes, reverse=True)
    semitone = 2 ** (1 / 12)
    checked = set()
    for candidate in arr:
        key = round(candidate, 1)
        if key in checked:
            continue
        checked.add(key)
        count = sum(1 for f in notes if candidate / semitone <= f <= candidate * semitone)
        if count >= min_sustain:
            return candidate
    return arr[0]  # フォールバック: 全て不足なら元のmax


# ============================================================
# check_octave_by_spectrum
# CREPEがviterbi平滑化で1オクターブ低く検出した場合の補正
# ============================================================
def check_octave_by_spectrum(y_seg: np.ndarray, sr: int, candidate_hz: float) -> float:
    doubled = candidate_hz * 2
    if doubled > sr / 2 * 0.9 or doubled > VOICE_MAX_HZ or len(y_seg) < 512:
        return candidate_hz

    n_fft = FFT_SPECTRUM_SIZE
    win   = np.hanning(min(len(y_seg), n_fft))
    y_w   = np.zeros(n_fft)
    n     = min(len(y_seg), n_fft)
    y_w[:n] = y_seg[:n] * win[:n]
    fft   = np.abs(np.fft.rfft(y_w))
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)

    def band_energy(hz, width=0.04):
        if hz <= 0 or hz >= sr / 2:
            return 0.0
        lo = np.searchsorted(freqs, hz * (1 - width))
        hi = np.searchsorted(freqs, hz * (1 + width))
        return float(np.max(fft[lo:hi])) if lo < hi else 0.0

    e_candidate = band_energy(candidate_hz)
    e_doubled   = band_energy(doubled)

    if e_candidate <= 1e-10:
        return candidate_hz

    ratio = e_doubled / e_candidate
    # doubled が candidate より明確に強い場合のみ補正（閾値1.2）
    if ratio >= 1.2:
        print(f"[DEBUG] 最高音オクターブ修正: {candidate_hz:.1f}→{doubled:.1f}Hz ratio={ratio:.2f}")
        return doubled
    return candidate_hz


# ============================================================
# get_min_max_from_crepe
# ============================================================
def get_min_max_from_crepe(f0: np.ndarray, conf: np.ndarray,
                            y_16k: np.ndarray = None,
                            sr_crepe: int = 16000,
                            hop_length: int = 80,
                            valid_indices: np.ndarray = None) -> tuple:
    """
    CREPEのconfidenceを使ってmin/maxを取得。

    valid_indices: f0がf0_np[valid_indices]で作られた場合に、
                   y_16k上の正しい位置を計算するために必要。
                   Noneの場合はf0内のローカルインデックスを使用（不正確）。
    """
    if len(f0) == 0:
        return 0.0, 0.0

    # ---- 最高音: CREPE_MAX_CONF_THRESHOLDS の順に閾値を下げて最大値を探す ----
    # MIN_SUSTAIN_FRAMES フレーム以上存在しないと孤立ノイズを最高音として誤採用するため
    # フレーム数要件を課す。全閾値で不足する場合は最後の mask_max をそのまま使う。
    for max_th in CREPE_MAX_CONF_THRESHOLDS:
        mask_max = conf >= max_th
        if mask_max.sum() >= MIN_SUSTAIN_FRAMES:
            break
    raw_max = float(np.max(f0[mask_max]))

    # スペクトルでオクターブ補正
    if y_16k is not None:
        local_indices_max = np.where(mask_max)[0]
        local_max_idx     = local_indices_max[np.argmax(f0[local_indices_max])]
        if valid_indices is not None:
            orig_frame_idx = int(valid_indices[local_max_idx])
        else:
            orig_frame_idx = int(local_max_idx)
        center    = orig_frame_idx * hop_length
        seg       = y_16k[max(0, center - 4096): min(len(y_16k), center + 4096)]
        raw_max   = check_octave_by_spectrum(seg, sr_crepe, raw_max)

    # ---- 最低音: conf >= 0.5 の最小値 ----
    for min_th in [0.5, 0.35, 0.2, 0.1]:
        mask_min = conf >= min_th
        if mask_min.sum() >= 3:
            break
    overall_min = float(np.min(f0[mask_min]))

    print(f"[DEBUG] max_th={max_th:.2f} min_th={min_th:.2f} "
          f"max_frames={mask_max.sum()} min_frames={mask_min.sum()} "
          f"raw_min={overall_min:.1f} raw_max={raw_max:.1f}")
    return overall_min, raw_max


# ============================================================
# run_crepe
# ============================================================
def run_crepe(audio_tensor, sr, hop_length, device, model_size='tiny'):
    common = dict(
        audio=audio_tensor, sample_rate=sr, hop_length=hop_length,
        fmin=65, fmax=1400, model=model_size,
        batch_size=2048, device=device, return_periodicity=True,
    )
    # 高速化: weighted_argmax優先（viterbiより2-3倍高速）
    for name, get_dec in [
        ("weighted_argmax", lambda: torchcrepe.decode.weighted_argmax),
        ("viterbi",         lambda: torchcrepe.decode.viterbi),
        ("none",            None),
    ]:
        try:
            print(f"[DEBUG] デコーダー '{name}' で試行中...")
            kw = {**common, "decoder": get_dec()} if get_dec else common
            f0, conf = torchcrepe.predict(**kw)
            print(f"[INFO] CREPE ({model_size}, {name}) 成功")
            return f0, conf
        except (AttributeError, TypeError) as e:
            print(f"[WARN] decoder={name} 失敗: {e}")
        except Exception:
            raise
    raise RuntimeError("torchcrepe: 全デコーダーで失敗")


# ============================================================
# analyze — パイプライン関数群
# ============================================================

def _load_audio(wav_path: str) -> dict:
    """WAV読込+バリデーション → dict(y, sr) or dict(error)"""
    print(f"\n{'='*60}")
    print(f"[INFO] 分析開始: {wav_path}")
    print(f"{'='*60}")

    print(f"[STEP 1/7] WAVファイル読み込み中...")
    try:
        y, sr = sf.read(wav_path)
        if len(y.shape) > 1:
            print(f"[INFO] ステレオをモノラルに変換中...")
            y = np.mean(y, axis=1)
        y = y.astype(np.float32)
    except Exception as e:
        return {"error": f"WAVファイルの読み込みに失敗しました: {str(e)}"}

    duration = len(y) / sr
    print(f"[DEBUG] 読込完了: SR={sr}, duration={duration:.2f}s, max={np.max(np.abs(y)):.4f}")

    if duration < 0.3:
        return {"error": "音声が短すぎます（0.3秒以上必要）。"}
    if np.max(np.abs(y)) < 0.0001:
        return {"error": "音が小さすぎます（ほぼ無音）。"}

    return {"y": y, "sr": sr}


def _preprocess(y: np.ndarray, sr: int) -> dict:
    """正規化+リサンプル+テンソル → dict(y_16k, sr_crepe, hop_length, device, audio_tensor)"""
    print(f"\n[STEP 2/7] 音声前処理中...")
    print(f"[INFO] 音量正規化中... (目標: 0.95)")
    y = y / (np.max(np.abs(y)) + 1e-8) * 0.95

    sr_crepe   = CREPE_SR
    print(f"[INFO] リサンプリング中: {sr}Hz → {sr_crepe}Hz")
    y_16k      = librosa.resample(y, orig_sr=sr, target_sr=sr_crepe) if sr != sr_crepe else y.copy()
    hop_length = CREPE_HOP_LENGTH
    # GPU優先: CUDA → MPS（Apple Silicon）→ CPU の順にフォールバック
    if torch.cuda.is_available():
        device = 'cuda'
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = 'mps'
    else:
        device = 'cpu'
    print(f"[INFO] デバイス: {device.upper()} (hop_length={hop_length})")
    audio_tensor = torch.tensor(np.copy(y_16k)).unsqueeze(0)
    print(f"[DEBUG] 前処理完了: tensor shape={audio_tensor.shape}")

    return {
        "y_16k": y_16k, "sr_crepe": sr_crepe,
        "hop_length": hop_length, "device": device,
        "audio_tensor": audio_tensor,
    }


def _run_pitch_detection(audio_tensor, sr: int, hop_length: int, device: str) -> dict:
    """CREPE実行 → dict(f0, conf) or dict(error)"""
    print(f"\n[STEP 3/7] CREPE音高推定中...")
    f0_raw = conf_raw = None
    for model_size in ['tiny', 'small']:
        try:
            print(f"[INFO] CREPEモデル '{model_size}' で試行中... (device={device})")
            f0_raw, conf_raw = run_crepe(audio_tensor, sr, hop_length, device, model_size)
            print(f"[DEBUG] CREPE ({model_size}) 成功")
            break
        except Exception as e:
            print(f"[ERROR] CREPE ({model_size}) 失敗: {type(e).__name__}: {e}")

    if f0_raw is None:
        return {"error": "解析エンジン(CREPE)の実行に失敗しました。"}

    f0_np   = f0_raw.squeeze().detach().cpu().numpy()
    conf_np = conf_raw.squeeze().detach().cpu().numpy()
    print(f"[DEBUG] CREPE完了: frames={len(f0_np)} conf_max={np.max(conf_np):.4f} conf_mean={np.mean(conf_np):.4f}")

    return {"f0": f0_np, "conf": conf_np}


def _filter_frames(f0_np: np.ndarray, conf_np: np.ndarray) -> dict:
    """フィルタリング+オクターブ補正+中央値 → dict or dict(error)"""
    print(f"\n[STEP 4/7] 信頼度フィルタリング中...")

    # --- confidence フィルタ ---
    for th in CONF_THRESHOLDS:
        idx = np.where(conf_np >= th)[0]
        if len(idx) >= CONF_MIN_FRAMES:
            valid_indices = idx
            print(f"[INFO] 有効フレーム検出: {len(idx)}個 (confidence threshold={th:.2f})")
            break
    else:
        return {"error": f"歌声が検出できませんでした。(conf_max={np.max(conf_np):.4f})"}

    f0_v   = f0_np[valid_indices].copy()
    conf_v = conf_np[valid_indices].copy()

    print(f"[INFO] 人声音域フィルタ適用中 ({VOICE_MIN_HZ}Hz - {VOICE_MAX_HZ}Hz)...")
    # --- 人声絶対範囲 ---
    mask   = (f0_v >= VOICE_MIN_HZ) & (f0_v <= VOICE_MAX_HZ)
    f0_v   = f0_v[mask]
    conf_v = conf_v[mask]
    valid_indices_filtered = valid_indices[mask]
    print(f"[DEBUG] 人声範囲内: {len(f0_v)}フレーム")

    if len(f0_v) == 0:
        return {
            "error": (
                f"人声の音域範囲（{VOICE_MIN_HZ:.0f}Hz〜{VOICE_MAX_HZ:.0f}Hz）内の音が検出できませんでした。"
                "声が小さすぎるか、音域が極端に高低すぎる可能性があります。"
            )
        }

    print(f"\n[STEP 5/7] 音域データ処理中...")
    # --- レジスター判定用フィルタ（min/maxとは独立） ---
    print(f"[INFO] 異常値除去中 (下{UNREALISTIC_LOWER_OCT}oct / 上{UNREALISTIC_UPPER_OCT}oct)...")
    f0_reg, conf_reg = remove_unrealistic_range(f0_v, conf_v)
    if len(f0_reg) == 0:
        return {"error": "有効な音域データが残りませんでした。"}
    print(f"[DEBUG] 残留フレーム: {len(f0_reg)}個")

    # remove_unrealistic_range後もvalid_indicesを対応させる
    # ★ 同じ定数を使って再導出（旧コードの 2.0 vs 1.75 不一致を修正）
    lower_factor = 2 ** UNREALISTIC_LOWER_OCT
    upper_factor = 2 ** UNREALISTIC_UPPER_OCT
    hc      = conf_v >= 0.3
    median0 = np.median(f0_v[hc]) if hc.sum() >= 3 else np.median(f0_v)
    reg_mask = (f0_v >= median0 / lower_factor) & (f0_v <= median0 * upper_factor)
    valid_indices_reg = valid_indices_filtered[reg_mask]

    print(f"[INFO] オクターブエラー修正中...")
    f0_reg_fixed = fix_octave_errors(f0_reg, conf_reg)

    # 信頼度重み付き中央値
    print(f"[INFO] 中央値計算中...")
    sort_idx    = np.argsort(f0_reg_fixed)
    cum_conf    = np.cumsum(conf_reg[sort_idx])
    mid_idx     = np.searchsorted(cum_conf, cum_conf[-1] / 2)
    median_freq = f0_reg_fixed[sort_idx[mid_idx]]
    print(f"[DEBUG] 中央値={median_freq:.1f} Hz, レジスター判定フレーム数={len(f0_reg_fixed)}")

    return {
        "f0_reg": f0_reg, "f0_reg_fixed": f0_reg_fixed,
        "conf_reg": conf_reg, "valid_indices_reg": valid_indices_reg,
        "median_freq": median_freq,
    }


# ============================================================
# filter_falsetto_noise
# demucs残留楽器による偽裏声を3段階で除去
# ============================================================
def filter_falsetto_consecutive(falsetto_data, min_consecutive):
    """
    フィルタ1: 連続フレーム要件
    時間的に連続しない孤立裏声フレームを除去。
    残留楽器は散発的、本当の裏声は連続する。

    Args:
        falsetto_data: list of (array_index, freq, rms)
        min_consecutive: 最小連続フレーム数
    Returns:
        フィルタ後のfalsetto_data
    """
    if len(falsetto_data) < min_consecutive:
        return []

    # array_indexでソートしてグループ化
    sorted_data = sorted(falsetto_data, key=lambda x: x[0])
    groups = []
    current_group = [sorted_data[0]]

    for item in sorted_data[1:]:
        # 前のフレームとの間隔が1以下なら連続とみなす（≒20ms以内）
        # 旧: <= 2(40ms)。アーティファクトが断続的に混入するケースに対応するため厳化。
        if item[0] - current_group[-1][0] <= 1:
            current_group.append(item)
        else:
            groups.append(current_group)
            current_group = [item]
    groups.append(current_group)

    # min_consecutive以上のグループのみ残す
    result = []
    removed = 0
    for g in groups:
        if len(g) >= min_consecutive:
            result.extend(g)
        else:
            removed += len(g)

    if removed > 0:
        print(f"[FILTER] 連続フレームフィルタ: {removed}フレーム除外 "
              f"(連続{min_consecutive}未満のグループ除去, 残{len(result)}フレーム)")
    return result


def filter_falsetto_rms(falsetto_data, chest_rms_values, rms_ratio):
    """
    フィルタ2: RMSパワーフィルタ
    地声の中央RMSと比べて極端に小さい裏声フレームを除去。
    残留楽器はボーカルより音量が小さい。

    Args:
        falsetto_data: list of (array_index, freq, rms)
        chest_rms_values: list of float (地声フレームのRMS値)
        rms_ratio: 閾値比率
    Returns:
        フィルタ後のfalsetto_data
    """
    if not falsetto_data or not chest_rms_values:
        return falsetto_data

    chest_rms_median = float(np.median(chest_rms_values))
    rms_threshold = chest_rms_median * rms_ratio

    result = [item for item in falsetto_data if item[2] >= rms_threshold]
    removed = len(falsetto_data) - len(result)

    if removed > 0:
        print(f"[FILTER] RMSパワーフィルタ: {removed}フレーム除外 "
              f"(地声RMS中央={chest_rms_median:.4f}, 閾値={rms_threshold:.4f}, 残{len(result)}フレーム)")
    return result


def filter_falsetto_vad(
    falsetto_data: list,
    y_16k: np.ndarray,
    valid_indices_reg: np.ndarray,
    hop_length: int,
    threshold: float,
    frame_len: int = 2048,
) -> list:
    """
    フィルタ3: Silero VAD フレームスコアフィルタ
    各フレームの VAD スコアが threshold 未満のものを楽器リークとして除去する。

    区間ベース（「歌声区間に含まれるか」）ではなくフレーム単位でスコアを付与する。
    楽器ハーモニクスは歌声と異なる音響特徴を持つため、個別スコアで区別できる。

    モデル未初期化の場合は score_frame_vad が 1.0 を返すため
    全フレームが threshold を超えてフィルタは無効になる（フォールバック）。

    Args:
        falsetto_data: list of (local_index, freq, rms) タプル。
        y_16k: 16kHz モノラル音声の numpy 配列。
        valid_indices_reg: CREPE フレームインデックスの配列。
        hop_length: CREPE のホップ長（サンプル数）。
        threshold: VAD スコアの閾値。これ未満を楽器リークと判定。
                   config.SILERO_VAD_THRESHOLD を渡す。
        frame_len: フレームのサンプル数（デフォルト 2048 = 128ms at 16kHz）。

    Returns:
        フィルタ後の falsetto_data。
    """
    if not falsetto_data:
        return falsetto_data

    result = []
    low_score_count = 0
    for item in falsetto_data:
        center = int(valid_indices_reg[item[0]]) * hop_length
        frame = y_16k[max(0, center - frame_len // 2):
                      min(len(y_16k), center + frame_len // 2)]
        vad_score = score_frame_vad(frame)
        if vad_score >= threshold:
            result.append(item)
        else:
            low_score_count += 1

    removed = len(falsetto_data) - len(result)
    removal_ratio = removed / len(falsetto_data) if falsetto_data else 0.0

    # 安全弁: VAD_MAX_REMOVAL_RATIO 超の除去は Demucs後の裏声誤判定の可能性がある。
    # ただし「楽器の持続音（単一音程に集中）」と「本物の裏声（複数音程に広がる）」は
    # 音程の広がりで区別できる。
    if removal_ratio > VAD_MAX_REMOVAL_RATIO:
        falsetto_freqs = np.array([item[1] for item in falsetto_data])
        # log2周波数の標準偏差を半音換算（広がり = 0 なら全フレームが同一音程）
        semitone_spread = 12.0 * float(np.std(np.log2(falsetto_freqs + 1e-8)))

        if semitone_spread < VAD_NARROW_CLUSTER_SEMITONES:
            # 音程が単一付近 = 楽器の持続音。VADの判定を信頼してフィルタを適用する。
            print(f"[FILTER] VADフィルタ: 除去率{removal_ratio*100:.0f}%, "
                  f"音程広がり={semitone_spread:.2f}半音 < {VAD_NARROW_CLUSTER_SEMITONES}半音 "
                  f"→ 楽器持続音と判定、{removed}フレーム除外 (残{len(result)}フレーム)")
        else:
            # 音程が広範囲 = 本物の裏声。Demucs後の誤判定としてスキップする。
            print(f"[WARN] VADフィルタ: 除去率{removal_ratio*100:.0f}%, "
                  f"音程広がり={semitone_spread:.2f}半音 ≥ {VAD_NARROW_CLUSTER_SEMITONES}半音 "
                  f"→ Demucs後の裏声誤判定を検出、フィルタをスキップ ({len(falsetto_data)}フレームを保持)")
            return falsetto_data

    else:
        if removed > 0:
            print(f"[FILTER] VADフィルタ: {removed}フレーム除外 "
                  f"(VADスコア<{threshold:.2f}の楽器リーク, 残{len(result)}フレーム)")
        elif low_score_count == 0 and falsetto_data:
            print(f"[DEBUG] VADフィルタ: 全{len(falsetto_data)}フレームが閾値({threshold:.2f})を超え除外なし")
    return result


def filter_falsetto_min_ratio(falsetto_notes, chest_notes, min_ratio):
    """
    フィルタ3: 最小比率フィルタ
    裏声が全体の一定割合未満なら、全て地声に再分類。
    裏声を本当に使う曲なら一定割合を超えるはず。

    Args:
        falsetto_notes: list of float (周波数)
        chest_notes: list of float (周波数)
        min_ratio: 最小裏声比率 (0.0-1.0)
    Returns:
        (chest_notes, falsetto_notes) のタプル
    """
    total = len(chest_notes) + len(falsetto_notes)
    if total == 0 or not falsetto_notes:
        return chest_notes, falsetto_notes

    actual_ratio = len(falsetto_notes) / total
    if actual_ratio < min_ratio:
        # 裏声が少なすぎる → ノイズの可能性が高い
        # ただし地声の分布に近いフレームは高音の地声が誤判定された可能性がある
        # → 地声P97から一定範囲内なら地声に戻し、遠いものだけ捨てる
        if chest_notes:
            chest_arr = np.array(chest_notes)
            chest_p97 = float(np.percentile(chest_arr, 97))
            # P97 + 4半音以内 → 地声に戻す（高音の地声が裏声誤判定されたケース）
            # P97 + 4半音超え → ノイズとして除外（残留楽器）
            rescue_threshold = chest_p97 * (2 ** (FALSETTO_RESCUE_SEMITONES / 12))
            rescued = [f for f in falsetto_notes if f <= rescue_threshold]
            discarded = [f for f in falsetto_notes if f > rescue_threshold]
            chest_notes = chest_notes + rescued
            print(f"[FILTER] 最小比率フィルタ: 裏声{len(falsetto_notes)}フレーム "
                  f"({actual_ratio*100:.1f}% < {min_ratio*100:.0f}%) "
                  f"→ {len(rescued)}フレーム地声に復帰 (P97={chest_p97:.1f}Hz, 上限={rescue_threshold:.1f}Hz), "
                  f"{len(discarded)}フレームをノイズ除外")
        else:
            print(f"[FILTER] 最小比率フィルタ: 裏声{len(falsetto_notes)}フレーム "
                  f"({actual_ratio*100:.1f}% < {min_ratio*100:.0f}%) → ノイズとして除外")
        falsetto_notes = []

    return chest_notes, falsetto_notes


def _classify_frames(filtered: dict, y_16k: np.ndarray, sr_crepe: int,
                     hop_length: int, no_falsetto: bool,
                     already_separated: bool) -> tuple:
    """レジスター判定 → (chest_notes, falsetto_notes)"""
    f0_reg_fixed     = filtered["f0_reg_fixed"]
    f0_reg           = filtered["f0_reg"]
    conf_reg         = filtered["conf_reg"]
    valid_indices_reg = filtered["valid_indices_reg"]
    median_freq      = filtered["median_freq"]

    print(f"\n[STEP 6/7] レジスター判定中...")

    if no_falsetto:
        # === no_falsetto モード: 全フレームを地声として扱う ===
        print(f"[INFO] no_falsetto=True: 裏声判定をスキップし、全フレームを地声として処理")
        chest_notes = [f for f in f0_reg_fixed if VOICE_MIN_HZ <= f <= VOICE_MAX_HZ]
        falsetto_notes = []
        # no_falsettoではレジスター判定がないため、伴奏混入やCREPEオクターブエラーが
        # 全て地声に含まれP97が汚染される。P95を使い、主歌声分布の上端を基準にする。
        chest_notes = remove_statistical_outliers(
            chest_notes,
            percentile=NO_FALSETTO_OUTLIER_PERCENTILE,
            max_semitones_gap=NO_FALSETTO_OUTLIER_GAP_ST,
        )
        chest_notes = remove_isolated_extremes(chest_notes)
        return chest_notes, falsetto_notes

    # === 通常モード: レジスター判定 ===
    chest_notes    = []
    falsetto_data  = []   # (array_index, freq, rms) - フィルタ用に追加情報を保持
    chest_rms      = []   # 地声フレームのRMS値（RMSフィルタ用）
    frame_len      = 2048
    total_frames   = len(f0_reg_fixed)
    progress_interval = max(1, total_frames // 10)

    stats = new_register_stats()
    graduated_conf_filtered = 0
    print(f"[INFO] {total_frames}フレームを処理中...")
    for i in range(total_frames):
        if i % progress_interval == 0 and i > 0:
            progress = (i / total_frames) * 100
            n_falsetto_so_far = len(falsetto_data)
            print(f"[INFO] 進捗: {progress:.0f}% ({i}/{total_frames}) - 地声:{len(chest_notes)} 裏声:{n_falsetto_so_far}")
        freq = f0_reg_fixed[i]
        if not (VOICE_MIN_HZ <= freq <= VOICE_MAX_HZ):
            continue
        # --- 段階的信頼度要求: 中央値から遠いほど高い信頼度を要求 ---
        orig_freq = f0_reg[i]
        if orig_freq > median_freq:
            octaves_above = np.log2(orig_freq / median_freq)
            if octaves_above > 1.5:
                min_conf = GRADUATED_CONF_FAR
            elif octaves_above > 1.0:
                min_conf = GRADUATED_CONF_MID
            else:
                min_conf = GRADUATED_CONF_NEAR
            if conf_reg[i] < min_conf:
                graduated_conf_filtered += 1
                continue
        frame_idx = valid_indices_reg[i]
        center    = int(frame_idx) * hop_length
        start     = max(0, center - frame_len // 2)
        end       = min(len(y_16k), center + frame_len // 2)
        frame     = y_16k[start:end]
        if len(frame) < 512:
            continue
        # フレームのRMSを計算（RMSフィルタ用、計算コスト小）
        frame_rms = float(np.sqrt(np.mean(frame ** 2)))
        try:
            reg = classify_register(
                frame,
                sr_crepe,
                freq,
                median_freq,
                already_separated,
                crepe_conf=float(conf_reg[i]),
                stats=stats,
            )
            if reg == "falsetto":
                falsetto_data.append((i, freq, frame_rms))
            elif reg == "chest":
                chest_notes.append(freq)
                chest_rms.append(frame_rms)
            # reg == "unknown" はスキップ（無声音・異常データ）
        except Exception:
            continue

    print_register_summary(stats)  # レジスター判定のサマリーを出力

    if graduated_conf_filtered > 0:
        print(f"[DEBUG] 段階的信頼度フィルタ: {graduated_conf_filtered}フレーム除外")

    # === 裏声ノイズフィルタ（demucs残留楽器対策） ===
    # フィルタ前のカウントを記録
    falsetto_before_filter = len(falsetto_data)
    print(f"[DEBUG] 裏声ノイズフィルタ開始: 裏声={falsetto_before_filter}フレーム")

    if falsetto_data:
        # フィルタ1: 連続フレーム要件 - 孤立した裏声はノイズ
        falsetto_data = filter_falsetto_consecutive(
            falsetto_data, FALSETTO_MIN_CONSECUTIVE)

        # フィルタ2: RMSパワー - 残留楽器はボーカルより音量が小さい
        falsetto_data = filter_falsetto_rms(
            falsetto_data, chest_rms, FALSETTO_RMS_RATIO)

        # フィルタ3: Silero VAD - フレーム単位で音声スコアを評価し楽器リークを除去
        # ★ Demucs分離後（カラオケモード）のみ適用。
        # マイク録音では除去対象の残留楽器が存在せず、Silero VAD が裏声を
        # 「非音声」と誤判定して正当な裏声フレームを大量に除去してしまうため。
        if already_separated:
            falsetto_data = filter_falsetto_vad(
                falsetto_data, y_16k, valid_indices_reg, hop_length, SILERO_VAD_THRESHOLD)
        else:
            print(f"[DEBUG] VADフィルタ: マイク録音モード（already_separated=False）のためスキップ")

    # falsetto_data → falsetto_notes に変換（周波数リストに戻す）
    falsetto_notes = [item[1] for item in falsetto_data]

    # 裏声表示フィルタ: 330Hz未満の「裏声」は息混じり地声の可能性が高い
    falsetto_orig  = list(falsetto_notes)
    falsetto_notes = [f for f in falsetto_orig if f >= FALSETTO_DISPLAY_MIN_HZ]
    low_falsetto   = [f for f in falsetto_orig if f < FALSETTO_DISPLAY_MIN_HZ]
    chest_notes.extend(low_falsetto)
    if low_falsetto:
        print(f"[DEBUG] {len(low_falsetto)}フレームを裏声→地声に再分類")

    if not chest_notes and not falsetto_notes:
        print(f"[WARN] レジスター判定結果なし。全フレームを地声として処理")
        chest_notes = f0_reg_fixed.tolist()
    else:
        print(f"[DEBUG] レジスター判定直後: 地声={len(chest_notes)}フレーム, 裏声={len(falsetto_notes)}フレーム")

    # デバッグ: 最高音付近（上位10Hz）の判定状況を確認
    if chest_notes or falsetto_notes:
        all_freqs = chest_notes + falsetto_notes
        if all_freqs:
            max_freq = max(all_freqs)
            high_threshold = max_freq - 10
            high_chest = [f for f in chest_notes if f >= high_threshold]
            high_falsetto = [f for f in falsetto_notes if f >= high_threshold]
            print(f"[DEBUG] 最高音付近（{high_threshold:.1f}Hz以上）: 地声{len(high_chest)}フレーム, 裏声{len(high_falsetto)}フレーム")
            if high_chest and high_falsetto:
                print(f"[DEBUG] → 地声最高: {max(high_chest):.1f}Hz, 裏声最高: {max(high_falsetto):.1f}Hz")

    # === 統計的外れ値除去（パーセンタイルベースの安全ネット） ===
    print(f"[DEBUG] フィルタリング前: 地声={len(chest_notes)}, 裏声={len(falsetto_notes)}")
    chest_notes_before = len(chest_notes)
    falsetto_notes_before = len(falsetto_notes)

    chest_notes = remove_statistical_outliers(
        chest_notes,
        percentile=CHEST_OUTLIER_PERCENTILE,
        max_semitones_gap=CHEST_OUTLIER_GAP_ST,
    )
    falsetto_notes = remove_statistical_outliers(
        falsetto_notes,
        percentile=FALSETTO_OUTLIER_PERCENTILE,
        max_semitones_gap=FALSETTO_OUTLIER_GAP_ST,
    )
    print(f"[DEBUG] 統計外れ値除去後: 地声={len(chest_notes)} ({chest_notes_before}→{len(chest_notes)}), 裏声={len(falsetto_notes)} ({falsetto_notes_before}→{len(falsetto_notes)})")

    # === 孤立した極端値を除去（ノイズ最終防衛線） ===
    chest_notes_before = len(chest_notes)
    falsetto_notes_before = len(falsetto_notes)

    chest_notes = remove_isolated_extremes(chest_notes)
    falsetto_notes = remove_isolated_extremes(falsetto_notes)
    print(f"[DEBUG] 孤立フレーム除去後: 地声={len(chest_notes)} ({chest_notes_before}→{len(chest_notes)}), 裏声={len(falsetto_notes)} ({falsetto_notes_before}→{len(falsetto_notes)})")

    # === フィルタ3: 最小比率（外れ値除去後に適用して正確な比率で判定） ===
    # 地声フレームが揃った後に適用することで、裏声2.5%などを正しく弾ける。
    falsetto_pre_ratio_filter = len(falsetto_notes)
    chest_notes, falsetto_notes = filter_falsetto_min_ratio(
        falsetto_notes, chest_notes, FALSETTO_MIN_RATIO)
    if falsetto_pre_ratio_filter != len(falsetto_notes):
        print(f"[DEBUG] 最小比率フィルタ: 裏声 {falsetto_pre_ratio_filter} → {len(falsetto_notes)}フレーム "
              f"({falsetto_pre_ratio_filter - len(falsetto_notes)}フレーム除外)")

    # === 救済フレームの後処理: 孤立フレーム除去を再適用 ===
    # filter_falsetto_min_ratio の救済ロジックで地声に加えられたフレームは
    # 前段の outlier/isolated 除去をスキップしているため、ここで再度適用する。
    # (statistical_outliers の再適用は救済範囲が outlier 閾値内に収まるため不要)
    chest_notes_before_isolated = len(chest_notes)
    chest_notes = remove_isolated_extremes(chest_notes)
    if len(chest_notes) < chest_notes_before_isolated:
        print(f"[DEBUG] 救済後孤立フレーム除去: "
              f"{chest_notes_before_isolated - len(chest_notes)}フレーム削除")

    # === 最高音付近の混在判定を解消 ===
    print(f"[DEBUG] 最高音付近の混在判定前: 地声={len(chest_notes)}, 裏声={len(falsetto_notes)}")
    if chest_notes and falsetto_notes:
        all_freqs = chest_notes + falsetto_notes
        max_freq = max(all_freqs)
        cleanup_factor = 2 ** (CLEANUP_SEMITONES / 12)
        high_range_threshold = max_freq / cleanup_factor

        high_chest_frames = [f for f in chest_notes if f >= high_range_threshold]
        high_falsetto_frames = [f for f in falsetto_notes if f >= high_range_threshold]

        # 両方存在する場合、最高音付近では裏声を優先（高音は裏声で出すのが自然）
        if high_chest_frames and high_falsetto_frames:
            chest_notes = [f for f in chest_notes if f < high_range_threshold]
            print(f"[INFO] 最高音付近の地声{len(high_chest_frames)}フレームを除外（裏声{len(high_falsetto_frames)}フレームを優先採用）")

        # ラベル変換後の安全チェック: 量子化で同じ音名になるケースを防止
        if chest_notes and falsetto_notes:
            f_label, _ = hz_to_label_and_hz(max(falsetto_notes))
            c_label, _ = hz_to_label_and_hz(max(chest_notes))
            if c_label == f_label:
                before_count = len(chest_notes)
                chest_notes = [f for f in chest_notes
                               if hz_to_label_and_hz(f)[0] != f_label]
                removed = before_count - len(chest_notes)
                print(f"[INFO] ラベル一致'{c_label}'の地声{removed}フレームを除外")

    print(f"[DEBUG] 最高音付近の混在判定後: 地声={len(chest_notes)}, 裏声={len(falsetto_notes)}")

    return chest_notes, falsetto_notes


def _build_result(chest_notes: list, falsetto_notes: list,
                  f0_reg_fixed: np.ndarray, conf_reg: np.ndarray) -> dict:
    """結果dict構築 → result"""
    print(f"\n[STEP 7/7] 結果集計中...")

    all_notes   = chest_notes + falsetto_notes
    overall_min = float(np.min(all_notes))
    overall_max = float(np.max(all_notes))
    print(f"[DEBUG] 全体音域: min={overall_min:.1f}Hz max={overall_max:.1f}Hz")

    result = {}
    chest_avg_hz = float(np.mean(chest_notes)) if chest_notes else 0.0

    def add_range(notes, prefix):
        if not notes:
            return
        arr = np.array(notes)
        lo_label, lo_hz = hz_to_label_and_hz(float(np.min(arr)))
        robust_max = _get_robust_max(notes)
        hi_label, hi_hz = hz_to_label_and_hz(float(robust_max))
        raw_max = float(np.max(arr))
        if robust_max < raw_max:
            print(f"[INFO] {prefix} 最高音堅牢化: {raw_max:.1f}Hz → {robust_max:.1f}Hz (持続不足フレームをスキップ)")
        result[f"{prefix}_min"]    = lo_label
        result[f"{prefix}_max"]    = hi_label
        result[f"{prefix}_min_hz"] = lo_hz
        result[f"{prefix}_max_hz"] = hi_hz
        result[f"{prefix}_count"]  = len(arr)

    add_range(chest_notes,    "chest")
    add_range(falsetto_notes, "falsetto")

    # デバッグ: 地声と裏声の最高音Hz値を出力
    if chest_notes and falsetto_notes:
        chest_max_hz = float(np.max(chest_notes))
        falsetto_max_hz = float(np.max(falsetto_notes))
        print(f"[DEBUG] 地声最高音: {chest_max_hz:.1f}Hz, 裏声最高音: {falsetto_max_hz:.1f}Hz")
        if abs(chest_max_hz - falsetto_max_hz) < 5:
            print(f"[WARN] 地声と裏声の最高音が近い（差: {abs(chest_max_hz - falsetto_max_hz):.1f}Hz）")

    ovr_min_label, ovr_min_hz = hz_to_label_and_hz(overall_min)
    ovr_max_label, ovr_max_hz = hz_to_label_and_hz(overall_max)
    result["overall_min"]    = ovr_min_label
    result["overall_max"]    = ovr_max_label
    result["overall_min_hz"] = ovr_min_hz
    result["overall_max_hz"] = ovr_max_hz

    total = len(chest_notes) + len(falsetto_notes)
    result["chest_ratio"]    = round(len(chest_notes)    / total * 100, 1) if total else 100.0
    result["falsetto_ratio"] = round(len(falsetto_notes) / total * 100, 1) if total else 0.0
    result["chest_avg_hz"]   = round(chest_avg_hz, 1)

    # === デバッグ出力 ===
    print(f"[DEBUG] 声区バランス計算:")
    print(f"  地声: {len(chest_notes)}フレーム ({result['chest_ratio']}%)")
    print(f"  裏声: {len(falsetto_notes)}フレーム ({result['falsetto_ratio']}%)")
    print(f"  合計: {total}フレーム")

    # === 歌唱力分析 ===
    try:
        result["singing_analysis"] = analyze_singing_ability(
            f0_array=f0_reg_fixed,
            conf_array=conf_reg,
            chest_notes=chest_notes,
            falsetto_notes=falsetto_notes,
            overall_min_hz=overall_min,
            overall_max_hz=overall_max,
        )
    except Exception as e:
        print(f"[WARN] 歌唱力分析スキップ: {e}")

    print(f"\n{'='*60}")
    print(f"[INFO] 解析完了!")
    print(f"{'='*60}")
    print(f"[INFO] 最終結果:")
    print(f"  全体音域: {result.get('overall_min', 'N/A')} - {result.get('overall_max', 'N/A')}")
    if 'chest_min' in result:
        print(f"  地声音域: {result.get('chest_min', 'N/A')} - {result.get('chest_max', 'N/A')} ({result.get('chest_ratio', 0)}%)")
    if 'falsetto_min' in result:
        print(f"  裏声音域: {result.get('falsetto_min', 'N/A')} - {result.get('falsetto_max', 'N/A')} ({result.get('falsetto_ratio', 0)}%)")
    print(f"{'='*60}\n")
    return result


# ============================================================
# analyze — オーケストレータ
# ============================================================
def analyze(wav_path: str, already_separated: bool = False, no_falsetto: bool = False) -> dict:
    audio = _load_audio(wav_path)
    if "error" in audio:
        return audio

    prep = _preprocess(audio["y"], audio["sr"])

    pitch = _run_pitch_detection(prep["audio_tensor"], prep["sr_crepe"],
                                 prep["hop_length"], prep["device"])
    if "error" in pitch:
        return pitch

    filtered = _filter_frames(pitch["f0"], pitch["conf"])
    if "error" in filtered:
        return filtered

    chest, falsetto = _classify_frames(
        filtered, prep["y_16k"], prep["sr_crepe"],
        prep["hop_length"], no_falsetto, already_separated,
    )

    return _build_result(chest, falsetto, filtered["f0_reg_fixed"], filtered["conf_reg"])
