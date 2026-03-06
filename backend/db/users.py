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
from config import FAVORITE_ARTIST_LIMIT


# 環境変数をロード
load_dotenv()

# Supabaseクライアントの初期化
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    print("[WARN] SUPABASE_URL / SUPABASE_KEY 未設定のため認証機能は無効です")


def _get_supabase() -> Client:
    """
    Supabase クライアントを返す。

    未設定の場合は RuntimeError を送出する。
    auth.py の get_current_user / get_optional_user が先に認証を検証するため、
    保護エンドポイントでこの関数が RuntimeError を送出することは通常ない。

    Returns:
        初期化済みの Supabase クライアント。

    Raises:
        RuntimeError: Supabase が設定されていない場合。
    """
    if supabase is None:
        raise RuntimeError("Supabase が設定されていません (SUPABASE_URL / SUPABASE_KEY を確認してください)")
    return supabase


# ============================================================
# ユーザープロファイル関連
# ============================================================

def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """ユーザープロファイルを取得"""
    try:
        response = _get_supabase().table("user_profiles").select("*").eq("id", user_id).single().execute()
        return response.data
    except Exception as e:
        print(f"[ERROR] プロファイル取得失敗 (user={user_id}): {e}")
        return None


def update_user_profile(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """ユーザープロファイルを更新"""
    try:
        response = _get_supabase().table("user_profiles").update(data).eq("id", user_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"[ERROR] プロファイル更新失敗 (user={user_id}): {e}")
        return None


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
    try:
        data = {
            "user_id": user_id,
            "vocal_range_min": vocal_min,
            "vocal_range_max": vocal_max,
            "falsetto_max": falsetto,
            "source_type": source_type,
            "file_name": file_name,
            "result_json": result_json
        }
        response = _get_supabase().table("analysis_history").insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"[ERROR] 分析履歴作成失敗 (user={user_id}): {e}")
        return None


