"""
J-POP 音域の沼 (vocal-range.com) から楽曲の音域データをスクレイピングしてSQLiteに保存する。
独立スクリプトとして実行: python scraper_vocal_range.py

クロール戦略: WordPress サイトマップ (post-sitemap*.xml) から全投稿URLを列挙し、
各ページのタイトルと本文から音域データを正規表現で抽出する。

配慮事項:
- リクエスト間隔を1.5秒空けてサーバー負荷を抑える
- robots.txt で許可されていることを確認済み
- 出典: vocal-range.com
"""
import re
import time
import xml.etree.ElementTree as ET
import httpx
from db.songs import init_db, get_connection

SITEMAP_URLS = [
    "https://vocal-range.com/post-sitemap.xml",
    "https://vocal-range.com/post-sitemap2.xml",
    "https://vocal-range.com/post-sitemap3.xml",
]
REQUEST_INTERVAL = 1.5
SOURCE = "vocal-range.com"

# カラオケ表記の音名パターン（lowG ~ hihiE まで対応）
NOTE_PATTERN = r"(?:lowlow|low|mid1|mid2|hi[A-G]|hihi)?[A-G]#?"
# より厳密なパターン: プレフィックス必須
STRICT_NOTE = r"(?:lowlow[A-G]#?|low[A-G]#?|mid1[A-G]#?|mid2[A-G]#?|hi[A-G]#?|hihi[A-G]#?)"

# タイトルから曲名・アーティスト名を抽出する正規表現
TITLE_RE = re.compile(r"[『「](.+?)[』」][\(（](.+?)[\)）].*?音域")


def fetch_sitemap_urls(client: httpx.Client) -> list[str]:
    """3つの post-sitemap.xml から全投稿URLを収集"""
    urls = []
    for sitemap_url in SITEMAP_URLS:
        try:
            resp = client.get(sitemap_url, timeout=15.0)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            # XML namespace を処理
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            for url_elem in root.findall("sm:url/sm:loc", ns):
                urls.append(url_elem.text)
            print(f"  {sitemap_url}: {len(root.findall('sm:url', ns))}件")
        except Exception as e:
            print(f"  {sitemap_url}: 取得失敗 ({e})")
        time.sleep(REQUEST_INTERVAL)
    return urls


def parse_song_page(html: str) -> dict | None:
    """ページHTMLから曲名・アーティスト名・音域データを抽出。抽出できない場合はNone"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # タイトルから曲名・アーティスト名を抽出
    title_tag = soup.find("h1", class_="entry-title") or soup.find("h1")
    if not title_tag:
        return None
    title_text = title_tag.get_text(strip=True)

    match = TITLE_RE.search(title_text)
    if not match:
        return None

    song_title = match.group(1).strip()
    artist_name = match.group(2).strip()

    # 本文テキストから音域データを抽出
    content = soup.find("div", class_="entry-content")
    if not content:
        content = soup.find("article") or soup
    text = content.get_text()

    lowest = _extract_note(text, r"【地声最低音】")
    highest = _extract_note(text, r"【地声最高音】")
    falsetto = _extract_note(text, r"【裏声最高音】")

    # 最低音か最高音のどちらかが取れなければデータ不十分
    if not lowest and not highest:
        return None

    return {
        "song_title": song_title,
        "artist_name": artist_name,
        "lowest_note": lowest,
        "highest_note": highest,
        "falsetto_note": falsetto,
    }


def _extract_note(text: str, label_pattern: str) -> str | None:
    """テキスト中のラベル直後にある音名を抽出"""
    # ラベルの後に続く文字列から音名を探す
    pattern = label_pattern + r"[^\n]{0,50}?(" + STRICT_NOTE + r")"
    match = re.search(pattern, text)
    return match.group(1) if match else None


def save_song(conn, song_data: dict) -> bool:
    """1曲をDBに保存。アーティストが存在しなければ作成。"""
    artist_name = song_data["artist_name"]
    # slug は名前をそのまま使用（vocal-range.com にはスラッグ概念がないため）
    slug = artist_name

    conn.execute(
        "INSERT OR IGNORE INTO artists (name, slug, song_count) VALUES (?, ?, 0)",
        (artist_name, slug),
    )
    row = conn.execute(
        "SELECT id FROM artists WHERE name = ?", (artist_name,)
    ).fetchone()
    if not row:
        return False
    artist_id = row["id"]

    cursor = conn.execute(
        """INSERT OR IGNORE INTO songs
           (title, artist_id, lowest_note, highest_note, falsetto_note, note, source)
           VALUES (?, ?, ?, ?, ?, NULL, ?)""",
        (song_data["song_title"], artist_id,
         song_data["lowest_note"], song_data["highest_note"],
         song_data["falsetto_note"], SOURCE),
    )
    return cursor.rowcount > 0


def main():
    init_db()
    conn = get_connection()

    with httpx.Client(
        headers={"User-Agent": "VoiceMatch-Scraper/1.0 (educational project)"},
        follow_redirects=True,
    ) as client:
        print("サイトマップから投稿URLを収集中...")
        all_urls = fetch_sitemap_urls(client)
        print(f"  合計 {len(all_urls)} ページ検出\n")

        saved_count = 0
        skipped = 0
        failed = 0

        for i, url in enumerate(all_urls, 1):
            print(f"[{i}/{len(all_urls)}] {url}...", end=" ", flush=True)

            try:
                resp = client.get(url, timeout=15.0)
                resp.raise_for_status()
                result = parse_song_page(resp.text)

                if result is None:
                    print("⏭ 音域データなし")
                    skipped += 1
                elif save_song(conn, result):
                    saved_count += 1
                    print(f"✓ {result['artist_name']} - {result['song_title']}")
                else:
                    print("⏭ 重複")
                    skipped += 1
            except httpx.HTTPStatusError as e:
                print(f"✗ HTTP {e.response.status_code}")
                failed += 1
            except Exception as e:
                print(f"✗ {e}")
                failed += 1

            if i % 100 == 0:
                conn.commit()

            time.sleep(REQUEST_INTERVAL)

    conn.commit()
    conn.close()
    print(f"\n完了: {saved_count}曲保存 / {skipped}スキップ / {failed}失敗")
    print(f"出典: {SOURCE}")


if __name__ == "__main__":
    main()
