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
from fastapi.encoders import jsonable_encoder

from audio.converter import convert_to_wav, convert_to_wav_hq
from analysis import analyze
from audio.separator import separate_vocals
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
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SEPARATED_DIR, exist_ok=True)


def cleanup_files(*paths: str | None) -> None:
    """一時ファイルを削除するバックグラウンドタスク"""
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
    print(f"[API] 📥 アカペラ音源分析リクエスト受信: {file.filename}")
    print(f"{'#'*60}")

    temp_input_path = None
    converted_wav_path = None

    try:
        print(f"[API] [1/3] ファイル保存中...")
        ext = os.path.splitext(file.filename or "")[1] or ".tmp"
        temp_input_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{ext}")

        with open(temp_input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"[API] ✅ 保存完了: {temp_input_path}")

        print(f"\n[API] [2/3] WAV変換中...")
        converted_wav_path = convert_to_wav(temp_input_path, output_dir=UPLOAD_DIR)
        print(f"[API] ✅ 変換完了: {converted_wav_path}")

        print(f"\n[API] [3/3] 音域解析実行中...")
        result = analyze(converted_wav_path, no_falsetto=no_falsetto)
        result = _enrich_result(result, user)
        _auto_save_analysis(user, result, "microphone", file.filename)

        elapsed_time = time.time() - start_time
        print(f"\n[API] ✅ アカペラ音源分析完了! (処理時間: {elapsed_time:.2f}秒)")
        print(f"{'#'*60}\n")

        background_tasks.add_task(cleanup_files, temp_input_path, converted_wav_path)
        return result

    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"[API] ❌ エラー発生: {e} (経過時間: {elapsed_time:.2f}秒)")
        background_tasks.add_task(cleanup_files, temp_input_path, converted_wav_path)
        return {"error": f"エラーが発生しました: {str(e)}"}


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
    print(f"[API] 📥 カラオケ音源分析リクエスト受信: {file.filename}")
    print(f"{'#'*60}")

    temp_input_path = None
    converted_wav_path = None
    vocal_path = None
    demucs_folder = None

    try:
        print(f"[API] [1/4] ファイル保存中...")
        ext = os.path.splitext(file.filename or "")[1] or ".tmp"
        temp_input_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{ext}")
        with open(temp_input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"[API] ✅ 保存完了: {temp_input_path}")

        print(f"\n[API] [2/4] 高品質WAV変換中...")
        converted_wav_path = convert_to_wav_hq(temp_input_path, output_dir=UPLOAD_DIR)
        print(f"[API] ✅ 変換完了: {converted_wav_path}")

        print(f"\n[API] [3/4] Demucsボーカル分離実行中...")
        vocal_path = separate_vocals(
            converted_wav_path,
            output_dir=SEPARATED_DIR,
            fast_mode=True,
        )
        print(f"[API] ✅ ボーカル分離完了: {vocal_path}")

        print(f"\n[API] [4/4] 音域解析実行中...")
        result = analyze(vocal_path, already_separated=True, no_falsetto=no_falsetto)
        result = _enrich_result(result, user)
        _auto_save_analysis(user, result, "karaoke", file.filename)

        if vocal_path:
            demucs_folder = os.path.dirname(vocal_path)

        elapsed_time = time.time() - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        time_str = f"{minutes}分{seconds}秒" if minutes > 0 else f"{seconds}秒"
        print(f"\n[API] ✅ カラオケ音源分析完了! (処理時間: {time_str})")
        if elapsed_time > 240:
            print(f"[WARN] ⚠️ 処理時間が長いです ({time_str})")
        print(f"{'#'*60}\n")

        background_tasks.add_task(cleanup_files, temp_input_path, converted_wav_path, demucs_folder)
        return result

    except Exception as e:
        print(f"[ERROR] Process failed: {e}")
        if vocal_path:
            demucs_folder = os.path.dirname(vocal_path)
        background_tasks.add_task(cleanup_files, temp_input_path, converted_wav_path, demucs_folder)
        return {"error": f"処理中にエラーが発生しました: {str(e)}"}
