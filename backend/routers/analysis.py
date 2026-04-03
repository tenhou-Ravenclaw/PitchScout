"""
音声解析エンドポイント
- POST /analyze      (アカペラ/マイク録音用、Demucsなし)
- POST /analyze-karaoke (カラオケ音源用、Demucsあり)
"""
import os
import shutil
import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
import soundfile as sf

from audio.converter import convert_to_wav, convert_to_wav_hq
from analysis import analyze
from audio.separator import separate_vocals
from audio.noise import apply_deepfilter
from config import DFN_ATTENUATION_LIMIT_DB
from recommender import recommend_songs, find_similar_artists, classify_voice_type
from db.users import (
    get_favorite_artist_ids,
    create_analysis_record,
    update_vocal_range,
)
from auth import get_optional_user

router = APIRouter(tags=["analysis"])

# ── ファイル管理 ───────────────────────────────────────────────
UPLOAD_DIR = "uploads"
SEPARATED_DIR = "separated"
DEBUG_DIR = "debugfile"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SEPARATED_DIR, exist_ok=True)
os.makedirs(DEBUG_DIR, exist_ok=True)

ALLOWED_MIME_BY_EXT: dict[str, set[str]] = {
    ".wav": {"audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave"},
    ".mp3": {"audio/mpeg", "audio/mp3"},
    ".m4a": {"audio/mp4", "audio/x-m4a"},
    ".flac": {"audio/flac", "audio/x-flac"},
    ".webm": {"audio/webm", "video/webm"},
    ".aac": {"audio/aac", "audio/x-aac"},
    ".ogg": {"audio/ogg", "application/ogg"},
    ".wma": {"audio/x-ms-wma", "audio/wma"},
    ".mp4": {"audio/mp4", "video/mp4"},
    ".mov": {"video/quicktime"},
}

# マジックバイト検証テーブル: (シグネチャ, バイトオフセット, 対応拡張子セット)
# Content-Type スプーフィングによる不正ファイルアップロードを防ぐ。
# WAV/MP3/FLAC/OGG/WebM/MP4系のみ検証可能。WMA/AAC はシグネチャが不統一のため除外。
_MAGIC_SIGNATURES: list[tuple[bytes, int, set[str]]] = [
    (b"ID3",               0, {".mp3"}),
    (b"\xff\xfb",          0, {".mp3"}),   # MPEG Layer3 フレーム同期
    (b"\xff\xf3",          0, {".mp3"}),
    (b"\xff\xfa",          0, {".mp3"}),
    (b"fLaC",              0, {".flac"}),
    (b"OggS",              0, {".ogg"}),
    (b"\x1a\x45\xdf\xa3", 0, {".webm"}),  # EBML ヘッダ
    (b"ftyp",              4, {".mp4", ".m4a", ".mov"}),  # ISO Base Media
]
# マジックバイトを確認できる拡張子（それ以外は MIME チェックのみ）
_MAGIC_CHECKABLE_EXTS: set[str] = {ext for _, _, exts in _MAGIC_SIGNATURES for ext in exts}
# WAV は RIFF + WAVE の二重チェックが必要なため個別処理
_MAGIC_CHECKABLE_EXTS.add(".wav")


