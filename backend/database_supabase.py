"""
Supabaseデータベースの接続管理とクエリ関数

楽曲・アーティスト検索とユーザーデータ（プロファイル、分析履歴、お気に入り）を提供。
"""
import os
import re
import unicodedata
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

# 環境変数をロード
load_dotenv()

# Supabaseクライアントの初期化
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URLとSUPABASE_KEYを.envファイルに設定してください")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ============================================================
# 共通ヘルパー
# ============================================================

# songs テーブルの標準SELECTカラム（artists JOINつき）
_SONG_FIELDS = (
    "id, title, artist_id, lowest_note, highest_note, "
    "falsetto_note, note, source, artists(name, slug, reading)"
)


def _hiragana_normalize(text: str) -> str:
    """カタカナをひらがなに変換して正規化"""
    text = unicodedata.normalize('NFKC', text)
    result = []
    for char in text:
        code = ord(char)
        if 0x30A1 <= code <= 0x30F6:
            result.append(chr(code - 0x60))
        else:
            result.append(char)
    return ''.join(result)


def _query_mode(query: str) -> str:
    """ひらがな/カタカナだけなら kana、それ以外は name 検索"""
    if not query:
        return "name"
    nfkc = unicodedata.normalize('NFKC', query)
    return "kana" if re.fullmatch(r"[ぁ-ゖァ-ヺーﾞﾟ]+", nfkc) else "name"


def _flatten_song(song: Dict[str, Any]) -> Dict[str, Any]:
    """Supabaseの songs(artists(...)) レスポンスをフラットに変換

    SQLite版 database.py と同じフィールド名で返す。
    """
    artists_data = song.get("artists") or {}
    return {
        **{k: v for k, v in song.items() if k != "artists"},
        "artist": artists_data.get("name"),
        "artist_slug": artists_data.get("slug"),
        "artist_reading": artists_data.get("reading"),
    }


# ============================================================
# 楽曲関連のクエリ関数
# ============================================================

