"""修正済み CSV を songs.db に反映するスクリプト

使い方:
  python scripts/apply_csv_fixes.py              # dry-run（変更プレビューのみ）
  python scripts/apply_csv_fixes.py --apply      # 変更を適用

CSV ファイル:
  backend/scripts/output/songs_check.csv   — 楽曲データ
  backend/scripts/output/artists_check.csv — アーティストデータ
"""
import argparse
import csv
import os
import re
import shutil
import sqlite3
from typing import Any

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'songs.db')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')
SONGS_CSV = os.path.join(OUTPUT_DIR, 'songs_check.csv')
ARTISTS_CSV = os.path.join(OUTPUT_DIR, 'artists_check.csv')

# 音程表記の正規表現（lowlowA ~ hihihiG#）
NOTE_PATTERN = re.compile(r'^(lowlow|low|mid1|mid2|hi|hihi|hihihi)[A-G]#?$')

# songs で修正可能なカラム（id, artist_name, source は変更不可）
SONGS_EDITABLE = ['title', 'lowest_note', 'highest_note', 'falsetto_note', 'note']

# artists で修正可能なカラム（id, slug, song_count は変更不可）
ARTISTS_EDITABLE = ['name', 'reading']


def load_csv(path: str) -> list[dict[str, str]]:
    """CSV を読み込んで辞書のリストとして返す（BOM 対応）"""
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        return list(reader)


def validate_note(value: str, col_name: str, row_id: int) -> str | None:
    """音程カラムの値をバリデーション。エラーメッセージまたは None を返す。"""
    if not value:
        return None
    if not NOTE_PATTERN.match(value):
        return f"[songs id={row_id}] {col_name}='{value}' は不正な音程表記です"
    return None


def diff_songs(conn: sqlite3.Connection, csv_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """songs の変更差分を検出する。"""
    changes: list[dict[str, Any]] = []

    for csv_row in csv_rows:
        song_id = int(csv_row['id'])
        db_row = conn.execute(
            "SELECT id, title, lowest_note, highest_note, falsetto_note, note "
            "FROM songs WHERE id = ?",
            (song_id,)
        ).fetchone()

        if db_row is None:
            print(f"[WARN] songs id={song_id} が DB に存在しません（スキップ）")
            continue

        updates: dict[str, tuple[str, str]] = {}
        for col in SONGS_EDITABLE:
            csv_val = csv_row.get(col, '') or ''
            db_val = db_row[col] or ''
            if csv_val != db_val:
                updates[col] = (db_val, csv_val)

        if updates:
            changes.append({'id': song_id, 'table': 'songs', 'updates': updates})

    return changes


def diff_artists(conn: sqlite3.Connection, csv_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """artists の変更差分を検出する。"""
    changes: list[dict[str, Any]] = []

    for csv_row in csv_rows:
        artist_id = int(csv_row['id'])
        db_row = conn.execute(
            "SELECT id, name, reading FROM artists WHERE id = ?",
            (artist_id,)
        ).fetchone()

        if db_row is None:
            print(f"[WARN] artists id={artist_id} が DB に存在しません（スキップ）")
            continue

        updates: dict[str, tuple[str, str]] = {}
        for col in ARTISTS_EDITABLE:
            csv_val = csv_row.get(col, '') or ''
            db_val = db_row[col] or ''
            if csv_val != db_val:
                updates[col] = (db_val, csv_val)

        if updates:
            changes.append({'id': artist_id, 'table': 'artists', 'updates': updates})

    return changes


def validate_changes(changes: list[dict[str, Any]]) -> list[str]:
    """変更内容をバリデーションし、エラーのリストを返す。"""
    errors: list[str] = []
    note_cols = {'lowest_note', 'highest_note', 'falsetto_note'}

    for change in changes:
        if change['table'] == 'songs':
            for col, (_, new_val) in change['updates'].items():
                if col in note_cols:
                    err = validate_note(new_val, col, change['id'])
                    if err:
                        errors.append(err)

    return errors


def print_changes(changes: list[dict[str, Any]]) -> None:
    """変更差分を表示する。"""
    songs_changes = [c for c in changes if c['table'] == 'songs']
    artists_changes = [c for c in changes if c['table'] == 'artists']

    if artists_changes:
        print(f"\n=== artists の変更: {len(artists_changes)} 件 ===")
        for change in artists_changes:
            print(f"  id={change['id']}:")
            for col, (old, new) in change['updates'].items():
                print(f"    {col}: '{old}' → '{new}'")

    if songs_changes:
        print(f"\n=== songs の変更: {len(songs_changes)} 件 ===")
        for change in songs_changes:
            print(f"  id={change['id']}:")
            for col, (old, new) in change['updates'].items():
                print(f"    {col}: '{old}' → '{new}'")

    if not changes:
        print("\n変更なし。CSV と DB の内容は一致しています。")


def apply_changes(conn: sqlite3.Connection, changes: list[dict[str, Any]]) -> None:
    """変更を songs.db に適用する。"""
    for change in changes:
        table = change['table']
        row_id = change['id']
        updates = change['updates']

        set_clause = ', '.join(f"{col} = ?" for col in updates)
        values = [new for _, new in updates.values()]
        values.append(row_id)

        conn.execute(f"UPDATE {table} SET {set_clause} WHERE id = ?", values)

    # song_count を再計算
    conn.execute("""
        UPDATE artists SET song_count = (
            SELECT COUNT(*) FROM songs WHERE songs.artist_id = artists.id
        )
    """)
    conn.commit()


def main() -> None:
    """CSV の変更を songs.db に反映する。"""
    parser = argparse.ArgumentParser(description='修正済み CSV を songs.db に反映')
    parser.add_argument('--apply', action='store_true', help='変更を適用する（省略時は dry-run）')
    args = parser.parse_args()

    # CSV 存在チェック
    for path, name in [(SONGS_CSV, 'songs_check.csv'), (ARTISTS_CSV, 'artists_check.csv')]:
        if not os.path.exists(path):
            print(f"[ERROR] {name} が見つかりません: {path}")
            return

    # CSV 読み込み
    songs_csv = load_csv(SONGS_CSV)
    artists_csv = load_csv(ARTISTS_CSV)
    print(f"CSV 読み込み: songs={len(songs_csv)} 件, artists={len(artists_csv)} 件")

    # DB 接続
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 差分検出
    changes: list[dict[str, Any]] = []
    changes.extend(diff_artists(conn, artists_csv))
    changes.extend(diff_songs(conn, songs_csv))

    # 表示
    print_changes(changes)

    if not changes:
        conn.close()
        return

    # バリデーション
    errors = validate_changes(changes)
    if errors:
        print(f"\n[ERROR] バリデーションエラー: {len(errors)} 件")
        for err in errors:
            print(f"  {err}")
        conn.close()
        return

    # 適用
    if args.apply:
        # バックアップ作成
        backup_path = DB_PATH + '.bak'
        shutil.copy2(DB_PATH, backup_path)
        print(f"\nバックアップ作成: {backup_path}")

        apply_changes(conn, changes)
        total = len(changes)
        print(f"\n{total} 件の変更を適用しました。")
        print("品質チェックを実行してください: python scripts/db_quality_check.py")
    else:
        print(f"\n[dry-run] 適用するには --apply を付けて実行してください。")

    conn.close()


if __name__ == '__main__':
    main()
