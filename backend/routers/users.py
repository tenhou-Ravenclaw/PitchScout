"""
ユーザー関連エンドポイント
- /profile/* (プロファイル)
- /analysis/* (分析履歴・統合音域)
- /favorites* (お気に入り楽曲)
- /favorite-artists* (お気に入りアーティスト)
"""
import math
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from auth import get_current_user
from config import FAVORITE_ARTIST_LIMIT, STABLE_THRESHOLD
from db.users import (
    get_user_profile, update_user_profile, update_vocal_range,
    create_analysis_record, get_analysis_history, get_analysis_timeline,
    delete_analysis_record, update_analysis_record,
    get_favorite_artist_ids,
    add_favorite_song, remove_favorite_song, get_favorite_songs, is_favorite,
    batch_check_favorites,
    add_favorite_artist, remove_favorite_artist,
    get_favorite_artists, is_favorite_artist,
)
from recommender import aggregate_vocal_range
from models import (
    UserProfileUpdate, VocalRangeUpdate,
    AnalysisCreate, AnalysisUpdate, FavoriteSongAdd,
    BatchFavoriteCheckRequest,
    FavoriteArtistAdd,
)

router = APIRouter(tags=["users"])


# ============================================================
# ユーザープロファイル
# ============================================================

@router.get("/profile/me")
def get_my_profile(user: dict = Depends(get_current_user)) -> dict:
    """自分のプロファイルを取得"""
    profile = get_user_profile(user["id"])
    if not profile:
        raise HTTPException(status_code=404, detail="プロファイルが見つかりません")
    return profile


@router.put("/profile/me")
def update_my_profile(data: UserProfileUpdate, user: dict = Depends(get_current_user)) -> dict:
    """自分のプロファイルを更新"""
    profile = update_user_profile(user["id"], data.model_dump(exclude_none=True))
    if profile is None:
        raise HTTPException(status_code=500, detail="プロファイルの更新に失敗しました")
    return profile


@router.put("/profile/vocal-range")
def update_my_vocal_range(data: VocalRangeUpdate, user: dict = Depends(get_current_user)) -> dict:
    """自分の声域情報を更新"""
    result = update_vocal_range(
        user["id"],
        data.vocal_range_min,
        data.vocal_range_max,
        data.falsetto_max,
    )
    if result is None:
        raise HTTPException(status_code=500, detail="声域情報の更新に失敗しました")
    return result


# ============================================================
# 分析履歴
# ============================================================

@router.post("/analysis")
def create_analysis(data: AnalysisCreate, user: dict = Depends(get_current_user)) -> dict:
    """分析履歴を保存"""
    record = create_analysis_record(
        user["id"],
        data.vocal_range_min,
        data.vocal_range_max,
        data.falsetto_max,
        data.source_type,
        data.file_name,
    )
    if record is None:
        raise HTTPException(status_code=500, detail="分析履歴の保存に失敗しました")
    if update_vocal_range(
        user["id"],
        data.vocal_range_min,
        data.vocal_range_max,
        data.falsetto_max,
    ) is None:
        print(f"[WARN] 声域プロファイルの更新に失敗しました (user={user['id']})")
    return record


@router.get("/analysis/history")
def get_my_analysis_history(
    user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
) -> list:
    """自分の分析履歴を取得"""
    return get_analysis_history(user["id"], limit)


