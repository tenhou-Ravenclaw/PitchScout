"""
楽曲・アーティスト関連エンドポイント（認証不要）
- /songs
- /artists, /artists/{artist_id}/songs
- /recommend
- /similar-artists
"""
from fastapi import APIRouter, Depends, Query
from db.songs import (
    get_all_songs, search_songs, count_songs,
    get_artists, get_artist_songs, count_artists, search_artists,
)
from recommender import recommend_songs, recommend_key_for_song, find_similar_artists
from db.users import get_favorite_artist_ids
from auth import get_optional_user

router = APIRouter(tags=["songs"])


# ============================================================
# アーティスト一覧（認証不要）
# ============================================================

@router.get("/artists")
def read_artists(
    limit: int = 10,
    offset: int = 0,
    q: str | None = None,
):
    """アーティスト一覧を取得（ページネーション対応）"""
    if q:
        artists = search_artists(q, limit, offset)
        total = count_artists(q)
    else:
        artists = get_artists(limit, offset)
        total = count_artists()
    return {"artists": artists, "total": total}


@router.get("/artists/{artist_id}/songs")
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

@router.get("/songs")
def read_songs(
    limit: int = 20,
    offset: int = 0,
    q: str | None = None,
    chest_min_hz: float | None = Query(None, description="ユーザー地声最低(Hz)"),
    chest_max_hz: float | None = Query(None, description="ユーザー地声最高(Hz)"),
    falsetto_max_hz: float | None = Query(None, description="ユーザー裏声最高(Hz)"),
):
    """楽曲一覧を取得（検索・ページネーション対応）"""
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
# おすすめ曲・似てるアーティスト（認証オプショナル）
# ============================================================

@router.get("/recommend")
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


@router.get("/similar-artists")
def get_similar_artists(
    chest_min_hz: float = Query(...),
    chest_max_hz: float = Query(...),
    chest_avg_hz: float = Query(...),
    limit: int = Query(5, ge=1, le=20),
):
    """音域Hzを指定して似てるアーティストを取得"""
    return find_similar_artists(chest_min_hz, chest_max_hz, chest_avg_hz, limit)
