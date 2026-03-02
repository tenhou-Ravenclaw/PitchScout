import numpy as np
import librosa
import noisereduce as nr
import soundfile as sf


def reduce_noise_light(file_path: str, output_path: str = "cleaned.wav") -> str:
    """
    Demucs分離後の残留楽器音を軽く除去する。

    ポイント:
      - prop_decrease=0.5 (50%除去): ボーカルを壊さない程度に抑える
      - librosa.effects.splitは使わない: 小さな声のフレーズを切らない
      - stationary=False: 非定常ノイズ(楽器の残留)にも対応
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
