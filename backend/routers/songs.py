"""
楽曲・アーティスト関連エンドポイント（認証不要）
- /songs
- /artists, /artists/{artist_id}/songs
- /recommend
- /similar-artists
"""
from fastapi import APIRouter, Depends, Query
from db.songs import (
    get_all_songs, get_all_songs_raw, search_songs, count_songs,
    get_artists, get_artist_songs, count_artists, search_artists,
)
from recommender import (
    recommend_songs, recommend_challenge_songs,
    recommend_key_for_song, find_similar_artists,
)
from db.users import get_favorite_artist_ids
from auth import get_optional_user

router = APIRouter(tags=["songs"])


# ============================================================
# アーティスト一覧（認証不要）
# ============================================================

@router.get("/artists")
def read_artists(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
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
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: str | None = None,
    chest_min_hz: float | None = Query(None, description="ユーザー地声最低(Hz)"),
    chest_max_hz: float | None = Query(None, description="ユーザー地声最高(Hz)"),
    falsetto_max_hz: float | None = Query(None, description="ユーザー裏声最高(Hz)"),
    filter_by_range: bool = Query(
        False,
        description=(
            "True のとき、chest_min_hz/chest_max_hz を使って歌える曲（fit: perfect/good/ok）のみ返す。"
            "False のときは全曲を返しキー推薦情報のみ付与する。"
        ),
    ),
):
    """
    楽曲一覧を取得（検索・ページネーション対応）。

    filter_by_range=True かつ Hz 情報が揃っている場合、
    キー変更を考慮してユーザーの音域内に収まる楽曲のみを返す（fit: perfect/good/ok）。
    全件に対して Python でフィルタするため q を指定して件数を絞ることを推奨する。
    """
    has_hz = chest_min_hz is not None and chest_max_hz is not None

    if filter_by_range and has_hz:
        # 全件取得 → Python で音域フィルタ → ページネーション
        effective_max = chest_max_hz
        if falsetto_max_hz and falsetto_max_hz > chest_max_hz:
            effective_max = falsetto_max_hz

        # 全件取得して Python 側で音域フィルタを適用する。
        # 現在 ~5000 曲で許容範囲だが、DB 拡張時のメモリ圧迫を防ぐため上限を設ける。
        _MAX_FILTER_SONGS = 20000
        all_songs = get_all_songs_raw(q or "")[:_MAX_FILTER_SONGS]
        filtered: list[dict] = []
        for song in all_songs:
            try:
                key_info = recommend_key_for_song(
                    song.get("lowest_note"),
                    song.get("highest_note"),
                    chest_min_hz,
                    effective_max,
                )
                if key_info["fit"] in ("perfect", "good", "ok"):
                    song.update(key_info)
                    filtered.append(song)
            except Exception:
                pass

        total = len(filtered)
        songs = filtered[offset: offset + limit]
        return {"songs": songs, "total": total}

    # 通常モード: DB ページネーション → キー推薦情報を付与
    if q:
        songs = search_songs(q, limit, offset)
        total = count_songs(q)
    else:
        songs = get_all_songs(limit, offset)
        total = count_songs()

    if has_hz:
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

@router.get("/recommend/challenge")
def get_challenge_recommendations(
    chest_min_hz: float = Query(..., description="ユーザー地声最低(Hz)"),
    chest_max_hz: float = Query(..., description="ユーザー地声最高(Hz)"),
    chest_avg_hz: float = Query(..., description="ユーザー地声平均(Hz)"),
    falsetto_max_hz: float | None = Query(None, description="ユーザー裏声最高(Hz)"),
    limit: int = Query(5, ge=1, le=20),
):
    """
    あと少しで歌えるチャレンジ曲を取得する。

    通常推薦（/recommend）のスコア下限（30点）以下だが、
    練習すれば届く範囲（高音ペナルティ 1〜5半音）の楽曲を返す。
    各曲に challenge_reason（難易度の主因）を付与する。
    """
    return recommend_challenge_songs(
        chest_min_hz, chest_max_hz, chest_avg_hz,
        falsetto_max_hz, limit=limit,
    )


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
