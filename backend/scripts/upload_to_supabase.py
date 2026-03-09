"""
SQLite songs.db のデータを Supabase にアップロードするスクリプト

処理:
  1. 接続テスト
  2. SQLite から artists / songs を読み込み
  3. Supabase にバッチ upsert
  4. SERIAL シーケンスをリセット
  5. favorite_songs の song_id 整合性チェック
  6. バリデーション

使用方法:
  SUPABASE_KEY には service_role key を使用すること（RLS バイパス用）

  cd backend
  source venv/bin/activate
  python scripts/upload_to_supabase.py
"""
import os
import sqlite3
import sys

# backend ディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[ERROR] SUPABASE_URL と SUPABASE_KEY を .env に設定してください")
    print("  ※ RLS バイパスのため service_role key を使用してください")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "songs.db")
BATCH_SIZE = 100


def load_from_sqlite() -> tuple[list[dict], list[dict]]:
    """SQLite からアーティストと楽曲を読み込む"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cur = conn.cursor()
    cur.execute("SELECT id, name, slug, song_count, reading FROM artists ORDER BY id")
    artists = [dict(row) for row in cur.fetchall()]

    cur.execute(
        "SELECT id, title, artist_id, lowest_note, highest_note, "
        "falsetto_note, note, source FROM songs ORDER BY id"
    )
    songs = [dict(row) for row in cur.fetchall()]

    conn.close()
    return artists, songs


def check_connection() -> bool:
    """接続テスト"""
    try:
        resp = supabase.table("artists").select("id", count="exact").limit(0).execute()
        print(f"[OK] Supabase 接続成功 (artists: {resp.count}件)")
        resp = supabase.table("songs").select("id", count="exact").limit(0).execute()
        print(f"[OK] songs: {resp.count}件")
        return True
    except Exception as e:
        print(f"[ERROR] 接続失敗: {e}")
        return False


def upload_artists(artists: list[dict]) -> int:
    """アーティストをバッチアップロード"""
    print(f"\n[STEP 1] アーティストアップロード ({len(artists)}件)...")

    uploaded = 0
    for i in range(0, len(artists), BATCH_SIZE):
        batch = artists[i:i + BATCH_SIZE]
        supabase.table("artists").upsert(batch, on_conflict="id").execute()
        uploaded += len(batch)
        print(f"  {uploaded}/{len(artists)} 件完了")

    return uploaded


def upload_songs(songs: list[dict]) -> int:
    """楽曲をバッチアップロード"""
    print(f"\n[STEP 2] 楽曲アップロード ({len(songs)}件)...")

    uploaded = 0
    for i in range(0, len(songs), BATCH_SIZE):
        batch = songs[i:i + BATCH_SIZE]
        supabase.table("songs").upsert(batch, on_conflict="id").execute()
        uploaded += len(batch)
        if uploaded % 500 == 0 or uploaded == len(songs):
            print(f"  {uploaded}/{len(songs)} 件完了")

    return uploaded


def reset_sequences() -> None:
    """SERIAL シーケンスをリセット（次の INSERT が正しい ID を使うように）"""
    print("\n[STEP 3] シーケンスリセット...")
    try:
        supabase.rpc("reset_sequences", {}).execute()
        print("  [OK] RPC でリセット完了")
    except Exception:
        print("  [WARN] RPC が未定義です。ダッシュボードで以下を実行してください:")
        print("    SELECT setval('artists_id_seq', (SELECT COALESCE(MAX(id), 1) FROM artists));")
        print("    SELECT setval('songs_id_seq', (SELECT COALESCE(MAX(id), 1) FROM songs));")


def check_favorites() -> int:
    """favorite_songs の参照整合性チェック"""
    print("\n[STEP 4] お気に入り参照整合性チェック...")

    fav_resp = supabase.table("favorite_songs").select("id, song_id").execute()
    favorites = fav_resp.data or []
    if not favorites:
        print("  お気に入りデータなし — スキップ")
        return 0

    print(f"  お気に入り楽曲: {len(favorites)}件")

    # Supabase 上の全 song ID を取得
    all_songs_resp = supabase.table("songs").select("id").execute()
    valid_song_ids = {s["id"] for s in (all_songs_resp.data or [])}

    invalid_refs = 0
    for fav in favorites:
        if fav["song_id"] not in valid_song_ids:
            print(f"  [WARN] 参照先なし: favorite_id={fav['id']}, song_id={fav['song_id']}")
            invalid_refs += 1

    if invalid_refs > 0:
        print(f"  [WARN] 無効な参照: {invalid_refs}件")
    else:
        print("  [OK] 全参照が有効")

    return invalid_refs


def validate(expected_artists: int, expected_songs: int) -> bool:
    """アップロード結果のバリデーション"""
    print("\n[STEP 5] バリデーション...")

    artists_resp = supabase.table("artists").select("id", count="exact").limit(0).execute()
    songs_resp = supabase.table("songs").select("id", count="exact").limit(0).execute()
    a_count = artists_resp.count or 0
    s_count = songs_resp.count or 0
    print(f"  artists: {a_count}件 (期待値: {expected_artists})")
    print(f"  songs: {s_count}件 (期待値: {expected_songs})")

    ok = True
    if a_count != expected_artists:
        print(f"  [WARN] artists 件数不一致")
        ok = False
    if s_count != expected_songs:
        print(f"  [WARN] songs 件数不一致")
        ok = False

    if ok:
        print("  [OK] 件数一致")

    return ok


def main() -> None:
    """メイン処理"""
    print("=" * 60)
    print("PitchScout SQLite → Supabase データアップロード")
    print("=" * 60)

    if not check_connection():
        sys.exit(1)

    # SQLite からデータ読み込み
    artists, songs = load_from_sqlite()
    print(f"\n[INFO] SQLite: artists={len(artists)}件, songs={len(songs)}件")

    # 既存データ確認
    artists_resp = supabase.table("artists").select("id", count="exact").limit(0).execute()
    songs_resp = supabase.table("songs").select("id", count="exact").limit(0).execute()
    if (artists_resp.count or 0) > 0 or (songs_resp.count or 0) > 0:
        print(f"\n[WARN] 既存データがあります (artists={artists_resp.count}, songs={songs_resp.count})")
        answer = input("上書きしますか？ (y/N): ").strip().lower()
        if answer != "y":
            print("中断しました")
            sys.exit(0)

    # アップロード
    upload_artists(artists)
    upload_songs(songs)
    reset_sequences()
    check_favorites()

    # バリデーション
    valid = validate(len(artists), len(songs))

    print("\n" + "=" * 60)
    if valid:
        print("アップロード完了!")
    else:
        print("アップロード完了（警告あり — 上記を確認してください）")
    print("=" * 60)


if __name__ == "__main__":
    main()
