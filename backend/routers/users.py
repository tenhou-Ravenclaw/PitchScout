"""
ユーザー関連エンドポイント
- /profile/* (プロファイル)
- /analysis/* (分析履歴・統合音域)
- /favorites* (お気に入り楽曲)
- /favorite-artists* (お気に入りアーティスト)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from auth import get_current_user
from db.users import (
    get_user_profile, update_user_profile, update_vocal_range,
    create_analysis_record, get_analysis_history, delete_analysis_record,
    update_analysis_record,
    get_favorite_artist_ids,
    add_favorite_song, remove_favorite_song, get_favorite_songs, is_favorite,
    add_favorite_artist, remove_favorite_artist,
    get_favorite_artists, is_favorite_artist,
)
from recommender import aggregate_vocal_range
from models import (
    UserProfileUpdate, VocalRangeUpdate,
    AnalysisCreate, AnalysisUpdate, FavoriteSongAdd,
    FavoriteArtistAdd,
)

router = APIRouter(tags=["users"])


# ============================================================
# ユーザープロファイル
# ============================================================

@router.get("/profile/me")
def get_my_profile(user: dict = Depends(get_current_user)):
    """自分のプロファイルを取得"""
    profile = get_user_profile(user["id"])
    if not profile:
        raise HTTPException(status_code=404, detail="プロファイルが見つかりません")
    return profile


@router.put("/profile/me")
def update_my_profile(data: UserProfileUpdate, user: dict = Depends(get_current_user)):
    """自分のプロファイルを更新"""
    profile = update_user_profile(user["id"], data.model_dump(exclude_none=True))
    return profile


@router.put("/profile/vocal-range")
def update_my_vocal_range(data: VocalRangeUpdate, user: dict = Depends(get_current_user)):
    """自分の声域情報を更新"""
    result = update_vocal_range(
        user["id"],
        data.vocal_range_min,
        data.vocal_range_max,
        data.falsetto_max,
    )
    return result


# ============================================================
# 分析履歴
# ============================================================

@router.post("/analysis")
def create_analysis(data: AnalysisCreate, user: dict = Depends(get_current_user)):
    """分析履歴を保存"""
    record = create_analysis_record(
        user["id"],
        data.vocal_range_min,
        data.vocal_range_max,
        data.falsetto_max,
        data.source_type,
        data.file_name,
    )
    update_vocal_range(
        user["id"],
        data.vocal_range_min,
        data.vocal_range_max,
        data.falsetto_max,
    )
    return record


@router.get("/analysis/history")
def get_my_analysis_history(
    user: dict = Depends(get_current_user),
    limit: int = 50,
):
    """自分の分析履歴を取得"""
    return get_analysis_history(user["id"], limit)


@router.get("/analysis/integrated-range")
def get_my_integrated_range(
    user: dict = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
):
    """直近N件の分析履歴から統合音域を取得"""
    records = get_analysis_history(user["id"], limit)
    fav_ids = get_favorite_artist_ids(user["id"])
    result = aggregate_vocal_range(records, favorite_artist_ids=fav_ids)
    if not result:
        raise HTTPException(status_code=404, detail="統合可能な分析データが見つかりません")
    return result


@router.delete("/analysis/history/{record_id}")
def delete_my_analysis_history(record_id: str, user: dict = Depends(get_current_user)):
    """自分の分析履歴を削除"""
    success = delete_analysis_record(user["id"], record_id)
    if success:
        return {"message": "履歴を削除しました"}
    raise HTTPException(status_code=400, detail="履歴の削除に失敗しました")


@router.patch("/analysis/history/{record_id}")
def update_my_analysis_history(
    record_id: str,
    data: AnalysisUpdate,
    user: dict = Depends(get_current_user),
):
    """自分の分析履歴を更新 (file_nameなど)"""
    result = update_analysis_record(user["id"], record_id, data.model_dump(exclude_none=True))
    if result:
        return result
    raise HTTPException(status_code=400, detail="履歴の更新に失敗しました")


# ============================================================
# お気に入り楽曲
# ============================================================

@router.post("/favorites")
def add_favorite(data: FavoriteSongAdd, user: dict = Depends(get_current_user)):
    """お気に入りに楽曲を追加"""
    result = add_favorite_song(user["id"], data.song_id)
    if not result:
        raise HTTPException(status_code=400, detail="既にお気に入りに登録されています")
    return result


@router.delete("/favorites/{song_id}")
def remove_favorite(song_id: int, user: dict = Depends(get_current_user)):
    """お気に入りから楽曲を削除"""
    success = remove_favorite_song(user["id"], song_id)
    if success:
        return {"message": "お気に入りから削除しました"}
    raise HTTPException(status_code=404, detail="お気に入りに登録されていません")


@router.get("/favorites")
def get_my_favorites(user: dict = Depends(get_current_user), limit: int = 100):
    """自分のお気に入り楽曲一覧を取得"""
    return get_favorite_songs(user["id"], limit)


@router.get("/favorites/check/{song_id}")
def check_favorite(song_id: int, user: dict = Depends(get_current_user)):
    """楽曲がお気に入りに登録されているか確認"""
    return {"is_favorite": is_favorite(user["id"], song_id)}


# ============================================================
# お気に入りアーティスト
# ============================================================

@router.post("/favorite-artists")
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


@router.delete("/favorite-artists/{artist_id}")
def remove_favorite_artist_endpoint(
    artist_id: int,
    user: dict = Depends(get_current_user),
):
    """お気に入りアーティストを削除"""
    success = remove_favorite_artist(user["id"], artist_id)
    if success:
        return {"message": "お気に入りから削除しました"}
    raise HTTPException(status_code=404, detail="お気に入りに登録されていません")


@router.get("/favorite-artists")
def get_my_favorite_artists(user: dict = Depends(get_current_user)):
    """自分のお気に入りアーティスト一覧を取得"""
    return get_favorite_artists(user["id"])


@router.get("/favorite-artists/check/{artist_id}")
def check_favorite_artist(artist_id: int, user: dict = Depends(get_current_user)):
    """アーティストがお気に入りに登録されているか確認"""
    return {"is_favorite": is_favorite_artist(user["id"], artist_id)}
