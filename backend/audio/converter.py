import os
import shutil
import subprocess
import uuid

def find_ffmpeg():
    """ffmpegの実行パスを探す"""
    path = shutil.which("ffmpeg")
    if path: return path

    candidates = [
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/usr/bin/ffmpeg"
    ]
    for p in candidates:
        if os.path.exists(p) and os.access(p, os.X_OK):
            return p
    return None

def _run_ffmpeg(cmd: list, input_path: str, output_path: str):
    """ffmpegコマンドを実行する共通関数"""
    ffmpeg_bin = find_ffmpeg()
    if not ffmpeg_bin:
        raise RuntimeError("ffmpegが見つかりません。brew install ffmpegを実行してください。")

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"入力ファイルが見つかりません: {input_path}")

    print(f"[INFO] Converting: {input_path} -> {output_path}")
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else "Unknown error"
        print(f"[ERROR] FFmpeg conversion failed: {error_msg}")
        raise RuntimeError(f"音声変換に失敗しました: {error_msg}")

    if not os.path.exists(output_path):
        raise RuntimeError("変換後のファイルが生成されませんでした。")

    return output_path


def convert_to_wav(input_path: str, output_dir: str = "uploads") -> str:
    """
    マイク録音・アカペラ解析用: 16kHz・モノラルに変換
    (CREPE解析専用。Demucsには使わないこと)
    """
    ffmpeg_bin = find_ffmpeg()
    filename = os.path.basename(input_path)
    name_without_ext = os.path.splitext(filename)[0]
    output_filename = f"{name_without_ext}_{uuid.uuid4().hex[:8]}.wav"
    output_path = os.path.join(output_dir, output_filename)

    cmd = [
        ffmpeg_bin, "-y",
        "-i", input_path,
        "-vn",
        "-ar", "16000",   # CREPEは16kHzで十分
        "-ac", "1",        # モノラル
        output_path
    ]
    return _run_ffmpeg(cmd, input_path, output_path)


def convert_to_wav_hq(input_path: str, output_dir: str = "uploads") -> str:
    """
    Demucs（ボーカル分離）前処理用: 44100Hz・ステレオに変換
    Demucsは高品質なステレオ音声を必要とする。
    16kHz/モノラルだとボーカル分離の精度が大幅に低下する。
    """
    ffmpeg_bin = find_ffmpeg()
    filename = os.path.basename(input_path)
    name_without_ext = os.path.splitext(filename)[0]
    output_filename = f"{name_without_ext}_hq_{uuid.uuid4().hex[:8]}.wav"
    output_path = os.path.join(output_dir, output_filename)

    cmd = [
        ffmpeg_bin, "-y",
        "-i", input_path,
        "-vn",
        "-ar", "44100",   # Demucsが期待するサンプリングレート
        "-ac", "2",        # ステレオ（Demucsはステレオで最適に動作）
        "-sample_fmt", "s16",  # 16bit PCM
        output_path
    ]
    return _run_ffmpeg(cmd, input_path, output_path)