@router.get("/analysis/integrated-range")
def get_my_integrated_range(
    user: dict = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    """直近N件の分析履歴から統合音域を取得"""
    records = get_analysis_history(user["id"], limit)
    fav_ids = get_favorite_artist_ids(user["id"])
    result = aggregate_vocal_range(records, favorite_artist_ids=fav_ids)
    if not result:
        raise HTTPException(status_code=404, detail="統合可能な分析データが見つかりません")
    return result


@router.get("/analysis/timeline")
def get_analysis_timeline_endpoint(
    limit: int = Query(40, ge=1, le=100),
    user: dict = Depends(get_current_user),
) -> dict:
    """
    直近 N 件の分析タイムラインと安定音域を返す。

    安定音域は直近 N 件中 4 回以上同じラベルが出現した場合に、
    最高音・最低音・裏声最高音を確定済みとして返す。

    Returns:
        timeline: 各レコードの日時・地声/裏声のラベルと Hz 値のリスト（古い順）。
        stable_range: 安定とみなせる地声最高音・最低音・裏声最高音のラベル。
    """
    from collections import Counter
    from note_converter import label_to_rank

    records = get_analysis_timeline(user["id"], limit)

    # タイムラインポイント構築（result_json から Hz 値を取得）
    timeline = []
    for r in records:
        rj = r.get("result_json") or {}
        timeline.append({
            "date": r["created_at"],
            "chest_min": r.get("vocal_range_min"),
            "chest_max": r.get("vocal_range_max"),
            "falsetto_max": r.get("falsetto_max"),
            "chest_min_hz": rj.get("chest_min_hz") or rj.get("overall_min_hz"),
            "chest_max_hz": rj.get("chest_max_hz") or rj.get("overall_max_hz"),
            "falsetto_max_hz": rj.get("falsetto_max_hz"),
        })

    # 安定音域計算（STABLE_THRESHOLD 回以上出たラベルの中で最高音 / 最低音を選択）

    chest_max_counts: Counter[str] = Counter(
        r.get("vocal_range_max") for r in records if r.get("vocal_range_max")
    )
    chest_min_counts: Counter[str] = Counter(
        r.get("vocal_range_min") for r in records if r.get("vocal_range_min")
    )
    falsetto_counts: Counter[str] = Counter(
        r.get("falsetto_max") for r in records if r.get("falsetto_max")
    )

    def best_label(counts: Counter, highest: bool) -> str | None:
        """
        閾値以上出現したラベルのうち最高音（highest=True）または最低音を返す。

        label_to_rank が -1 を返す未知ラベルは除外する。
        未知ラベルを含めると min() で -1 が最小値として誤選択されるため。

        Args:
            counts: ラベルの出現回数 Counter。
            highest: True なら最高音、False なら最低音を返す。

        Returns:
            条件を満たすラベル、または None。
        """
        candidates = [
            lbl for lbl, cnt in counts.items()
            if cnt >= STABLE_THRESHOLD and label_to_rank(lbl) >= 0
        ]
        if not candidates:
            return None
        try:
            return (
                max(candidates, key=label_to_rank) if highest
                else min(candidates, key=label_to_rank)
            )
        except Exception as exc:
            print(f"[WARN] 安定音域ラベル選択失敗: {exc}")
            return None

    stable_range = {
        "chest_max": best_label(chest_max_counts, highest=True),
        "chest_min": best_label(chest_min_counts, highest=False),
        "falsetto_max": best_label(falsetto_counts, highest=True),
    }

    return {"timeline": timeline, "stable_range": stable_range}


@router.get("/analysis/growth")
def get_analysis_growth(
    user: dict = Depends(get_current_user),
    limit: int = Query(20, ge=2, le=100, description="比較対象とする最大履歴件数"),
) -> dict:
    """
    音域成長サマリーを返す。

    直近 N 件の分析履歴のうち最古と最新を比較し、
    音域の変化量（半音数）と経過日数を算出する。
    半音数の符号: 正 = 上昇（最高音が上がった / 最低音が上がった）、
                  負 = 下降（最高音が下がった / 最低音が下がった）。
    地声音域の広さ (chest_range_delta_semitones) は正が拡大を意味する。

    Returns:
        has_growth_data が False の場合は履歴不足。
        True の場合は各 delta_semitones, period_days, oldest/latest の日時と音名を返す。
    """
    records = get_analysis_history(user["id"], limit)

    if len(records) < 2:
        return {
            "has_growth_data": False,
            "message": "成長データを計算するには2件以上の分析履歴が必要です",
        }

    # get_analysis_history は新しい順なので records[0]=最新、records[-1]=最古
    latest = records[0]
    oldest = records[-1]
    latest_rj: dict = latest.get("result_json") or {}
    oldest_rj: dict = oldest.get("result_json") or {}

    def _get_hz(rj: dict, key: str) -> float | None:
        """result_json から Hz 値を取得する。存在しない・非正値の場合は None。"""
        v = rj.get(key)
        return float(v) if v and float(v) > 0 else None

    def _semitone_delta(old_hz: float | None, new_hz: float | None) -> float | None:
        """2周波数間の半音数差を返す。どちらかが None なら None。"""
        if old_hz and new_hz:
            return round(12 * math.log2(new_hz / old_hz), 1)
        return None

    # 経過日数を計算
    period_days: int | None = None
    try:
        oldest_dt = datetime.fromisoformat(oldest["created_at"].replace("Z", "+00:00"))
        latest_dt = datetime.fromisoformat(latest["created_at"].replace("Z", "+00:00"))
        period_days = (latest_dt - oldest_dt).days
    except Exception as exc:
        print(f"[WARN] 経過日数の計算失敗: {exc}")

    old_chest_max = _get_hz(oldest_rj, "chest_max_hz")
    new_chest_max = _get_hz(latest_rj, "chest_max_hz")
    old_chest_min = _get_hz(oldest_rj, "chest_min_hz")
    new_chest_min = _get_hz(latest_rj, "chest_min_hz")

    # 地声音域の広さ変化（半音数）: 正 = 音域が広がった
    chest_range_delta: float | None = None
    if old_chest_max and old_chest_min and new_chest_max and new_chest_min:
        old_range = 12 * math.log2(old_chest_max / old_chest_min)
        new_range = 12 * math.log2(new_chest_max / new_chest_min)
        chest_range_delta = round(new_range - old_range, 1)

    old_fmax = _get_hz(oldest_rj, "falsetto_max_hz")
    new_fmax = _get_hz(latest_rj, "falsetto_max_hz")

    return {
        "has_growth_data": True,
        "data_count": len(records),
        "period_days": period_days,
        "oldest_date": oldest.get("created_at"),
        "latest_date": latest.get("created_at"),
        # 音名ラベル（表示用）
        "chest_max": {
            "oldest": oldest.get("vocal_range_max"),
            "latest": latest.get("vocal_range_max"),
        },
        "chest_min": {
            "oldest": oldest.get("vocal_range_min"),
            "latest": latest.get("vocal_range_min"),
        },
        "falsetto_max": {
            "oldest": oldest.get("falsetto_max"),
            "latest": latest.get("falsetto_max"),
        },
        # 成長量（半音数）
        "chest_max_delta_semitones": _semitone_delta(old_chest_max, new_chest_max),
        "chest_min_delta_semitones": _semitone_delta(old_chest_min, new_chest_min),
        "chest_range_delta_semitones": chest_range_delta,
        "falsetto_max_delta_semitones": _semitone_delta(old_fmax, new_fmax),
    }


@router.delete("/analysis/history/{record_id}")
def delete_my_analysis_history(record_id: str, user: dict = Depends(get_current_user)) -> dict:
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
) -> dict:
    """自分の分析履歴を更新 (file_nameなど)"""
    result = update_analysis_record(user["id"], record_id, data.model_dump(exclude_none=True))
    if result:
        return result
    raise HTTPException(status_code=400, detail="履歴の更新に失敗しました")


