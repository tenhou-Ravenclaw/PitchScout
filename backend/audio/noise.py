"""
audio/noise.py — ノイズ除去

DeepFilterNet3 によるニューラルネットワークノイズ除去（MelBandRoformers 分離後に適用）と、
従来の noisereduce ベース関数（フォールバック用）を提供する。
Silero VAD も本モジュールで初期化・提供する。
"""
from __future__ import annotations

import threading
import time
from typing import Callable

import numpy as np
import soundfile as sf
import torch
import torchaudio
import librosa
import noisereduce as nr

from config import VAD_CHUNK_SIZE

# ============================================================
# Silero VAD シングルトン（モジュールレベル）
# main.py の lifespan で init_silero_vad() を呼び起動時に初期化する。
# ============================================================
_vad_model: torch.nn.Module | None = None
_vad_get_timestamps: Callable | None = None
_vad_lock = threading.Lock()  # 遅延初期化の競合状態を防止
_vad_fallback_warned = False   # 未初期化フォールバック警告を一度だけ出すためのフラグ


def init_silero_vad() -> bool:
    """
    Silero VAD モデルを初期化する。

    アプリ起動時に 1 回だけ呼び出すこと。torch.hub 経由でモデルをロードする
    （初回のみダウンロード、以降は ~/.cache/torch/hub/ のキャッシュを使用）。
    失敗した場合は警告を出力して False を返す（アプリは継続起動する）。

    Returns:
        初期化に成功した場合 True、失敗した場合 False。
    """
    global _vad_model, _vad_get_timestamps
    try:
        t0 = time.time()
        print("[INFO] Silero VAD モデルを初期化中...")
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            verbose=False,
        )
        get_speech_timestamps, *_ = utils
        _vad_model = model
        _vad_get_timestamps = get_speech_timestamps
        print(f"[INFO] Silero VAD 初期化完了 ({time.time() - t0:.1f}s)")
        return True
    except Exception as e:
        print(f"[WARN] Silero VAD 初期化失敗 (フィルタをスキップ): {e}")
        return False


def score_frame_vad(frame: np.ndarray, sr: int = 16000) -> float:
    """
    1フレームの音声らしさスコア (0.0-1.0) を返す。

    Silero VAD が期待する 512 サンプル (32ms) チャンクに分割し、
    最大スコアを返す（フレーム内に少しでも歌声があれば保持するため max を使う）。

    楽器ハーモニクスと歌声の違い:
      - 楽器リーク: 周期的・単調な倍音構造 → VAD スコアが低くなりやすい
      - 歌声: フォルマント遷移・ビブラート・子音を含む → VAD スコアが高くなる

    モデル未初期化の場合は 1.0 を返してフィルタをスキップする（フォールバック）。

    Args:
        frame: 16kHz モノラル音声フレームの numpy 配列。
        sr: サンプリングレート（16000 固定）。

    Returns:
        0.0-1.0 の音声確率スコア。
    """
    global _vad_fallback_warned
    if _vad_model is None:
        # 未初期化時は一度だけ警告を出してフィルタを無効化する。
        # 毎フレーム出力するとログが膨大になるため初回のみ。
        if not _vad_fallback_warned:
            print("[WARN] Silero VAD が初期化されていません — 裏声ノイズフィルタが無効です")
            _vad_fallback_warned = True
        return 1.0  # モデル未初期化: 全フレームを音声とみなしフィルタを無効化

    chunk_size = VAD_CHUNK_SIZE  # Silero VAD が期待するチャンクサイズ (16kHz で 32ms)
    scores: list[float] = []

    for start in range(0, len(frame), chunk_size):
        chunk = frame[start : start + chunk_size]
        if len(chunk) < chunk_size:
            # 末尾が足りない場合はゼロパディング
            chunk = np.pad(chunk, (0, chunk_size - len(chunk)))
        try:
            chunk_tensor = torch.FloatTensor(chunk).unsqueeze(0)
            with torch.no_grad():
                scores.append(float(_vad_model(chunk_tensor, sr)))
        except Exception as exc:
            print(f"[WARN] VAD チャンク推論失敗（スキップ）: {exc}")
            continue

    return max(scores) if scores else 1.0


# ============================================================
# DeepFilterNet シングルトン（モジュールレベル）
# main.py の lifespan で init_deepfilter() を呼び起動時に初期化する。
# ============================================================
_df_model: object | None = None
_df_state: object | None = None
_df_lock = threading.Lock()  # 遅延初期化の競合状態を防止


def init_deepfilter() -> bool:
    """
    DeepFilterNet3 のモデルを初期化する。

    アプリ起動時に 1 回だけ呼び出すこと（init_df が重いため）。
    失敗した場合は警告を出力して False を返す（アプリは継続起動する）。

    Returns:
        初期化に成功した場合 True、失敗した場合 False。
    """
    global _df_model, _df_state
    try:
        from df.enhance import init_df
        t0 = time.time()
        print("[INFO] DeepFilterNet モデルを初期化中...")
        _df_model, _df_state, _ = init_df()
        print(f"[INFO] DeepFilterNet 初期化完了 ({time.time() - t0:.1f}s)")
        return True
    except Exception as e:
        print(f"[WARN] DeepFilterNet 初期化失敗 (音声解析は継続): {e}")
        return False


