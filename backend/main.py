import warnings
warnings.filterwarnings("ignore")

from fastapi import FastAPI, File, UploadFile, BackgroundTasks, Depends, HTTPException, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
import shutil
import os
import uuid
import time

from audio_converter import convert_to_wav, convert_to_wav_hq
from analyzer import analyze
from vocal_separator import separate_vocals

# recommender 関数群（おすすめ曲・キー・声質タイプ）
from recommender import (
    recommend_songs, recommend_key_for_song,
    find_similar_artists, classify_voice_type,
)

# 楽曲データは Supabase（マージ済み834アーティスト、5,341曲）
from database_supabase import get_all_songs, search_songs, count_songs, get_artists, get_artist_songs, count_artists, search_artists

# 認証・ユーザー系は Supabase
from database_supabase import (
    get_user_profile, update_user_profile, update_vocal_range,
    create_analysis_record, get_analysis_history,delete_analysis_record,
    update_analysis_record,
    get_integrated_vocal_range,
    add_favorite_song, remove_favorite_song, get_favorite_songs, is_favorite,
    # お気に入りアーティスト
    add_favorite_artist, remove_favorite_artist,
    get_favorite_artists, is_favorite_artist, get_favorite_artist_ids,
)

# 認証関連
from auth import (
    get_current_user, get_optional_user,
    sign_up_with_email, sign_in_with_email, sign_out,
    refresh_session, request_password_reset, update_password
)

# Pydanticモデル
from models import (
    SignUpRequest, SignInRequest, RefreshTokenRequest,
    PasswordResetRequest, PasswordUpdateRequest,
    UserProfileUpdate, VocalRangeUpdate,
    AnalysisCreate, AnalysisUpdate, FavoriteSongAdd,
    FavoriteArtistAdd,
)

