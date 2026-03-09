"""
修正済みCSV（artists_check_fixed.csv / songs_check_fixed.csv）を Supabase にアップロードするスクリプト

処理フロー:
  1. CSV読み込み＋ID振り直し（1から連番）
  2. Supabase接続確認
  3. お気に入りデータのバックアップ（名前ベースで保持）
  4. 既存データクリア（TRUNCATE CASCADE）
  5. artists アップロード（バッチupsert）
  6. songs アップロード（バッチupsert）
  7. シーケンスリセット
  8. お気に入り自動修復（名前→新IDで復元）
  9. バリデーション

使用方法:
  SUPABASE_KEY には service_role key を使用すること（RLS バイパス用）

  cd backend
  source venv/bin/activate
  python scripts/upload_csv_to_supabase.py

  --dry-run オプションでアップロードせずにCSV読み込みと変換の確認のみ実行:
  python scripts/upload_csv_to_supabase.py --dry-run
"""

import csv
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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SCRIPT_DIR, "..")
ARTISTS_CSV = os.path.join(SCRIPT_DIR, "output", "artists_check_fixed.csv")
SONGS_CSV = os.path.join(SCRIPT_DIR, "output", "songs_check_fixed.csv")
# SQLiteフォールバック用: Supabase の songs/artists が空の場合に旧IDの逆引きに使用
SQLITE_DB = os.path.join(BACKEND_DIR, "songs.db")
BATCH_SIZE = 100