def apply_deepfilter(
    input_wav_path: str,
    output_wav_path: str | None = None,
    attenuation_limit_db: int = 20,
) -> str:
    """
    DeepFilterNet3 で MelBandRoformers 分離後の残留ノイズを除去する。

    サンプリングレートの変換フロー:
      MelBandRoformers 出力 (44.1kHz) → 48kHz にリサンプル → DeepFilterNet 処理 →
      48kHz のまま保存 → WORLD パイプラインが内部で 16kHz にリサンプル

    エラー時はフォールバックとして input_wav_path をそのまま返す。

    Args:
        input_wav_path: MelBandRoformers が出力したボーカル WAV のパス (44.1kHz 想定)。
        output_wav_path: 出力先パス。省略時は input と同ディレクトリに
                         {stem}_dfn.wav として保存する。
        attenuation_limit_db: ノイズ減衰上限 (dB)。config.DFN_ATTENUATION_LIMIT_DB を渡す。
                               大きいほど除去量が増えるが音質リスクも上がる。

    Returns:
        処理後の WAV ファイルパス。失敗時は input_wav_path をそのまま返す。
    """
    global _df_model, _df_state

    if output_wav_path is None:
        base = input_wav_path.rsplit(".", 1)[0]
        output_wav_path = f"{base}_dfn.wav"

    # モデル未初期化の場合は遅延初期化（フォールバック）
    # Lock により複数スレッドが同時に init_deepfilter() を呼ぶ競合を防止する。
    if _df_model is None or _df_state is None:
        with _df_lock:
            # ロック取得後に再確認（別スレッドが先に初期化した可能性）
            if _df_model is None or _df_state is None:
                if not init_deepfilter():
                    print("[WARN] DeepFilterNet 利用不可 — 分離後音声をそのまま使用します")
                    return input_wav_path

    t0 = time.time()
    try:
        from df.enhance import enhance

        # torchaudio で WAV 読み込み（shape: [C, T]）
        audio, sr = torchaudio.load(input_wav_path)

        # ステレオ → モノラル変換（DeepFilterNet はモノラル推奨）
        if audio.shape[0] > 1:
            audio = audio.mean(dim=0, keepdim=True)

        # 48kHz にリサンプル（DeepFilterNet3 の期待 SR）
        target_sr: int = _df_state.sr()  # 通常 48000
        if sr != target_sr:
            resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=target_sr)
            audio = resampler(audio)

        # 推論（torch.no_grad() でメモリリーク防止）
        with torch.no_grad():
            enhanced: torch.Tensor = enhance(
                _df_model,
                _df_state,
                audio,
                atten_lim_db=attenuation_limit_db,
            )

        # shape が 1D の場合は 2D に戻して保存
        if enhanced.dim() == 1:
            enhanced = enhanced.unsqueeze(0)

        torchaudio.save(output_wav_path, enhanced, target_sr)

        elapsed = time.time() - t0
        print(f"[INFO] DeepFilterNet 完了 ({elapsed:.1f}s): {output_wav_path}")
        return output_wav_path

    except Exception as e:
        print(f"[WARN] DeepFilterNet 処理失敗 ({e}) — 分離後音声をそのまま使用します")
        return input_wav_path


def reduce_noise_light(file_path: str, output_path: str = "cleaned.wav") -> str:
    """
    MelBandRoformers 分離後の残留楽器音を軽く除去する。

    ポイント:
      - prop_decrease=0.5 (50%除去): ボーカルを壊さない程度に抑える
      - librosa.effects.splitは使わない: 小さな声のフレーズを切らない
      - stationary=False: 非定常ノイズ(楽器の残留)にも対応

    現在は DeepFilterNet (apply_deepfilter) を優先使用しており、
    本関数はフォールバック・互換用として残している。
    """
    y, sr = librosa.load(file_path, sr=None, mono=True)

    y_denoised = nr.reduce_noise(
        y=y,
        sr=sr,
        prop_decrease=0.5,
        stationary=False,
        n_fft=2048,
        hop_length=512,
    )

    sf.write(output_path, y_denoised, sr)
    return output_path


def reduce_noise(file_path: str, output_path: str = "cleaned.wav") -> str:
    """
    通常のノイズ除去（マイク録音用）。
    現在は使用していないが互換性のため残す。
    """
    y, sr = librosa.load(file_path, sr=None, mono=True)

    y_denoised = nr.reduce_noise(
        y=y,
        sr=sr,
        prop_decrease=0.8,
        n_fft=2048,
        hop_length=512,
    )

    intervals = librosa.effects.split(y_denoised, top_db=30)
    if len(intervals) == 0:
        sf.write(output_path, y_denoised, sr)
        return output_path

    y_trimmed = np.concatenate([y_denoised[start:end] for start, end in intervals])
    sf.write(output_path, y_trimmed, sr)
    return output_path
