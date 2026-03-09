"""songs.db のクロスソース重複を除去するスクリプト

同一 (artist_id, title) で複数ソースが存在するレコードについて、
vocal-range.com（音域の沼）を優先し、voice-key.news（音域速報）を削除する。
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'songs.db')


def main() -> None:
    """クロスソース重複を検出・削除し、song_count を更新する。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 重複検出
    cur = conn.execute("""
        SELECT COUNT(*) as c FROM (
            SELECT artist_id, title FROM songs
            GROUP BY artist_id, title
            HAVING COUNT(DISTINCT source) > 1
        )
    """)
    dup_count = cur.fetchone()['c']
    print(f"クロスソース重複: {dup_count} 組")

    if dup_count == 0:
        print("重複なし。処理をスキップします。")
        conn.close()
        return

    # vocal-range.com が存在する重複ペアから voice-key.news を削除
    result = conn.execute("""
        DELETE FROM songs WHERE id IN (
            SELECT s_vk.id
            FROM songs s_vk
            JOIN songs s_vr
                ON s_vk.artist_id = s_vr.artist_id
                AND s_vk.title = s_vr.title
            WHERE s_vk.source = 'voice-key.news'
              AND s_vr.source = 'vocal-range.com'
        )
    """)
    deleted = result.rowcount
    print(f"削除: {deleted} 件（voice-key.news 側）")

    # vocal-range.com がなく voice-key.news のみの重複（理論上ないが安全策）
    cur = conn.execute("""
        SELECT COUNT(*) as c FROM (
            SELECT artist_id, title FROM songs
            GROUP BY artist_id, title
            HAVING COUNT(*) > 1
        )
    """)
    remaining = cur.fetchone()['c']
    if remaining > 0:
        print(f"[WARN] 同一ソース内の重複が {remaining} 組残っています")

    # song_count を実データから再計算
    conn.execute("""
        UPDATE artists SET song_count = (
            SELECT COUNT(*) FROM songs WHERE songs.artist_id = artists.id
        )
    """)
    conn.commit()

    # 結果サマリー
    artist_count = conn.execute("SELECT COUNT(*) FROM artists").fetchone()[0]
    song_count = conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0]
    print(f"\n=== 結果サマリー ===")
    print(f"アーティスト数: {artist_count}")
    print(f"楽曲数: {song_count}")

    # ソース分布
    for row in conn.execute("SELECT source, COUNT(*) as c FROM songs GROUP BY source"):
        print(f"  {row['source']}: {row['c']} 曲")

    conn.close()
    print("\n完了!")


if __name__ == '__main__':
    main()