app = FastAPI(title="Voice Range Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: 本番環境では具体的なオリジンに限定すること
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 認証エンドポイント
# ============================================================

@app.post("/auth/signup")
def signup(data: SignUpRequest):
    """メールアドレスでユーザー登録"""
    return sign_up_with_email(data.email, data.password, data.display_name)


@app.post("/auth/signin")
def signin(data: SignInRequest):
    """メールアドレスでログイン"""
    return sign_in_with_email(data.email, data.password)


@app.post("/auth/signout")
def signout_endpoint(user: dict = Depends(get_current_user)):
    """ログアウト"""
    sign_out(user.get("id"))
    return {"message": "ログアウトしました"}


@app.post("/auth/refresh")
def refresh(data: RefreshTokenRequest):
    """セッションをリフレッシュ"""
    return refresh_session(data.refresh_token)


@app.post("/auth/reset-password")
def reset_password(data: PasswordResetRequest):
    """パスワードリセットメールを送信"""
    success = request_password_reset(data.email)
    if success:
        return {"message": "パスワードリセットメールを送信しました"}
    raise HTTPException(status_code=400, detail="メール送信に失敗しました")


@app.post("/auth/update-password")
def update_password_endpoint(data: PasswordUpdateRequest, user: dict = Depends(get_current_user)):
    """パスワードを更新（要ログイン）"""
    success = update_password(user.get("id"), data.new_password)
    if success:
        return {"message": "パスワードを更新しました"}
    raise HTTPException(status_code=400, detail="パスワード更新に失敗しました")


# ============================================================
# ユーザープロファイル
# ============================================================

@app.get("/profile/me")
def get_my_profile(user: dict = Depends(get_current_user)):
    """自分のプロファイルを取得"""
    profile = get_user_profile(user["id"])
    if not profile:
        raise HTTPException(status_code=404, detail="プロファイルが見つかりません")
    return profile


@app.put("/profile/me")
def update_my_profile(data: UserProfileUpdate, user: dict = Depends(get_current_user)):
    """自分のプロファイルを更新"""
    profile = update_user_profile(user["id"], data.model_dump(exclude_none=True))
    return profile


@app.put("/profile/vocal-range")
def update_my_vocal_range(data: VocalRangeUpdate, user: dict = Depends(get_current_user)):
    """自分の声域情報を更新"""
    result = update_vocal_range(
        user["id"],
        data.vocal_range_min,
        data.vocal_range_max,
        data.falsetto_max
    )
    return result


# ============================================================
# 分析履歴
# ============================================================

@app.post("/analysis")
def create_analysis(data: AnalysisCreate, user: dict = Depends(get_current_user)):
    """分析履歴を保存"""
    record = create_analysis_record(
        user["id"],
        data.vocal_range_min,
        data.vocal_range_max,
        data.falsetto_max,
        data.source_type,
        data.file_name
    )

    update_vocal_range(
        user["id"],
        data.vocal_range_min,
        data.vocal_range_max,
        data.falsetto_max
    )

    return record


@app.get("/analysis/history")
def get_my_analysis_history(user: dict = Depends(get_current_user), limit: int = 50):
    """自分の分析履歴を取得"""
    return get_analysis_history(user["id"], limit)

@app.get("/analysis/integrated-range")
def get_my_integrated_range(user: dict = Depends(get_current_user), limit: int = Query(20, ge=1, le=100)):
    """直近N件の分析履歴から統合音域を取得"""
    result = get_integrated_vocal_range(user["id"], limit)
    if not result:
        raise HTTPException(status_code=404, detail="統合可能な分析データが見つかりません")
    return result

@app.delete("/analysis/history/{record_id}")
def delete_my_analysis_history(record_id: str, user: dict = Depends(get_current_user)):
    """自分の分析履歴を削除"""
    success = delete_analysis_record(user["id"], record_id)
    if success:
        return {"message": "履歴を削除しました"}
    raise HTTPException(status_code=400, detail="履歴の削除に失敗しました")


@app.patch("/analysis/history/{record_id}")
def update_my_analysis_history(record_id: str, data: AnalysisUpdate, user: dict = Depends(get_current_user)):
    """自分の分析履歴を更新 (file_nameなど)"""
    result = update_analysis_record(user["id"], record_id, data.model_dump(exclude_none=True))
    if result:
        return result
    raise HTTPException(status_code=400, detail="履歴の更新に失敗しました")


# ============================================================
# お気に入り楽曲
# ============================================================

@app.post("/favorites")
def add_favorite(data: FavoriteSongAdd, user: dict = Depends(get_current_user)):
    """お気に入りに楽曲を追加"""
    result = add_favorite_song(user["id"], data.song_id)
    if not result:
        raise HTTPException(status_code=400, detail="既にお気に入りに登録されています")
    return result


@app.delete("/favorites/{song_id}")
def remove_favorite(song_id: int, user: dict = Depends(get_current_user)):
    """お気に入りから楽曲を削除"""
    success = remove_favorite_song(user["id"], song_id)
    if success:
        return {"message": "お気に入りから削除しました"}
    raise HTTPException(status_code=404, detail="お気に入りに登録されていません")


@app.get("/favorites")
def get_my_favorites(user: dict = Depends(get_current_user), limit: int = 100):
    """自分のお気に入り楽曲一覧を取得"""
    return get_favorite_songs(user["id"], limit)


@app.get("/favorites/check/{song_id}")
def check_favorite(song_id: int, user: dict = Depends(get_current_user)):
    """楽曲がお気に入りに登録されているか確認"""
    return {"is_favorite": is_favorite(user["id"], song_id)}


# ============================================================
# お気に入りアーティスト
# ============================================================

@app.post("/favorite-artists")
def add_favorite_artist_endpoint(
    data: FavoriteArtistAdd,
    user: dict = Depends(get_current_user),
):
    """
    お気に入りアーティストを追加（上限10組）。
    artist_id と artist_name は /songs?q= などで検索して取得してください。
    """
    result = add_favorite_artist(user["id"], data.artist_id, data.artist_name)
    if result is None:
        # 上限 or 重複
        existing = is_favorite_artist(user["id"], data.artist_id)
        if existing:
            raise HTTPException(status_code=400, detail="既にお気に入りに登録されています")
        raise HTTPException(status_code=400, detail="お気に入りアーティストは10組まで登録できます")
    return result


@app.delete("/favorite-artists/{artist_id}")
def remove_favorite_artist_endpoint(
    artist_id: int,
    user: dict = Depends(get_current_user),
):
    """お気に入りアーティストを削除"""
    success = remove_favorite_artist(user["id"], artist_id)
    if success:
        return {"message": "お気に入りから削除しました"}
    raise HTTPException(status_code=404, detail="お気に入りに登録されていません")


@app.get("/favorite-artists")
def get_my_favorite_artists(user: dict = Depends(get_current_user)):
    """自分のお気に入りアーティスト一覧を取得"""
    return get_favorite_artists(user["id"])


@app.get("/favorite-artists/check/{artist_id}")
def check_favorite_artist(artist_id: int, user: dict = Depends(get_current_user)):
    """アーティストがお気に入りに登録されているか確認"""
    return {"is_favorite": is_favorite_artist(user["id"], artist_id)}


# ============================================================
# アーティスト一覧（認証不要）
# ============================================================

@app.get("/artists")
def read_artists(
    limit: int = 10, offset: int = 0, q: str | None = None,
):
    """アーティスト一覧を取得（ページネーション対応）"""
    if q:
        artists = search_artists(q, limit, offset)
        total = count_artists(q)
    else:
        artists = get_artists(limit, offset)
        total = count_artists()
    return {"artists": artists, "total": total}


@app.get("/artists/{artist_id}/songs")
def read_artist_songs(
    artist_id: int,
    chest_min_hz: float | None = Query(None),
    chest_max_hz: float | None = Query(None),
    falsetto_max_hz: float | None = Query(None),
):
    """特定アーティストの楽曲一覧を取得"""
    songs = get_artist_songs(artist_id)
    if chest_min_hz and chest_max_hz:
        effective_max = chest_max_hz
        if falsetto_max_hz and falsetto_max_hz > chest_max_hz:
            effective_max = falsetto_max_hz
        for song in songs:
            try:
                key_info = recommend_key_for_song(
                    song.get("lowest_note"),
                    song.get("highest_note"),
                    chest_min_hz,
                    effective_max,
                )
                song.update(key_info)
            except Exception:
                song["recommended_key"] = 0
                song["fit"] = "unknown"
    return songs


# ============================================================
# 楽曲検索（認証不要）
# ============================================================

@app.get("/songs")
def read_songs(
    limit: int = 20, offset: int = 0, q: str | None = None,
    chest_min_hz: float | None = Query(None, description="ユーザー地声最低(Hz)"),
    chest_max_hz: float | None = Query(None, description="ユーザー地声最高(Hz)"),
    falsetto_max_hz: float | None = Query(None, description="ユーザー裏声最高(Hz)"),
):
    if q:
        songs = search_songs(q, limit, offset)
        total = count_songs(q)
    else:
        songs = get_all_songs(limit, offset)
        total = count_songs()

    if chest_min_hz and chest_max_hz:
        effective_max = chest_max_hz
        if falsetto_max_hz and falsetto_max_hz > chest_max_hz:
            effective_max = falsetto_max_hz
        for song in songs:
            try:
                key_info = recommend_key_for_song(
                    song.get("lowest_note"),
                    song.get("highest_note"),
                    chest_min_hz,
                    effective_max,
                )
                song.update(key_info)
            except Exception:
                song["recommended_key"] = 0
                song["fit"] = "unknown"

    return {"songs": songs, "total": total}


# ============================================================
# おすすめ曲・似てるアーティスト（単体エンドポイント）
# ============================================================

@app.get("/recommend")
def get_recommendations(
    chest_min_hz: float = Query(...),
    chest_max_hz: float = Query(...),
    chest_avg_hz: float = Query(...),
    falsetto_max_hz: float | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    user: dict | None = Depends(get_optional_user),
):
    """音域Hzを指定しておすすめ曲を取得（ログイン済みならお気に入りアーティスト優先）"""
    fav_ids = get_favorite_artist_ids(user["id"]) if user else []
    return recommend_songs(
        chest_min_hz, chest_max_hz, chest_avg_hz, falsetto_max_hz,
        limit=limit, favorite_artist_ids=fav_ids,
    )


@app.get("/similar-artists")
def get_similar_artists(
    chest_min_hz: float = Query(...),
    chest_max_hz: float = Query(...),
    chest_avg_hz: float = Query(...),
    limit: int = Query(5, ge=1, le=20),
):
    """音域Hzを指定して似てるアーティストを取得"""
    return find_similar_artists(chest_min_hz, chest_max_hz, chest_avg_hz, limit)


# ============================================================
# ファイル管理
# ============================================================

UPLOAD_DIR = "uploads"
SEPARATED_DIR = "separated"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SEPARATED_DIR, exist_ok=True)


