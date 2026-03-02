"""
db/users.py — Supabaseユーザーデータの接続管理とクエリ関数

認証・ユーザープロファイル・分析履歴・お気に入り楽曲/アーティストを管理する。
楽曲カタログ（SQLite）との結合が必要な場合は db.songs を参照する。
"""
import os
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from db.songs import get_songs_by_ids
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
    if vocal_min is not None:
        data["current_vocal_range_min"] = vocal_min
    if vocal_max is not None:
        data["current_vocal_range_max"] = vocal_max
    if falsetto is not None:
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
    """ユーザーのお気に入り楽曲一覧を取得"""
    response = supabase.table("favorite_songs").select(
        "id, song_id, created_at"
    ).eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()

    if not response.data:
        return []

    # song_id を一括取得して N+1 を回避
    song_ids = [fav["song_id"] for fav in response.data]
    songs_map = get_songs_by_ids(song_ids)

    favorites = []
    for fav in response.data:
        song = songs_map.get(fav["song_id"])
        # SQLite側に曲が存在すればリストに追加
        if song:
            favorites.append({
                "favorite_id": fav["id"],
                "created_at": fav["created_at"],
                "song_id": song.get("id"),
                "title": song.get("title"),
                "artist": song.get("artist"),
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