# ============================================================
# お気に入り楽曲
# ============================================================

@router.post("/favorites")
def add_favorite(data: FavoriteSongAdd, user: dict = Depends(get_current_user)) -> dict:
    """お気に入りに楽曲を追加"""
    result = add_favorite_song(user["id"], data.song_id)
    if not result:
        raise HTTPException(status_code=400, detail="既にお気に入りに登録されています")
    return result


@router.delete("/favorites/{song_id}")
def remove_favorite(song_id: int, user: dict = Depends(get_current_user)) -> dict:
    """お気に入りから楽曲を削除"""
    success = remove_favorite_song(user["id"], song_id)
    if success:
        return {"message": "お気に入りから削除しました"}
    raise HTTPException(status_code=404, detail="お気に入りに登録されていません")


@router.get("/favorites")
def get_my_favorites(user: dict = Depends(get_current_user), limit: int = Query(100, ge=1, le=100)) -> list:
    """自分のお気に入り楽曲一覧を取得"""
    return get_favorite_songs(user["id"], limit)


@router.get("/favorites/check/{song_id}")
def check_favorite(song_id: int, user: dict = Depends(get_current_user)) -> dict:
    """楽曲がお気に入りに登録されているか確認"""
    return {"is_favorite": is_favorite(user["id"], song_id)}


@router.post("/favorites/batch-check")
def batch_check_favorites_endpoint(
    data: BatchFavoriteCheckRequest,
    user: dict = Depends(get_current_user),
) -> dict[str, bool]:
    """
    複数楽曲のお気に入り登録状態を一括確認する。

    楽曲一覧などを表示する際に N+1 リクエストを避けるために使用する。
    1回のリクエストで最大100件を確認できる。

    Returns:
        {"song_id": is_favorite} の辞書。JSON 仕様ではオブジェクトキーは常に文字列であるため、
        数値 song_id は文字列に変換される（例: {\"123\": true}）。
        フロントエンド側では result[String(songId)] でアクセスすること。
    """
    if not data.song_ids:
        return {}
    result = batch_check_favorites(user["id"], data.song_ids)
    # JSON 仕様: オブジェクトキーは文字列のみ。フロントは String(song_id) でアクセスすること。
    return {str(song_id): is_fav for song_id, is_fav in result.items()}


# ============================================================
# お気に入りアーティスト
# ============================================================

@router.post("/favorite-artists")
def add_favorite_artist_endpoint(
    data: FavoriteArtistAdd,
    user: dict = Depends(get_current_user),
) -> dict:
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
        raise HTTPException(status_code=400, detail=f"お気に入りアーティストは{FAVORITE_ARTIST_LIMIT}組まで登録できます")
    return result


@router.delete("/favorite-artists/{artist_id}")
def remove_favorite_artist_endpoint(
    artist_id: int,
    user: dict = Depends(get_current_user),
) -> dict:
    """お気に入りアーティストを削除"""
    success = remove_favorite_artist(user["id"], artist_id)
    if success:
        return {"message": "お気に入りから削除しました"}
    raise HTTPException(status_code=404, detail="お気に入りに登録されていません")


@router.get("/favorite-artists")
def get_my_favorite_artists(user: dict = Depends(get_current_user)) -> list:
    """自分のお気に入りアーティスト一覧を取得"""
    return get_favorite_artists(user["id"])


@router.get("/favorite-artists/check/{artist_id}")
def check_favorite_artist(artist_id: int, user: dict = Depends(get_current_user)) -> dict:
    """アーティストがお気に入りに登録されているか確認"""
    return {"is_favorite": is_favorite_artist(user["id"], artist_id)}
