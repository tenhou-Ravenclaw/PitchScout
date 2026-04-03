"""
audio/separator.py — MelBandRoformers によるボーカル分離

Demucs 依存を廃止し、MelBandRoformers (voc_fv6.ckpt) を利用する。
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

_MODEL_FILENAME_CANDIDATES: list[str] = [
    # audio-separator 同梱モデル（取得先メタデータを内部管理）
    "vocals_mel_band_roformer.ckpt",
    # 互換候補
    "mel_band_roformer_karaoke_gabox_v2.ckpt",
    "mel_band_roformer_karaoke_gabox.ckpt",
]
_MELBAND_LOCAL_DIR = Path("melbandroformers")


def _resolve_model_candidates() -> list[str]:
    """環境変数オーバーライドを含む候補モデル名を返す。"""
    override = os.getenv("MELBAND_MODEL_FILENAME", "").strip()
    if override:
        return [override, *_MODEL_FILENAME_CANDIDATES]
    return list(_MODEL_FILENAME_CANDIDATES)


def _load_separator(output_dir: str, model_file_dir: str):
    """
    audio-separator の Separator をロードする。

    Returns:
        Separator インスタンス。

    Raises:
        RuntimeError: 依存が不足している場合。
    """
    try:
        from audio_separator.separator import Separator
    except Exception as exc:
        raise RuntimeError(
            "audio-separator が見つかりません。'pip install audio-separator[cpu]' を実行してください。"
        ) from exc

    return Separator(
        output_dir=output_dir,
        output_format="WAV",
        output_single_stem="Vocals",
        model_file_dir=model_file_dir,
        sample_rate=44100,
    )


def _pick_vocals_file(output_files: list[str] | str) -> str:
    """分離結果から Vocals トラックを優先的に選択する。"""
    if isinstance(output_files, str):
        return output_files

    if not output_files:
        raise RuntimeError("MelBandRoformers の出力ファイルが空です")

    for path in output_files:
        name = Path(path).name.lower()
        if "vocal" in name:
            return path

    return output_files[0]


def _resolve_output_path(vocal_path: str, output_dir: str) -> Path:
    """audio-separator の返却値を実在する絶対パスへ解決する。"""
    candidate = Path(vocal_path)
    if candidate.exists():
        return candidate

    # audio-separator は相対ファイル名のみ返す場合があるため output_dir 基準で探索する。
    in_output_dir = Path(output_dir) / candidate.name
    if in_output_dir.exists():
        return in_output_dir

    # 念のため出力ディレクトリ配下を再帰検索する。
    matches = list(Path(output_dir).glob(f"**/{candidate.name}"))
    if matches:
        return matches[0]

    return candidate


def separate_vocals(
    input_wav_path: str,
    output_dir: str = "separated",
    fast_mode: bool = False,
    ultra_fast_mode: bool = False,
) -> str:
    """
    MelBandRoformers (voc_fv6.ckpt) を使ってボーカル分離を行う。

    Args:
        input_wav_path: 入力 WAV ファイルのパス。
        output_dir: 出力ディレクトリ。
        fast_mode: 互換引数（未使用）。
        ultra_fast_mode: 互換引数（未使用）。

    Returns:
        分離後ボーカル WAV のパス。

    Raises:
        FileNotFoundError: 入力ファイルが存在しない場合。
        RuntimeError: モデル取得・分離処理に失敗した場合。
    """
    del fast_mode, ultra_fast_mode

    input_file = Path(input_wav_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_wav_path}")

    os.makedirs(output_dir, exist_ok=True)

    print(f"[INFO] Starting MelBandRoformers separation for: {input_wav_path}")
    os.makedirs(_MELBAND_LOCAL_DIR, exist_ok=True)
    model_file_dir = str(_MELBAND_LOCAL_DIR)

    separator = _load_separator(output_dir=output_dir, model_file_dir=model_file_dir)

    output_files: list[str] | str | None = None
    last_error: Exception | None = None

    try:
        for model_filename in _resolve_model_candidates():
            try:
                try:
                    separator.load_model(model_filename=model_filename)
                except TypeError:
                    # audio-separator のバージョン差異でキーワード引数がない場合に備える。
                    separator.load_model(model_filename)

                print(f"[INFO] Loaded model: {model_filename}")
                output_files = separator.separate(str(input_file))
                break
            except Exception as exc:
                last_error = exc
                print(f"[WARN] モデル読込失敗: {model_filename} ({exc})")

        if output_files is None:
            raise RuntimeError(f"利用可能モデルが見つかりません: {last_error}")
    except Exception as exc:
        raise RuntimeError(f"MelBandRoformers 分離に失敗しました: {exc}") from exc

    vocal_path = _pick_vocals_file(output_files)
    resolved_path = _resolve_output_path(vocal_path=vocal_path, output_dir=output_dir)

    if not resolved_path.exists():
        raise RuntimeError(f"分離後のボーカルファイルが見つかりません: {vocal_path}")

    # 互換性のため、リクエストごとの output_dir 配下に必ず vocals.wav を用意する。
    canonical_path = Path(output_dir) / "vocals.wav"
    if resolved_path.resolve() != canonical_path.resolve():
        shutil.copy2(resolved_path, canonical_path)
        resolved_path = canonical_path

    print(f"[INFO] Separation complete: {resolved_path}")
    return str(resolved_path)