def load_and_reassign_ids() -> tuple[list[dict], list[dict], dict[str, int]]:
    """CSVを読み込み、IDを1から連番で振り直す。

    Returns:
        artists: 新IDが振られたアーティストリスト
        songs: 新IDが振られた楽曲リスト（artist_id変換済み）
        name_to_new_id: アーティスト名→新IDのマッピング
    """
    # --- artists ---
    artists: list[dict] = []
    name_to_new_id: dict[str, int] = {}

    with open(ARTISTS_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for new_id, row in enumerate(reader, start=1):
            name = row["name"]
            name_to_new_id[name] = new_id
            artists.append({
                "id": new_id,
                "name": name,
                "slug": row["slug"],
                "song_count": int(row["song_count"]) if row["song_count"] else 0,
                "reading": row.get("reading") or None,
            })

    print(f"[INFO] artists CSV: {len(artists)}件読み込み（新ID: 1〜{len(artists)}）")

    # --- songs ---
    songs: list[dict] = []
    unmatched_artists: set[str] = set()

    with open(SONGS_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for new_id, row in enumerate(reader, start=1):
            artist_name = row["artist_name"]
            artist_id = name_to_new_id.get(artist_name)

            if artist_id is None:
                unmatched_artists.add(artist_name)
                continue

            songs.append({
                "id": new_id,
                "title": row["title"],
                "artist_id": artist_id,
                "lowest_note": row.get("lowest_note") or None,
                "highest_note": row.get("highest_note") or None,
                "falsetto_note": row.get("falsetto_note") or None,
                "note": None,
                "source": row.get("source") or "voice-key.news",
            })

    if unmatched_artists:
        print(f"[WARN] artists に存在しない artist_name が {len(unmatched_artists)}件:")
        for name in sorted(unmatched_artists):
            print(f"  - {name}")

    print(f"[INFO] songs CSV: {len(songs)}件読み込み（新ID: 1〜{len(songs)}）")

    return artists, songs, name_to_new_id


def check_connection(supabase: Client) -> bool:
    """Supabase接続テスト。"""
    try:
        resp = supabase.table("artists").select("id", count="exact").limit(0).execute()
        print(f"[OK] Supabase 接続成功 (現在の artists: {resp.count}件)")
        resp = supabase.table("songs").select("id", count="exact").limit(0).execute()
        print(f"[OK] 現在の songs: {resp.count}件")
        return True
    except Exception as e:
        print(f"[ERROR] 接続失敗: {e}")
        return False


def backup_favorites(supabase: Client) -> tuple[list[dict], list[dict]]:
    """お気に入りデータを名前ベースでバックアップする。

    Returns:
        fav_songs_backup: [{user_id, title, artist_name}, ...]
        fav_artists_backup: [{user_id, artist_name}, ...]
    """
    print("\n[STEP 1] お気に入りデータのバックアップ...")

    # --- favorite_songs ---
    fav_songs_resp = supabase.table("favorite_songs").select(
        "user_id, song_id"
    ).execute()
    fav_songs_raw = fav_songs_resp.data or []

    fav_songs_backup: list[dict] = []
    artist_id_to_name: dict[int, str] = {}
    song_map: dict[int, dict] = {}
    if fav_songs_raw:
        # 現在の Supabase songs テーブルから song_id → (title, artist_name) を取得
        songs_resp = supabase.table("songs").select(
            "id, title, artist_id"
        ).execute()
        supabase_songs = songs_resp.data or []

        artists_resp = supabase.table("artists").select("id, name").execute()
        supabase_artists = artists_resp.data or []

        # Supabase の songs/artists が空の場合、SQLite をフォールバックとして使用
        # （本番環境では songs/artists テーブルが空でもお気に入りデータが存在するため）
        if not supabase_songs or not supabase_artists:
            print("  [INFO] Supabase songs/artists が空 → SQLite フォールバックを使用")
            if not os.path.exists(SQLITE_DB):
                print(f"  [ERROR] SQLite DB が見つかりません: {SQLITE_DB}")
                print(f"  お気に入り楽曲の名前解決ができないため、復元をスキップします")
                fav_songs_raw = []
            else:
                conn = sqlite3.connect(SQLITE_DB)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()

                # SQLite から song_id → (title, artist_id) のマップを構築
                cur.execute("SELECT id, title, artist_id FROM songs")
                song_map = {row["id"]: dict(row) for row in cur.fetchall()}

                # SQLite から artist_id → name のマップを構築
                cur.execute("SELECT id, name FROM artists")
                artist_id_to_name = {row["id"]: row["name"] for row in cur.fetchall()}

                conn.close()
                print(f"  [INFO] SQLite から {len(song_map)}曲, {len(artist_id_to_name)}アーティスト読み込み")
        else:
            song_map = {s["id"]: s for s in supabase_songs}
            artist_id_to_name = {
                a["id"]: a["name"] for a in supabase_artists
            }

        for fav in fav_songs_raw:
            song = song_map.get(fav["song_id"])
            if song:
                artist_name = artist_id_to_name.get(song["artist_id"], "")
                fav_songs_backup.append({
                    "user_id": fav["user_id"],
                    "title": song["title"],
                    "artist_name": artist_name,
                })

        print(f"  favorite_songs: {len(fav_songs_raw)}件 → {len(fav_songs_backup)}件バックアップ")
    else:
        print("  favorite_songs: 0件 — スキップ")

    # --- favorite_artists ---
    fav_artists_resp = supabase.table("favorite_artists").select(
        "user_id, artist_id, artist_name"
    ).execute()
    fav_artists_raw = fav_artists_resp.data or []

    # favorite_artists 用に artist_id → name マップを確保
    if not artist_id_to_name:
        # まだ artist_id_to_name が構築されていない場合
        artists_resp = supabase.table("artists").select("id, name").execute()
        supabase_artists = artists_resp.data or []

        if supabase_artists:
            artist_id_to_name = {
                a["id"]: a["name"] for a in supabase_artists
            }
        elif os.path.exists(SQLITE_DB):
            # SQLite フォールバック
            print("  [INFO] artist_id → name マップに SQLite フォールバックを使用")
            conn = sqlite3.connect(SQLITE_DB)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM artists")
            artist_id_to_name = {row["id"]: row["name"] for row in cur.fetchall()}
            conn.close()

    fav_artists_backup: list[dict] = []
    if fav_artists_raw:

        for fav in fav_artists_raw:
            # favorite_artists テーブルには artist_name カラムがあるので優先使用
            name = fav.get("artist_name") or artist_id_to_name.get(fav["artist_id"])
            if name:
                fav_artists_backup.append({
                    "user_id": fav["user_id"],
                    "artist_name": name,
                })

        print(f"  favorite_artists: {len(fav_artists_raw)}件 → {len(fav_artists_backup)}件バックアップ")
    else:
        print("  favorite_artists: 0件 — スキップ")

    return fav_songs_backup, fav_artists_backup


def truncate_data(supabase: Client) -> None:
    """既存データをTRUNCATE CASCADE で削除する。"""
    print("\n[STEP 2] 既存データクリア...")

    # RPC で TRUNCATE を実行（service_role key で RLS バイパス）
    # favorite テーブルは CASCADE で自動削除される
    # supabase-py には直接 TRUNCATE がないため、delete で全件削除
    # 順序: FK依存の子テーブルから先に削除
    tables_to_clear = ["favorite_songs", "favorite_artists", "songs", "artists"]

    for table in tables_to_clear:
        try:
            # neq で全件マッチさせて削除
            # artists/songs は id > 0、favorites は id != '' で全件マッチ
            if table in ("artists", "songs"):
                supabase.table(table).delete().gt("id", -1).execute()
            else:
                supabase.table(table).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            count_resp = supabase.table(table).select("id", count="exact").limit(0).execute()
            print(f"  {table}: クリア完了（残り: {count_resp.count}件）")
        except Exception as e:
            print(f"  [ERROR] {table} のクリアに失敗: {e}")
            raise


def upload_artists(supabase: Client, artists: list[dict]) -> int:
    """アーティストをバッチアップロードする。"""
    print(f"\n[STEP 3] アーティストアップロード ({len(artists)}件)...")

    uploaded = 0
    for i in range(0, len(artists), BATCH_SIZE):
        batch = artists[i:i + BATCH_SIZE]
        supabase.table("artists").upsert(batch, on_conflict="id").execute()
        uploaded += len(batch)
        if uploaded % 500 == 0 or uploaded == len(artists):
            print(f"  {uploaded}/{len(artists)} 件完了")

    return uploaded


def upload_songs(supabase: Client, songs: list[dict]) -> int:
    """楽曲をバッチアップロードする。"""
    print(f"\n[STEP 4] 楽曲アップロード ({len(songs)}件)...")

    uploaded = 0
    for i in range(0, len(songs), BATCH_SIZE):
        batch = songs[i:i + BATCH_SIZE]
        supabase.table("songs").upsert(batch, on_conflict="id").execute()
        uploaded += len(batch)
        if uploaded % 500 == 0 or uploaded == len(songs):
            print(f"  {uploaded}/{len(songs)} 件完了")

    return uploaded


def reset_sequences(supabase: Client, max_artist_id: int, max_song_id: int) -> None:
    """SERIALシーケンスをリセットする（次のINSERTが max(id)+1 を使うように）。"""
    print("\n[STEP 5] シーケンスリセット...")
    try:
        supabase.rpc("reset_sequences", {}).execute()
        print("  [OK] RPC でリセット完了")
    except Exception:
        print("  [WARN] RPC 'reset_sequences' が未定義です")
        print("  Supabase SQL Editor で以下を実行してください:")
        print(f"    SELECT setval('artists_id_seq', {max_artist_id});")
        print(f"    SELECT setval('songs_id_seq', {max_song_id});")


def fetch_all_rows(supabase: Client, table: str, columns: str) -> list[dict]:
    """Supabase のページネーション制限（1000件）を超えて全件取得する。

    Args:
        supabase: Supabase クライアント
        table: テーブル名
        columns: 取得カラム（例: "id, title, artist_id"）

    Returns:
        全レコードのリスト
    """
    all_rows: list[dict] = []
    page_size = 1000
    offset = 0
    while True:
        resp = supabase.table(table).select(columns).range(offset, offset + page_size - 1).execute()
        batch = resp.data or []
        all_rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return all_rows


def restore_favorites(
    supabase: Client,
    fav_songs_backup: list[dict],
    fav_artists_backup: list[dict],
    name_to_new_id: dict[str, int],
) -> None:
    """バックアップしたお気に入りを新IDで復元する。"""
    print("\n[STEP 6] お気に入り自動修復...")

    if not fav_songs_backup and not fav_artists_backup:
        print("  バックアップデータなし — スキップ")
        return

    # --- 新テーブルから逆引きマップを構築 ---
    # songs: (title, artist_name) → new_song_id
    # ※ Supabase はデフォルト1000件制限のため、ページネーション付きで全件取得
    all_songs = fetch_all_rows(supabase, "songs", "id, title, artist_id")
    print(f"  新テーブルから {len(all_songs)}曲取得")

    # artist_id → name（新テーブル）
    all_artists = fetch_all_rows(supabase, "artists", "id, name")
    new_id_to_name: dict[int, str] = {
        a["id"]: a["name"] for a in all_artists
    }

    song_lookup: dict[tuple[str, str], int] = {}
    for s in all_songs:
        artist_name = new_id_to_name.get(s["artist_id"], "")
        key = (s["title"], artist_name)
        song_lookup[key] = s["id"]

    # --- favorite_songs 復元 ---
    if fav_songs_backup:
        restored = 0
        failed = 0
        for fav in fav_songs_backup:
            key = (fav["title"], fav["artist_name"])
            new_song_id = song_lookup.get(key)
            if new_song_id:
                try:
                    supabase.table("favorite_songs").upsert({
                        "user_id": fav["user_id"],
                        "song_id": new_song_id,
                    }, on_conflict="user_id,song_id").execute()
                    restored += 1
                except Exception as e:
                    print(f"  [WARN] favorite_song 復元失敗: {fav['title']} - {e}")
                    failed += 1
            else:
                print(f"  [WARN] 楽曲が見つからず: 「{fav['title']}」({fav['artist_name']})")
                failed += 1

        print(f"  favorite_songs: {restored}件復元, {failed}件失敗")

    # --- favorite_artists 復元 ---
    if fav_artists_backup:
        restored = 0
        failed = 0
        for fav in fav_artists_backup:
            new_artist_id = name_to_new_id.get(fav["artist_name"])
            if new_artist_id:
                try:
                    supabase.table("favorite_artists").upsert({
                        "user_id": fav["user_id"],
                        "artist_id": new_artist_id,
                        "artist_name": fav["artist_name"],
                    }, on_conflict="user_id,artist_id").execute()
                    restored += 1
                except Exception as e:
                    print(f"  [WARN] favorite_artist 復元失敗: {fav['artist_name']} - {e}")
                    failed += 1
            else:
                print(f"  [WARN] アーティストが見つからず: {fav['artist_name']}")
                failed += 1

        print(f"  favorite_artists: {restored}件復元, {failed}件失敗")


def validate(supabase: Client, expected_artists: int, expected_songs: int) -> bool:
    """アップロード結果のバリデーション。"""
    print("\n[STEP 7] バリデーション...")

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

    # 参照整合性チェック: songs の artist_id が全て artists に存在するか
    # ※ Supabase はデフォルト1000件制限のため、ページネーション付きで全件取得
    all_artist_rows = fetch_all_rows(supabase, "artists", "id")
    valid_artist_ids = {a["id"] for a in all_artist_rows}

    all_song_rows = fetch_all_rows(supabase, "songs", "id, artist_id")
    orphan_count = 0
    for song in all_song_rows:
        if song["artist_id"] not in valid_artist_ids:
            orphan_count += 1

    if orphan_count > 0:
        print(f"  [WARN] 孤立した artist_id 参照: {orphan_count}件")
        ok = False
    else:
        print("  [OK] 全 songs.artist_id が artists に存在")

    if ok:
        print("  [OK] 全バリデーション合格")

    return ok


def main() -> None:
    """メイン処理。"""
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("PitchScout CSV → Supabase データアップロード")
    if dry_run:
        print("  *** DRY RUN モード — アップロードは実行しません ***")
    print("=" * 60)

    # CSV 読み込み & ID 振り直し
    artists, songs, name_to_new_id = load_and_reassign_ids()

    if dry_run:
        print("\n[DRY RUN] CSV読み込み結果:")
        print(f"  artists: {len(artists)}件（ID: 1〜{len(artists)}）")
        print(f"  songs: {len(songs)}件（ID: 1〜{len(songs)}）")
        print(f"\n  先頭3アーティスト:")
        for a in artists[:3]:
            print(f"    ID={a['id']}: {a['name']} ({a['song_count']}曲)")
        print(f"\n  先頭3楽曲:")
        for s in songs[:3]:
            print(f"    ID={s['id']}: {s['title']} (artist_id={s['artist_id']})")
        print("\n[DRY RUN] 完了")
        return

    # Supabase 接続
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[ERROR] SUPABASE_URL と SUPABASE_KEY を .env に設定してください")
        print("  ※ RLS バイパスのため service_role key を使用してください")
        sys.exit(1)

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    if not check_connection(supabase):
        sys.exit(1)

    # 確認プロンプト
    print(f"\n[確認] 以下の操作を実行します:")
    print(f"  - 対象: {SUPABASE_URL}")
    print(f"  - artists: {len(artists)}件アップロード（IDを1から振り直し）")
    print(f"  - songs: {len(songs)}件アップロード（IDを1から振り直し）")
    print(f"  - 既存の artists/songs データは全削除されます")
    print(f"  - お気に入りデータは名前ベースで自動修復します")
    answer = input("\n続行しますか？ (y/N): ").strip().lower()
    if answer != "y":
        print("中断しました")
        sys.exit(0)

    # 実行
    fav_songs_backup, fav_artists_backup = backup_favorites(supabase)
    truncate_data(supabase)
    upload_artists(supabase, artists)
    upload_songs(supabase, songs)
    reset_sequences(supabase, len(artists), len(songs))
    restore_favorites(supabase, fav_songs_backup, fav_artists_backup, name_to_new_id)
    valid = validate(supabase, len(artists), len(songs))

    # 完了メッセージ
    print("\n" + "=" * 60)
    if valid:
        print("アップロード完了!")
    else:
        print("アップロード完了（警告あり — 上記を確認してください）")
    print("=" * 60)


if __name__ == "__main__":
    main()