async def _validate_upload_file(file: UploadFile) -> None:
    """
    アップロードファイルの拡張子・MIME・マジックバイトを検証する。

    WAV は RIFF ヘッダ（bytes 0-3）と WAVE サブタイプ（bytes 8-11）の
    両方を確認する。その他のフォーマットは先頭シグネチャのみ。
    WMA・AAC はシグネチャが不統一なため MIME チェックのみ実施。

    Raises:
        HTTPException(400): ファイル名なし・非対応形式・MIME不一致・マジック不一致。
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="ファイル名が不正です")

    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in ALLOWED_MIME_BY_EXT:
        raise HTTPException(status_code=400, detail="対応していないファイル形式です")

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_MIME_BY_EXT[ext]:
        raise HTTPException(status_code=400, detail="ファイル形式とMIMEタイプが一致しません")

    # マジックバイト検証: ヘッダを先読みしてシグネチャ確認後、ファイルポインタを先頭に戻す
    if ext in _MAGIC_CHECKABLE_EXTS:
        header = await file.read(12)
        await file.seek(0)

        if ext == ".wav":
            # WAV: bytes[0:4]=="RIFF" かつ bytes[8:12]=="WAVE"
            if header[0:4] != b"RIFF" or header[8:12] != b"WAVE":
                raise HTTPException(status_code=400, detail="ファイルの内容が拡張子と一致しません")
        else:
            matched = any(
                header[offset: offset + len(sig)] == sig
                for sig, offset, exts in _MAGIC_SIGNATURES
                if ext in exts
            )
            if not matched:
                raise HTTPException(status_code=400, detail="ファイルの内容が拡張子と一致しません")


def cleanup_files(*paths: str | None) -> None:
    """一時ファイル・ディレクトリを削除するバックグラウンドタスク"""
    for path in paths:
        if not path:
            continue
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except Exception as e:
            print(f"[WARN] Cleanup failed for {path}: {e}")


def _save_debug_outputs(
    source_wav_path: str,
    result: dict,
    request_id: str,
    clip_window_sec: float = 1.0,
) -> list[str]:
    """デバッグ用に分離後音源と最低/最高音クリップを保存する。"""
    saved_paths: list[str] = []

    if not os.path.exists(source_wav_path):
        return saved_paths

    os.makedirs(DEBUG_DIR, exist_ok=True)

    separated_copy_path = os.path.join(DEBUG_DIR, f"{request_id}_separated_vocals.wav")
    shutil.copy2(source_wav_path, separated_copy_path)
    saved_paths.append(separated_copy_path)

    min_sec = result.get("debug_overall_min_sec")
    max_sec = result.get("debug_overall_max_sec")
    if min_sec is None or max_sec is None:
        return saved_paths

    try:
        audio, sr = sf.read(source_wav_path)
        total_samples = len(audio)
        if total_samples <= 0:
            return saved_paths

        def _clip_and_save(center_sec: float, suffix: str) -> str:
            center = float(center_sec)
            start_sec = max(0.0, center - clip_window_sec)
            end_sec = min(total_samples / float(sr), center + clip_window_sec)
            start_idx = int(start_sec * sr)
            end_idx = max(start_idx + 1, int(end_sec * sr))

            clip = audio[start_idx:end_idx]
            out_path = os.path.join(DEBUG_DIR, f"{request_id}_{suffix}.wav")
            sf.write(out_path, clip, sr)
            return out_path

        low_path = _clip_and_save(float(min_sec), "lowest")
        high_path = _clip_and_save(float(max_sec), "highest")
        saved_paths.extend([low_path, high_path])
    except Exception as exc:
        print(f"[WARN] デバッグ音声保存に失敗: {exc}")

    return saved_paths


def _enrich_result(result: dict, user: dict | None = None) -> dict:
    """解析結果におすすめ曲・似てるアーティスト・声質タイプを追加"""
    if "error" in result:
        return result

    chest_min_hz = result.get("chest_min_hz", 0)
    chest_max_hz = result.get("chest_max_hz", 0)
    chest_avg_hz = result.get("chest_avg_hz", 0)
    falsetto_max_hz = result.get("falsetto_max_hz")

    result.setdefault("recommended_songs", [])
    result.setdefault("similar_artists", [])
    result.setdefault("voice_type", {})

    if chest_min_hz > 0 and chest_max_hz > 0:
        # ログイン済みならお気に入りアーティストIDを取得
        fav_ids: list[int] = []
        if user:
            try:
                fav_ids = get_favorite_artist_ids(user["id"])
            except Exception as e:
                print(f"[WARN] お気に入りアーティストID取得失敗: {e}")

        try:
            result["recommended_songs"] = recommend_songs(
                chest_min_hz, chest_max_hz, chest_avg_hz, falsetto_max_hz,
                limit=10, favorite_artist_ids=fav_ids,
            )
        except Exception as e:
            print(f"[WARN] おすすめ曲取得失敗: {e}")

        try:
            result["similar_artists"] = find_similar_artists(
                chest_min_hz, chest_max_hz, chest_avg_hz, limit=5
            )
        except Exception as e:
            print(f"[WARN] 似てるアーティスト取得失敗: {e}")

        try:
            result["voice_type"] = classify_voice_type(
                chest_min_hz, chest_max_hz, chest_avg_hz,
                falsetto_max_hz,
                result.get("chest_ratio", 100.0),
            )
        except Exception as e:
            print(f"[WARN] 声質タイプ判定失敗: {e}")

    return result


def _auto_save_analysis(
    user: dict | None,
    result: dict,
    source_type: str,
    file_name: str | None,
) -> None:
    """解析結果をログイン済みユーザーの履歴に保存し、声域プロファイルを更新する"""
    if not user or result.get("error"):
        return
    try:
        create_analysis_record(
            user_id=user["id"],
            vocal_min=result.get("overall_min"),
            vocal_max=result.get("overall_max"),
            falsetto=result.get("falsetto_max"),
            source_type=source_type,
            file_name=file_name,
            result_json=jsonable_encoder(result),
        )
        update_vocal_range(
            user["id"],
            result.get("overall_min"),
            result.get("overall_max"),
            result.get("falsetto_max"),
        )
    except Exception as e:
        print(f"[WARN] 履歴保存失敗: {e}")


# ============================================================
# 音声解析エンドポイント（認証オプショナル）
# ============================================================

@router.post("/analyze")
async def analyze_voice(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    no_falsetto: bool = Form(False),
    user: dict | None = Depends(get_optional_user),
):
    """アカペラ/マイク録音用 (Demucsなし)。ログイン済みなら履歴に自動保存"""
    start_time = time.time()
    print(f"\n{'#'*60}")
    print(f"[API] アカペラ音源分析リクエスト受信: {file.filename}")
    print(f"{'#'*60}")

    temp_input_path = None
    converted_wav_path = None

    try:
        await _validate_upload_file(file)

        print(f"[API] [1/3] ファイル保存中...")
        # _validate_upload_file() 通過後は必ず有効な拡張子が取れる（空文字は 400 で弾かれる）
        ext = os.path.splitext(file.filename or "")[1]
        temp_input_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{ext}")

        with open(temp_input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"[API] [1/3] 保存完了: {temp_input_path}")

        print(f"\n[API] [2/3] WAV変換中...")
        converted_wav_path = convert_to_wav(temp_input_path, output_dir=UPLOAD_DIR)
        print(f"[API] [2/3] 変換完了: {converted_wav_path}")

        print(f"\n[API] [3/3] 音域解析実行中...")
        result = analyze(converted_wav_path, no_falsetto=no_falsetto)
        if "error" in result:
            raise HTTPException(status_code=422, detail=result["error"])
        result = _enrich_result(result, user)
        _auto_save_analysis(user, result, "microphone", file.filename)

        elapsed_time = time.time() - start_time
        print(f"\n[API] アカペラ音源分析完了 (処理時間: {elapsed_time:.2f}秒)")
        print(f"{'#'*60}\n")

        background_tasks.add_task(cleanup_files, temp_input_path, converted_wav_path)
        return result

    except HTTPException:
        background_tasks.add_task(cleanup_files, temp_input_path, converted_wav_path)
        raise
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"[ERROR] [API] アカペラ音源分析エラー: {e} (経過時間: {elapsed_time:.2f}秒)")
        background_tasks.add_task(cleanup_files, temp_input_path, converted_wav_path)
        raise HTTPException(status_code=500, detail="音声解析中にエラーが発生しました")


@router.post("/analyze-karaoke")
async def analyze_karaoke(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    no_falsetto: bool = Form(False),
    user: dict | None = Depends(get_optional_user),
):
    """カラオケ音源用 (Demucsあり)。ログイン済みなら履歴に自動保存"""
    start_time = time.time()
    print(f"\n{'#'*60}")
    print(f"[API] カラオケ音源分析リクエスト受信: {file.filename}")
    print(f"{'#'*60}")

    temp_input_path = None
    converted_wav_path = None
    vocal_path = None
    request_id = str(uuid.uuid4())
    # リクエストごとに独立したディレクトリを使い、並行リクエスト間のファイル混同を防ぐ
    separated_request_dir = os.path.join(SEPARATED_DIR, request_id)

    try:
        await _validate_upload_file(file)

        print(f"[API] [1/5] ファイル保存中...")
        # _validate_upload_file() 通過後は必ず有効な拡張子が取れる（空文字は 400 で弾かれる）
        ext = os.path.splitext(file.filename or "")[1]
        temp_input_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{ext}")
        with open(temp_input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"[API] [1/5] 保存完了: {temp_input_path}")

        print(f"\n[API] [2/5] 高品質WAV変換中...")
        t_step = time.time()
        converted_wav_path = convert_to_wav_hq(temp_input_path, output_dir=UPLOAD_DIR)
        print(f"[API] [2/5] 変換完了: {converted_wav_path} ({time.time() - t_step:.1f}s)")

        print(f"\n[API] [3/5] Demucsボーカル分離実行中...")
        t_step = time.time()
        vocal_path = separate_vocals(
            converted_wav_path,
            output_dir=separated_request_dir,
            ultra_fast_mode=True,
        )
        print(f"[API] [3/5] ボーカル分離完了: {vocal_path} ({time.time() - t_step:.1f}s)")

        print(f"\n[API] [4/5] DeepFilterNetノイズ除去実行中...")
        t_step = time.time()
        vocal_path = apply_deepfilter(vocal_path, attenuation_limit_db=DFN_ATTENUATION_LIMIT_DB)
        print(f"[API] [4/5] ノイズ除去完了: {vocal_path} ({time.time() - t_step:.1f}s)")

        print(f"\n[API] [5/5] 音域解析実行中...")
        t_step = time.time()
        result = analyze(vocal_path, already_separated=True, no_falsetto=no_falsetto)
        print(f"[API] [5/5] 音域解析完了 ({time.time() - t_step:.1f}s)")
        if "error" in result:
            print(f"[WARN] [API] 解析エラー詳細: {result['error']}")
            raise HTTPException(status_code=422, detail=result["error"])

        print(
            "[INFO] 最低音/最高音: "
            f"{result.get('overall_min', 'unknown')}({result.get('overall_min_hz', 0.0):.1f}Hz), "
            f"{result.get('overall_max', 'unknown')}({result.get('overall_max_hz', 0.0):.1f}Hz)"
        )

        debug_paths = _save_debug_outputs(
            source_wav_path=vocal_path,
            result=result,
            request_id=request_id,
        )
        if debug_paths:
            print("[INFO] debugfile 保存完了:")
            for p in debug_paths:
                print(f"  - {p}")

        result = _enrich_result(result, user)
        _auto_save_analysis(user, result, "karaoke", file.filename)

        elapsed_time = time.time() - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        time_str = f"{minutes}分{seconds}秒" if minutes > 0 else f"{seconds}秒"
        print(f"\n[API] カラオケ音源分析完了 (処理時間: {time_str})")
        if elapsed_time > 240:
            print(f"[WARN] 処理時間が長いです ({time_str})")
        print(f"{'#'*60}\n")

        background_tasks.add_task(cleanup_files, temp_input_path, converted_wav_path, separated_request_dir)
        return result

    except HTTPException:
        background_tasks.add_task(cleanup_files, temp_input_path, converted_wav_path, separated_request_dir)
        raise
    except Exception as e:
        print(f"[ERROR] [API] カラオケ音源分析エラー: {e}")
        background_tasks.add_task(cleanup_files, temp_input_path, converted_wav_path, separated_request_dir)
        raise HTTPException(status_code=500, detail="カラオケ音源解析中にエラーが発生しました")
