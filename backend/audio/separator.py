"""
audio/separator.py — MelBandRoformers によるボーカル分離

audio-separator ライブラリ経由で MelBandRoformers モデルを使用し、
カラオケ音源からボーカルトラックを分離する。
"""

from __future__ import annotations

import os
import shutil
import threading
from pathlib import Path

from config import CONVERTER_HQ_SR

_MODEL_FILENAME_CANDIDATES: list[str] = [
    # audio-separator 同梱モデル（取得先メタデータを内部管理）
    "vocals_mel_band_roformer.ckpt",
    # 互換候補
    "mel_band_roformer_karaoke_gabox_v2.ckpt",
    "mel_band_roformer_karaoke_gabox.ckpt",
]
_MELBAND_LOCAL_DIR = Path(
    os.getenv(
        "MELBAND_MODEL_DIR",
        str(Path.home() / ".cache" / "pitchscout" / "melbandroformers"),
    )
)

# モデルの再ダウンロード・再初期化を避けるためのシングルトン
_SEPARATOR_INSTANCE = None
_SEPARATOR_LOCK = threading.Lock()


def _resolve_model_candidates() -> list[str]:
    """
    環境変数オーバーライドを含む候補モデル名を返す。

    MELBAND_MODEL_FILENAME 環境変数が設定されていれば最優先候補として先頭に追加する。

    Returns:
        試行するモデルファイル名のリスト（優先順）。
    """
    override = os.getenv("MELBAND_MODEL_FILENAME", "").strip()
    if override:
        return [override, *_MODEL_FILENAME_CANDIDATES]
    return list(_MODEL_FILENAME_CANDIDATES)


def _load_model_once(separator: object) -> None:
    """
    Separator にモデルをロードする。

    候補モデル名を順に試行し、最初に成功したものを採用する。

    Args:
        separator: audio-separator の Separator インスタンス。

    Raises:
        RuntimeError: 全候補モデルのロードに失敗した場合。
    """
    last_error: Exception | None = None

    for model_filename in _resolve_model_candidates():
        try:
            try:
                separator.load_model(model_filename=model_filename)
            except TypeError:
                # audio-separator のバージョン差異でキーワード引数がない場合に備える。
                separator.load_model(model_filename)

            print(f"[INFO] Loaded model: {model_filename}")
            return
        except Exception as exc:
            last_error = exc
            print(f"[WARN] モデル読込失敗: {model_filename} ({exc})")

    raise RuntimeError(f"利用可能モデルが見つかりません: {last_error}")


def _get_separator(output_dir: str, model_file_dir: str) -> object:
    """
    モデルロード済み Separator を返す（初回のみ重い初期化を実行）。

    スレッドセーフなシングルトンパターンで、複数リクエストからの同時呼び出しに対応する。
    2回目以降は output_dir のみ差し替えてキャッシュ済みインスタンスを返す。

    Args:
        output_dir: 分離結果の出力ディレクトリ。
        model_file_dir: モデルファイルの保存ディレクトリ。

    Returns:
        audio-separator の Separator インスタンス。
    """
    global _SEPARATOR_INSTANCE

    with _SEPARATOR_LOCK:
        if _SEPARATOR_INSTANCE is None:
            _SEPARATOR_INSTANCE = _load_separator(output_dir=output_dir, model_file_dir=model_file_dir)
            _load_model_once(_SEPARATOR_INSTANCE)
        else:
            # リクエストごとの出力先に切り替える
            if hasattr(_SEPARATOR_INSTANCE, "output_dir"):
                _SEPARATOR_INSTANCE.output_dir = output_dir

    return _SEPARATOR_INSTANCE


def _load_separator(output_dir: str, model_file_dir: str) -> object:
    """
    audio-separator の Separator を新規生成する。

    Args:
        output_dir: 分離結果の出力ディレクトリ。
        model_file_dir: モデルファイルの保存ディレクトリ。

    Returns:
        audio-separator の Separator インスタンス。

    Raises:
        RuntimeError: audio-separator パッケージが見つからない場合。
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
        sample_rate=CONVERTER_HQ_SR,
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


def _resolve_output_path(vocal_path: str, output_dir: str, input_wav_path: str) -> Path:
    """audio-separator の返却値を実在する絶対パスへ解決する。"""
    candidate = Path(vocal_path)
    if candidate.exists():
        return candidate

    # 追加: ライブラリ内部の出力先差異を吸収するため、複数候補ディレクトリを順に探索する。
    search_dirs: list[Path] = [
        Path(output_dir),
        Path(input_wav_path).parent,
        Path.cwd(),
        Path(output_dir).parent,
    ]

    for search_dir in search_dirs:
        direct_path = search_dir / candidate.name
        if direct_path.exists():
            return direct_path

        matches = list(search_dir.glob(f"**/{candidate.name}"))
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
    model_file_dir = str(_MELBAND_LOCAL_DIR.resolve())
    separator = _get_separator(output_dir=output_dir, model_file_dir=model_file_dir)
    # 追加: シングルトン再利用時に実際に設定されている出力先を優先して解決に使う。
    effective_output_dir = str(getattr(separator, "output_dir", output_dir))

    output_files: list[str] | str | None = None

    try:
        output_files = separator.separate(str(input_file))
    except Exception as exc:
        raise RuntimeError(f"MelBandRoformers 分離に失敗しました: {exc}") from exc

    vocal_path = _pick_vocals_file(output_files)
    resolved_path = _resolve_output_path(
        vocal_path=vocal_path,
        output_dir=effective_output_dir,
        input_wav_path=input_wav_path,
    )

    if not resolved_path.exists():
        raise RuntimeError(f"分離後のボーカルファイルが見つかりません: {vocal_path}")

    # 互換性のため、リクエストごとの output_dir 配下に必ず vocals.wav を用意する。
    canonical_path = Path(output_dir) / "vocals.wav"
    if resolved_path.resolve() != canonical_path.resolve():
        shutil.copy2(resolved_path, canonical_path)
        resolved_path = canonical_path

    print(f"[INFO] Separation complete: {resolved_path}")
    return str(resolved_path)