def cleanup_files(*paths):
    """一時ファイルを削除するタスク"""
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
    """解析結果におすすめ曲・似てるアーティストを追加"""
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


# ============================================================
# 音声分析エンドポイント（認証オプショナル）
# ============================================================

@app.post("/analyze")
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
        ext = os.path.splitext(file.filename)[1] or ".tmp"
        temp_input_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{ext}")

        with open(temp_input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"[API] ✅ 保存完了: {temp_input_path}")

        print(f"\n[API] [2/3] WAV変換中...")
        converted_wav_path = convert_to_wav(temp_input_path, output_dir=UPLOAD_DIR)
        print(f"[API] ✅ 変換完了: {converted_wav_path}")

        print(f"\n[API] [3/3] 音域解析実行中...")
        result = analyze(converted_wav_path, no_falsetto=no_falsetto)

        # 2. その result におすすめ曲などを追加する
        result = _enrich_result(result, user)

        # 3. 最後に、完全な result を使って履歴を保存する
        if user and not result.get("error"):
            try:
                create_analysis_record(
                    user_id=user["id"],
                    vocal_min=result.get("overall_min"),
                    vocal_max=result.get("overall_max"),
                    falsetto=result.get("falsetto_max"),
                    source_type="microphone",
                    file_name=file.filename,
                    result_json=jsonable_encoder(result)
                )
                update_vocal_range(
                    user["id"],
                    result.get("overall_min"),
                    result.get("overall_max"),
                    result.get("falsetto_max"),
                )
            except Exception as e:
                print(f"[WARN] 履歴保存失敗: {e}")

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


@app.post("/analyze-karaoke")
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
        ext = os.path.splitext(file.filename)[1] or ".tmp"
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
            ultra_fast_mode=True,
        )
        print(f"[API] ✅ ボーカル分離完了: {vocal_path}")

        print(f"\n[API] [4/4] 音域解析実行中...")
        result = analyze(vocal_path, already_separated=True, no_falsetto=no_falsetto)

        # 2. その result におすすめ曲などを追加する
        result = _enrich_result(result, user)

        # 3. 最後に、完全な result を使って履歴を保存する
        if user and not result.get("error"):
            try:
                create_analysis_record(
                    user_id=user["id"],
                    vocal_min=result.get("overall_min"),
                    vocal_max=result.get("overall_max"),
                    falsetto=result.get("falsetto_max"),
                    source_type="karaoke",
                    file_name=file.filename,
                    result_json=jsonable_encoder(result)
                )
                update_vocal_range(
                    user["id"],
                    result.get("overall_min"),
                    result.get("overall_max"),
                    result.get("falsetto_max"),
                )
            except Exception as e:
                print(f"[WARN] 履歴保存失敗: {e}")

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