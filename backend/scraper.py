"""
音域速報 (voice-key.news) から楽曲の音域データをスクレイピングしてSQLiteに保存する。
独立スクリプトとして実行: python scraper.py

配慮事項:
- リクエスト間隔を1〜2秒空けてサーバー負荷を抑える
- 出典: voice-key.news
"""
import re
import time
import sqlite3
import httpx
from bs4 import BeautifulSoup
from db.songs import init_db, get_connection, DB_PATH

ARTIST_LIST_URL = "https://voice-key.news/artist-key/"
REQUEST_INTERVAL = 1.5  # 秒


def fetch_artist_links(client: httpx.Client) -> list[dict]:
    """アーティスト一覧ページからアーティスト名とURLを取得"""
    resp = client.get(ARTIST_LIST_URL, timeout=15.0)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    artists = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        text = a_tag.get_text(strip=True)
        # アーティストページは /{slug}-key/ 形式
        if re.match(r"https://voice-key\.news/[a-z0-9\-]+-key/$", href) and text:
            # artist-key はアーティスト一覧ページ自身なのでスキップ
            if "/artist-key/" in href:
                continue
            # テキストから曲数を分離: "米津玄師 (76曲)" -> ("米津玄師", "76")
            match = re.match(r"^(.+?)\s*[\(（](\d+)曲[\)）]$", text)
            if match:
                name = match.group(1).strip()
                song_count = int(match.group(2))
            else:
                name = text
                song_count = 0
            m = re.search(r"/([a-z0-9\-]+)-key/$", href)
            if not m:
                continue
            slug = m.group(1)
            artists.append({
                "name": name,
                "slug": slug,
                "url": href,
                "song_count": song_count,
            })
    return artists


def fetch_artist_songs(client: httpx.Client, url: str) -> list[dict]:
    """アーティストページから楽曲テーブルをパース"""
    resp = client.get(url, timeout=15.0)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    table = soup.find("table", class_="tablepress")
    if not table:
        return []

    songs = []
    tbody = table.find("tbody")
    if not tbody:
        return []

    for tr in tbody.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 4:
            continue
        title = cells[0].get_text(strip=True)
        lowest = cells[1].get_text(strip=True)
        highest = cells[2].get_text(strip=True)
        falsetto = cells[3].get_text(strip=True)
        note = cells[4].get_text(strip=True) if len(cells) > 4 else ""

        if not title:
            continue

        songs.append({
            "title": title,
            "lowest_note": lowest or None,
            "highest_note": highest or None,
            "falsetto_note": falsetto or None,
            "note": note or None,
        })
    return songs


def save_to_db(conn: sqlite3.Connection, artist: dict, songs: list[dict]) -> int:
    """アーティストと楽曲データをDBに保存。新規挿入された曲数を返す"""
    conn.execute(
        "INSERT OR IGNORE INTO artists (name, slug, song_count) VALUES (?, ?, ?)",
        (artist["name"], artist["slug"], artist["song_count"]),
    )
    row = conn.execute(
        "SELECT id FROM artists WHERE slug = ?", (artist["slug"],)
    ).fetchone()
    if not row:
        return 0
    artist_id = row["id"]

    inserted = 0
    for song in songs:
        cursor = conn.execute(
            """INSERT OR IGNORE INTO songs
               (title, artist_id, lowest_note, highest_note, falsetto_note, note, source)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (song["title"], artist_id, song["lowest_note"],
             song["highest_note"], song["falsetto_note"], song["note"],
             "voice-key.news"),
        )
        inserted += cursor.rowcount
    conn.commit()
    return inserted


def main():
    init_db()
    conn = get_connection()

    with httpx.Client(
        headers={"User-Agent": "VoiceMatch-Scraper/1.0 (educational project)"},
        follow_redirects=True,
    ) as client:
        print("アーティスト一覧を取得中...")
        artists = fetch_artist_links(client)
        print(f"  {len(artists)} 組のアーティストを検出")

        total_songs = 0
        for i, artist in enumerate(artists, 1):
            print(f"[{i}/{len(artists)}] {artist['name']} ({artist['song_count']}曲)...", end=" ", flush=True)

            try:
                songs = fetch_artist_songs(client, artist["url"])
                inserted = save_to_db(conn, artist, songs)
                if inserted > 0:
                    total_songs += inserted
                    print(f"✓ {inserted}曲保存")
                else:
                    print("⏭ スキップ（既存）")
            except httpx.HTTPStatusError as e:
                print(f"✗ HTTP {e.response.status_code}")
            except Exception as e:
                print(f"✗ {e}")

            time.sleep(REQUEST_INTERVAL)

    conn.close()
    print(f"\n完了: {total_songs}曲を {DB_PATH} に保存しました")
    print(f"出典: voice-key.news")


if __name__ == "__main__":
    main()