def search_songs(query: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    """
    曲名またはアーティスト名・ふりがなであいまい検索。

    PostgRESTの制限により、タイトル検索とアーティスト検索を分けて実行し、
    重複をIDで除外する。
    """
    # 曲名で検索
    title_resp = supabase.table("songs").select(
        _SONG_FIELDS
    ).ilike("title", f"%{query}%").range(offset, offset + limit - 1).execute()

    # アーティスト名・ふりがなで検索
    normalized = _hiragana_normalize(query)
    name_artists = supabase.table("artists").select("id").ilike(
        "name", f"%{query}%"
    ).execute()
    reading_artists = supabase.table("artists").select("id").ilike(
        "reading", f"%{normalized}%"
    ).execute()

    artist_ids: set[int] = set()
    for a in (name_artists.data or []) + (reading_artists.data or []):
        artist_ids.add(a["id"])

    artist_songs: List[Dict[str, Any]] = []
    for artist_id in artist_ids:
        resp = supabase.table("songs").select(
            _SONG_FIELDS
        ).eq("artist_id", artist_id).range(0, limit - 1).execute()
        artist_songs.extend(resp.data or [])

    # 重複除去（IDベース）
    seen_ids: set[int] = set()
    merged: List[Dict[str, Any]] = []
    for song in (title_resp.data or []) + artist_songs:
        if song["id"] not in seen_ids:
            seen_ids.add(song["id"])
            merged.append(song)

    return [_flatten_song(s) for s in merged[:limit]]


def count_songs(query: str = "") -> int:
    """楽曲総数を取得（検索クエリ対応）"""
    if not query:
        resp = supabase.table("songs").select(
            "id", count="exact"
        ).limit(0).execute()
        return resp.count or 0

    # クエリあり: タイトル + アーティスト名 + ふりがなで検索しIDを集める
    title_resp = supabase.table("songs").select("id").ilike(
        "title", f"%{query}%"
    ).execute()

    normalized = _hiragana_normalize(query)
    name_artists = supabase.table("artists").select("id").ilike(
        "name", f"%{query}%"
    ).execute()
    reading_artists = supabase.table("artists").select("id").ilike(
        "reading", f"%{normalized}%"
    ).execute()

    artist_ids: set[int] = set()
    for a in (name_artists.data or []) + (reading_artists.data or []):
        artist_ids.add(a["id"])

    song_ids: set[int] = {s["id"] for s in (title_resp.data or [])}
    for artist_id in artist_ids:
        resp = supabase.table("songs").select("id").eq(
            "artist_id", artist_id
        ).execute()
        for s in (resp.data or []):
            song_ids.add(s["id"])

    return len(song_ids)


def get_song(song_id: int) -> Optional[Dict[str, Any]]:
    """IDで楽曲を取得"""
    response = supabase.table("songs").select(
        _SONG_FIELDS
    ).eq("id", song_id).single().execute()

    if response.data:
        return _flatten_song(response.data)
    return None


def get_all_songs(limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    """全曲を取得（ページネーション対応）"""
    response = supabase.table("songs").select(
        _SONG_FIELDS
    ).range(offset, offset + limit - 1).execute()

    return [_flatten_song(s) for s in response.data]


def get_artist(artist_id: int) -> Optional[Dict[str, Any]]:
    """IDでアーティストを取得"""
    response = supabase.table("artists").select(
        "id, name, slug, song_count, reading"
    ).eq("id", artist_id).single().execute()
    return response.data


def get_artists(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """アーティスト一覧を取得（song_count > 0、reading順）"""
    response = supabase.table("artists").select(
        "id, name, slug, song_count, reading"
    ).gt("song_count", 0).order("reading").range(
        offset, offset + limit - 1
    ).execute()
    return response.data


def get_artist_songs(artist_id: int) -> List[Dict[str, Any]]:
    """アーティストの全曲を取得"""
    response = supabase.table("songs").select(
        _SONG_FIELDS
    ).eq("artist_id", artist_id).order("title").execute()

    return [_flatten_song(s) for s in response.data]


def count_artists(query: str = "") -> int:
    """アーティスト総数を取得（検索クエリ対応）"""
    if not query:
        resp = supabase.table("artists").select(
            "id", count="exact"
        ).gt("song_count", 0).limit(0).execute()
        return resp.count or 0

    mode = _query_mode(query)
    if mode == "kana":
        normalized = _hiragana_normalize(query)
        resp = supabase.table("artists").select(
            "id", count="exact"
        ).gt("song_count", 0).ilike(
            "reading", f"{normalized}%"
        ).limit(0).execute()
    else:
        resp = supabase.table("artists").select(
            "id", count="exact"
        ).gt("song_count", 0).ilike(
            "name", f"%{query}%"
        ).limit(0).execute()

    return resp.count or 0


def search_artists(query: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """アーティスト検索: かな入力なら reading 前方一致、その他は name 部分一致"""
    mode = _query_mode(query)

    if mode == "kana":
        normalized = _hiragana_normalize(query)
        response = supabase.table("artists").select(
            "id, name, slug, song_count, reading"
        ).gt("song_count", 0).ilike(
            "reading", f"{normalized}%"
        ).order("reading").range(offset, offset + limit - 1).execute()
    else:
        response = supabase.table("artists").select(
            "id, name, slug, song_count, reading"
        ).gt("song_count", 0).ilike(
            "name", f"%{query}%"
        ).order("reading").range(offset, offset + limit - 1).execute()

    return response.data


# ============================================================
# ユーザープロファイル関連
# ============================================================

def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """ユーザープロファイルを取得"""
    response = supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()
    return response.data


def update_user_profile(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """ユーザープロファイルを更新"""
    response = supabase.table("user_profiles").update(data).eq("id", user_id).execute()
    return response.data[0] if response.data else None


def update_vocal_range(
    user_id: str,
    vocal_min: Optional[str] = None,
    vocal_max: Optional[str] = None,
    falsetto: Optional[str] = None
) -> Dict[str, Any]:
    """ユーザーの最新声域を更新"""
    data = {}
    if vocal_min:
        data["current_vocal_range_min"] = vocal_min
    if vocal_max:
        data["current_vocal_range_max"] = vocal_max
    if falsetto:
        data["current_falsetto_max"] = falsetto

    return update_user_profile(user_id, data)


# ============================================================
# 分析履歴関連
# ============================================================

def create_analysis_record(
    user_id: str,
    vocal_min: Optional[str],
    vocal_max: Optional[str],
    falsetto: Optional[str],
    source_type: str,
    file_name: Optional[str] = None,
    result_json: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """分析履歴を新規作成"""
    data = {
        "user_id": user_id,
        "vocal_range_min": vocal_min,
        "vocal_range_max": vocal_max,
        "falsetto_max": falsetto,
        "source_type": source_type,
        "file_name": file_name,
        "result_json": result_json
    }
    response = supabase.table("analysis_history").insert(data).execute()
    return response.data[0] if response.data else None


def get_analysis_history(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """ユーザーの分析履歴を取得（新しい順）"""
    response = supabase.table("analysis_history").select(
        "*"
    ).eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
    return response.data


# ============================================================
# お気に入り楽曲関連
# ============================================================

def add_favorite_song(user_id: str, song_id: int) -> Optional[Dict[str, Any]]:
    """お気に入りに楽曲を追加"""
    try:
        data = {"user_id": user_id, "song_id": song_id}
        response = supabase.table("favorite_songs").insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"お気に入り追加エラー: {e}")
        return None


def remove_favorite_song(user_id: str, song_id: int) -> bool:
    """お気に入りから楽曲を削除"""
    try:
        supabase.table("favorite_songs").delete().eq("user_id", user_id).eq("song_id", song_id).execute()
        return True
    except Exception:
        return False


def get_favorite_songs(user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """ユーザーのお気に入り楽曲一覧を取得（Supabaseから楽曲詳細をJOIN）"""
    response = supabase.table("favorite_songs").select(
        "id, song_id, created_at, songs(id, title, lowest_note, highest_note, falsetto_note, artists(name))"
    ).eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()

    favorites = []
    for fav in response.data:
        song = fav.get("songs")
        if not song:
            continue
        artists_data = song.get("artists") or {}
        favorites.append({
            "favorite_id": fav["id"],
            "created_at": fav["created_at"],
            "song_id": song["id"],
            "title": song["title"],
            "artist": artists_data.get("name"),
            "lowest_note": song.get("lowest_note"),
            "highest_note": song.get("highest_note"),
            "falsetto_note": song.get("falsetto_note"),
        })

    return favorites


def is_favorite(user_id: str, song_id: int) -> bool:
    """楽曲がお気に入りに登録されているか確認"""
    response = supabase.table("favorite_songs").select("id").eq(
        "user_id", user_id
    ).eq("song_id", song_id).execute()
    return len(response.data) > 0


# ============================================================
# お気に入りアーティスト関連
# ============================================================

def add_favorite_artist(user_id: str, artist_id: int, artist_name: str) -> Optional[Dict[str, Any]]:
    """
    お気に入りアーティストを追加（上限10組）。
    既に登録済みの場合はNoneを返す。
    """
    try:
        # 上限チェック
        count_resp = supabase.table("favorite_artists").select(
            "id", count="exact"
        ).eq("user_id", user_id).execute()
        if (count_resp.count or 0) >= 10:
            return None  # 上限超過

        data = {
            "user_id": user_id,
            "artist_id": artist_id,
            "artist_name": artist_name,
        }
        response = supabase.table("favorite_artists").insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"お気に入りアーティスト追加エラー: {e}")
        return None


def remove_favorite_artist(user_id: str, artist_id: int) -> bool:
    """お気に入りアーティストを削除"""
    try:
        supabase.table("favorite_artists").delete().eq(
            "user_id", user_id
        ).eq("artist_id", artist_id).execute()
        return True
    except Exception:
        return False


def get_favorite_artists(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """ユーザーのお気に入りアーティスト一覧を取得（登録が古い順）"""
    response = supabase.table("favorite_artists").select(
        "id, artist_id, artist_name, created_at"
    ).eq("user_id", user_id).order("created_at", desc=False).limit(limit).execute()
    return response.data or []


def is_favorite_artist(user_id: str, artist_id: int) -> bool:
    """アーティストがお気に入りに登録されているか確認"""
    response = supabase.table("favorite_artists").select("id").eq(
        "user_id", user_id
    ).eq("artist_id", artist_id).execute()
    return len(response.data) > 0


def get_favorite_artist_ids(user_id: str) -> List[int]:
    """
    お気に入りアーティストのIDリストを返す（recommenderで使用）。
    DBエラー時は空リストを返してフォールバック。
    """
    try:
        response = supabase.table("favorite_artists").select(
            "artist_id"
        ).eq("user_id", user_id).execute()
        return [row["artist_id"] for row in (response.data or [])]
    except Exception as e:
        print(f"[WARN] お気に入りアーティストID取得失敗: {e}")
        return []

def delete_analysis_record(user_id: str, record_id: str) -> bool:
    """分析履歴を削除"""
    try:
        supabase.table("analysis_history").delete().eq(
            "id", record_id
        ).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        print(f"履歴削除エラー: {e}")
        return False

def update_analysis_record(user_id: str, record_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """分析履歴を更新 (file_nameなど)"""
    try:
        response = supabase.table("analysis_history").update(data).eq(
            "id", record_id
        ).eq("user_id", user_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"履歴更新エラー: {e}")
        return None


def get_integrated_vocal_range(user_id: str, limit: int = 20) -> Optional[Dict[str, Any]]:
    """
    直近N件の分析履歴から統合音域と総合分析を計算

    Args:
        user_id: ユーザーID
        limit: 統合する履歴の件数（デフォルト20件）

    Returns:
        統合音域・タイプ・おすすめ曲・アーティスト・歌唱力指標を含む辞書
        データがない場合はNone
    """
    try:
        from note_converter import hz_to_label_and_hz
        from recommender import recommend_songs, find_similar_artists, classify_voice_type

        # 直近N件の履歴を取得
        history = get_analysis_history(user_id, limit=limit)

        if not history:
            return None

        # Hz値のリストを収集
        chest_min_values = []
        chest_max_values = []
        falsetto_max_values = []
        overall_min_values = []
        overall_max_values = []
        chest_ratio_values = []

        # 歌唱力指標の収集
        range_scores = []
        stability_scores = []
        expression_scores = []
        overall_scores = []

        valid_count = 0
        for record in history:
            # result_jsonがある場合はそこから取得
            if record.get("result_json"):
                result = record["result_json"]
                if result.get("chest_min_hz"):
                    chest_min_values.append(result["chest_min_hz"])
                if result.get("chest_max_hz"):
                    chest_max_values.append(result["chest_max_hz"])
                if result.get("falsetto_max_hz"):
                    falsetto_max_values.append(result["falsetto_max_hz"])
                if result.get("overall_min_hz"):
                    overall_min_values.append(result["overall_min_hz"])
                if result.get("overall_max_hz"):
                    overall_max_values.append(result["overall_max_hz"])
                if result.get("chest_ratio") is not None:
                    chest_ratio_values.append(result["chest_ratio"])

                # 歌唱力指標
                if result.get("singing_analysis"):
                    sa = result["singing_analysis"]
                    if sa.get("range_score") is not None:
                        range_scores.append(sa["range_score"])
                    if sa.get("stability_score") is not None:
                        stability_scores.append(sa["stability_score"])
                    if sa.get("expression_score") is not None:
                        expression_scores.append(sa["expression_score"])
                    if sa.get("overall_score") is not None:
                        overall_scores.append(sa["overall_score"])

                valid_count += 1
            # 古い形式の場合は直接取得
            elif record.get("vocal_range_min_hz") or record.get("vocal_range_max_hz"):
                if record.get("vocal_range_min_hz"):
                    overall_min_values.append(record["vocal_range_min_hz"])
                    chest_min_values.append(record["vocal_range_min_hz"])
                if record.get("vocal_range_max_hz"):
                    overall_max_values.append(record["vocal_range_max_hz"])
                    chest_max_values.append(record["vocal_range_max_hz"])
                if record.get("falsetto_max_hz"):
                    falsetto_max_values.append(record["falsetto_max_hz"])
                valid_count += 1

        if valid_count == 0:
            return None

        # 統合値を計算（最小値と最大値を採用）
        result = {
            "data_count": valid_count,
            "limit": limit
        }

        # 音域情報
        if overall_min_values:
            overall_min_hz = min(overall_min_values)
            overall_min_label, overall_min_hz_defined = hz_to_label_and_hz(overall_min_hz)
            result["overall_min"] = overall_min_label
            result["overall_min_hz"] = overall_min_hz_defined

        if overall_max_values:
            overall_max_hz = max(overall_max_values)
            overall_max_label, overall_max_hz_defined = hz_to_label_and_hz(overall_max_hz)
            result["overall_max"] = overall_max_label
            result["overall_max_hz"] = overall_max_hz_defined

        chest_min_hz_defined = None
        if chest_min_values:
            chest_min_hz = min(chest_min_values)
            chest_min_label, chest_min_hz_defined = hz_to_label_and_hz(chest_min_hz)
            result["chest_min"] = chest_min_label
            result["chest_min_hz"] = chest_min_hz_defined

        chest_max_hz_defined = None
        if chest_max_values:
            chest_max_hz = max(chest_max_values)
            chest_max_label, chest_max_hz_defined = hz_to_label_and_hz(chest_max_hz)
            result["chest_max"] = chest_max_label
            result["chest_max_hz"] = chest_max_hz_defined

        falsetto_max_hz_defined = None
        if falsetto_max_values:
            falsetto_max_hz = max(falsetto_max_values)
            falsetto_max_label, falsetto_max_hz_defined = hz_to_label_and_hz(falsetto_max_hz)
            result["falsetto_max"] = falsetto_max_label
            result["falsetto_max_hz"] = falsetto_max_hz_defined

        # 地声比率の平均
        avg_chest_ratio = sum(chest_ratio_values) / len(chest_ratio_values) if chest_ratio_values else 0.8
        result["chest_ratio"] = avg_chest_ratio
        result["falsetto_ratio"] = 1.0 - avg_chest_ratio

        # 歌唱力指標の平均
        if range_scores or stability_scores or expression_scores or overall_scores:
            result["singing_analysis"] = {}
            if range_scores:
                result["singing_analysis"]["range_score"] = sum(range_scores) / len(range_scores)
            if stability_scores:
                result["singing_analysis"]["stability_score"] = sum(stability_scores) / len(stability_scores)
            if expression_scores:
                result["singing_analysis"]["expression_score"] = sum(expression_scores) / len(expression_scores)
            if overall_scores:
                result["singing_analysis"]["overall_score"] = sum(overall_scores) / len(overall_scores)

            # 音域の半音数を計算
            if chest_min_hz_defined and chest_max_hz_defined:
                import math
                result["singing_analysis"]["range_semitones"] = round(
                    12 * math.log2(chest_max_hz_defined / chest_min_hz_defined)
                )

        # 声質タイプを判定（chest_avg_hzを計算）
        if chest_min_hz_defined and chest_max_hz_defined:
            import math
            chest_avg_hz = math.sqrt(chest_min_hz_defined * chest_max_hz_defined)  # 幾何平均

            # voice_typeを分類
            voice_type_data = classify_voice_type(
                chest_min_hz_defined,
                chest_max_hz_defined,
                chest_avg_hz,
                falsetto_max_hz_defined,
                avg_chest_ratio
            )
            result["voice_type"] = voice_type_data

            # 似ているアーティストを取得
            similar_artists = find_similar_artists(
                chest_min_hz_defined,
                chest_max_hz_defined,
                chest_avg_hz,
                limit=5
            )
            result["similar_artists"] = similar_artists

            # おすすめ曲を取得
            fav_artist_ids = get_favorite_artist_ids(user_id)
            recommended_songs = recommend_songs(
                chest_min_hz_defined,
                chest_max_hz_defined,
                chest_avg_hz,
                falsetto_max_hz_defined,
                limit=10,
                favorite_artist_ids=fav_artist_ids
            )
            result["recommended_songs"] = recommended_songs

        return result

    except Exception as e:
        print(f"統合音域計算エラー: {e}")
        import traceback
        traceback.print_exc()
        return None