def get_analysis_history(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """ユーザーの分析履歴を取得（新しい順）"""
    try:
        response = _get_supabase().table("analysis_history").select(
            "*"
        ).eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        print(f"[ERROR] 分析履歴取得失敗 (user={user_id}): {e}")
        return []


def get_analysis_timeline(user_id: str, limit: int = 40) -> List[Dict[str, Any]]:
    """
    分析履歴タイムラインを取得する（古い順、result_json の Hz 値を含む）。

    グラフ描画用に古い順（昇順）で返す点が get_analysis_history と異なる。
    result_json には chest_min_hz / chest_max_hz / falsetto_max_hz などが含まれる。

    Args:
        user_id: Supabase ユーザー ID。
        limit: 取得する最大件数（デフォルト 40）。

    Returns:
        分析履歴レコードのリスト（古い順）。
    """
    try:
        response = (
            _get_supabase().table("analysis_history")
            .select("id, created_at, vocal_range_min, vocal_range_max, falsetto_max, result_json")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        # グラフ用に古い順（昇順）で返す
        return list(reversed(response.data))
    except Exception as e:
        print(f"[ERROR] 分析タイムライン取得失敗 (user={user_id}): {e}")
        return []


# ============================================================
# お気に入り楽曲関連
# ============================================================

def add_favorite_song(user_id: str, song_id: int) -> Optional[Dict[str, Any]]:
    """お気に入りに楽曲を追加"""
    try:
        data = {"user_id": user_id, "song_id": song_id}
        response = _get_supabase().table("favorite_songs").insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"[ERROR] お気に入り楽曲追加失敗 (user={user_id}, song={song_id}): {e}")
        return None


def remove_favorite_song(user_id: str, song_id: int) -> bool:
    """お気に入りから楽曲を削除"""
    try:
        _get_supabase().table("favorite_songs").delete().eq("user_id", user_id).eq("song_id", song_id).execute()
        return True
    except Exception:
        return False


def get_favorite_songs(user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """ユーザーのお気に入り楽曲一覧を取得"""
    try:
        response = _get_supabase().table("favorite_songs").select(
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
    except Exception as e:
        print(f"[ERROR] お気に入り楽曲取得失敗 (user={user_id}): {e}")
        return []


def is_favorite(user_id: str, song_id: int) -> bool:
    """楽曲がお気に入りに登録されているか確認"""
    try:
        response = _get_supabase().table("favorite_songs").select("id").eq(
            "user_id", user_id
        ).eq("song_id", song_id).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"[ERROR] お気に入り確認失敗 (user={user_id}, song={song_id}): {e}")
        return False


def batch_check_favorites(user_id: str, song_ids: list[int]) -> dict[int, bool]:
    """
    複数楽曲のお気に入り登録状態を一括確認する。

    楽曲一覧ページなど多数の楽曲を表示する際に N+1 リクエストを防ぐために使用する。
    Supabase の IN フィルタで1回のクエリに集約する。

    Args:
        user_id:  Supabase ユーザー ID。
        song_ids: 確認する楽曲 ID のリスト。

    Returns:
        {song_id: is_favorite} の辞書。song_ids に含まれる全 ID がキーに含まれる。
        DB エラー時は全 song_id を False として返す。
    """
    if not song_ids:
        return {}

    try:
        response = _get_supabase().table("favorite_songs").select(
            "song_id"
        ).eq("user_id", user_id).in_("song_id", song_ids).execute()

        favorited: set[int] = {row["song_id"] for row in (response.data or [])}
        return {song_id: song_id in favorited for song_id in song_ids}
    except Exception as e:
        print(f"[ERROR] お気に入り一括確認失敗 (user={user_id}): {e}")
        return {song_id: False for song_id in song_ids}


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
        count_resp = _get_supabase().table("favorite_artists").select(
            "id", count="exact"
        ).eq("user_id", user_id).execute()
        if (count_resp.count or 0) >= FAVORITE_ARTIST_LIMIT:
            return None  # 上限超過

        data = {
            "user_id": user_id,
            "artist_id": artist_id,
            "artist_name": artist_name,
        }
        response = _get_supabase().table("favorite_artists").insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"[ERROR] お気に入りアーティスト追加失敗 (user={user_id}, artist={artist_id}): {e}")
        return None


def remove_favorite_artist(user_id: str, artist_id: int) -> bool:
    """お気に入りアーティストを削除"""
    try:
        _get_supabase().table("favorite_artists").delete().eq(
            "user_id", user_id
        ).eq("artist_id", artist_id).execute()
        return True
    except Exception:
        return False


def get_favorite_artists(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """ユーザーのお気に入りアーティスト一覧を取得（登録が古い順）"""
    try:
        response = _get_supabase().table("favorite_artists").select(
            "id, artist_id, artist_name, created_at"
        ).eq("user_id", user_id).order("created_at", desc=False).limit(limit).execute()
        return response.data or []
    except Exception as e:
        print(f"[ERROR] お気に入りアーティスト取得失敗 (user={user_id}): {e}")
        return []


def is_favorite_artist(user_id: str, artist_id: int) -> bool:
    """アーティストがお気に入りに登録されているか確認"""
    try:
        response = _get_supabase().table("favorite_artists").select("id").eq(
            "user_id", user_id
        ).eq("artist_id", artist_id).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"[ERROR] お気に入りアーティスト確認失敗 (user={user_id}, artist={artist_id}): {e}")
        return False


def get_favorite_artist_ids(user_id: str) -> List[int]:
    """
    お気に入りアーティストのIDリストを返す（recommenderで使用）。
    DBエラー時は空リストを返してフォールバック。
    """
    try:
        response = _get_supabase().table("favorite_artists").select(
            "artist_id"
        ).eq("user_id", user_id).execute()
        return [row["artist_id"] for row in (response.data or [])]
    except Exception as e:
        print(f"[WARN] お気に入りアーティストID取得失敗: {e}")
        return []

def delete_analysis_record(user_id: str, record_id: str) -> bool:
    """分析履歴を削除"""
    try:
        _get_supabase().table("analysis_history").delete().eq(
            "id", record_id
        ).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        print(f"[ERROR] 分析履歴削除失敗 (user={user_id}, record={record_id}): {e}")
        return False

def update_analysis_record(user_id: str, record_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """分析履歴を更新 (file_nameなど)"""
    try:
        response = _get_supabase().table("analysis_history").update(data).eq(
            "id", record_id
        ).eq("user_id", user_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"[ERROR] 分析履歴更新失敗 (user={user_id}, record={record_id}): {e}")
        return None
