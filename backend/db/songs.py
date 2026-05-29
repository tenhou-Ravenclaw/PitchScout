"""
db/songs.py — SQLite楽曲カタログの接続管理とクエリ関数

songs / artists テーブルへの CRUD 操作を提供する。
実行時は読み取り専用（スクレイパー以外から書き込まない）。
"""
import sqlite3
import os
import unicodedata
import re
from functools import lru_cache

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "songs.db")

def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """
    SQLite 接続を取得する。

    Row ファクトリと外部キー制約を有効化した接続を返す。
    呼び出し元で必ず close() すること。

    Args:
        db_path: データベースファイルのパス。

    Returns:
        sqlite3.Connection インスタンス。
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def _escape_like(query: str) -> str:
    """
    LIKE 句の特殊文字（%, _）をエスケープするヘルパー。

    Args:
        query: エスケープする検索文字列。

    Returns:
        エスケープ済みの文字列。
    """
    return query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')

def _hiragana_normalize(text: str) -> str:
    """カタカナをひらがなに変換して正規化

    Unicodeコードポイント範囲（U+30A1〜U+30F6）を使用して、
    濁点・半濁点・小書き文字・ヴなどを含む一般的なカタカナに対応。

    変換範囲: ァ〜ヶ（U+30A1〜U+30F6）
    対象外: ヷヸヹヺ（U+30F7〜U+30FA）等の稀な文字

    例: "ミセス" -> "みせす", "ガッツ" -> "がっつ", "パーティー" -> "ぱーてぃー"
    """
    # NFKC正規化で合成文字を統一（濁点・半濁点の結合文字対応）
    text = unicodedata.normalize('NFKC', text)

    # カタカナ（U+30A1〜U+30F6）をひらがな（U+3041〜U+3096）に変換
    result = []
    for char in text:
        code = ord(char)
        if 0x30A1 <= code <= 0x30F6:  # カタカナ範囲
            result.append(chr(code - 0x60))  # ひらがなに変換
        else:
            result.append(char)

    return ''.join(result)


def _query_mode(query: str) -> str:
    """
    検索クエリのモードを判定する。

    ひらがな/カタカナのみなら "kana"（reading 前方一致）、それ以外は "name"（name 部分一致）。

    Args:
        query: ユーザーの検索文字列。

    Returns:
        "kana" または "name"。
    """
    if not query:
        return "name"
    nfkc = unicodedata.normalize('NFKC', query)
    return "kana" if re.fullmatch(r"[ぁ-ゖァ-ヺーﾞﾟ]+", nfkc) else "name"

def init_db(db_path: str = DB_PATH) -> None:
    """
    データベースの初期化とマイグレーションを実行する。

    テーブル作成・カラム追加・データクレンジング・重複除去を行う。
    アプリ起動時に 1 回呼び出される（main.py の lifespan から）。

    Args:
        db_path: データベースファイルのパス。
    """
    conn = get_connection(db_path)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS artists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                slug TEXT NOT NULL UNIQUE,
                song_count INTEGER DEFAULT 0,
                reading TEXT
            );

            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                artist_id INTEGER NOT NULL,
                lowest_note TEXT,
                highest_note TEXT,
                falsetto_note TEXT,
                note TEXT,
                source TEXT DEFAULT 'voice-key.news',
                FOREIGN KEY (artist_id) REFERENCES artists(id)
            );

            CREATE INDEX IF NOT EXISTS idx_songs_title ON songs(title);
            CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(artist_id);
            CREATE INDEX IF NOT EXISTS idx_artists_reading ON artists(reading);
        """)

        # マイグレーション: 既存DBに reading カラムを追加
        try:
            conn.execute("ALTER TABLE artists ADD COLUMN reading TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # カラムが既に存在する場合は無視

        # マイグレーション: 既存DBに source カラムを追加
        try:
            conn.execute("ALTER TABLE songs ADD COLUMN source TEXT DEFAULT 'voice-key.news'")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # カラムが既に存在する場合は無視

        # マイグレーション: 既存DBに idx_artists_reading インデックスを追加
        # reading 前方一致検索（かな検索）を高速化するため
        conn.execute("CREATE INDEX IF NOT EXISTS idx_artists_reading ON artists(reading)")
        conn.commit()

        # 既存の重複データを除去（IDが最小のレコードを残す）
        conn.execute("""
            DELETE FROM songs WHERE id NOT IN (
                SELECT MIN(id) FROM songs GROUP BY artist_id, title, source
            )
        """)
        conn.commit()

        # 同一アーティスト・同一タイトル・同一ソースの重複防止
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_songs_unique
            ON songs(artist_id, title, source)
        """)
        conn.commit()

        # マイグレーション: 不正な音名データを修正
        conn.executescript("""
            -- タイプミス修正: mmid2A → mid2A
            UPDATE songs SET lowest_note = 'mid2A' WHERE lowest_note = 'mmid2A';

            -- 判別不可 → NULL
            UPDATE songs SET lowest_note = NULL WHERE lowest_note = '判別不可';
            UPDATE songs SET highest_note = NULL WHERE highest_note = '判別不可';

            -- 疑問符付き → 疑問符を除去（推定値として扱う）
            UPDATE songs SET highest_note = REPLACE(highest_note, '?', '') WHERE highest_note LIKE '%?';
            UPDATE songs SET falsetto_note = REPLACE(falsetto_note, '?', '') WHERE falsetto_note LIKE '%?';

            -- テキスト値 → NULL
            UPDATE songs SET falsetto_note = NULL WHERE falsetto_note = '裏声あり';
        """)
        conn.commit()

        # マイグレーション: クロスソース重複の削除（voice-key.news を優先）
        # 同一アーティスト・同一タイトルが両ソースに存在する場合、vocal-range.com 側を削除
        conn.execute("""
            DELETE FROM songs WHERE id IN (
                SELECT s2.id
                FROM songs s1
                JOIN songs s2 ON s1.artist_id = s2.artist_id AND s1.title = s2.title
                WHERE s1.source = 'voice-key.news' AND s2.source = 'vocal-range.com'
            )
        """)
        conn.commit()

        # マイグレーション: song_count を実データから再計算
        conn.execute("""
            UPDATE artists SET song_count = (
                SELECT COUNT(*) FROM songs WHERE songs.artist_id = artists.id
            )
        """)
        conn.commit()

        # データクレンジング・整合性維持
        conn.execute("""
            DELETE FROM songs WHERE id NOT IN (
                SELECT MIN(id) FROM songs GROUP BY artist_id, title, source
            )
        """)
        conn.execute("UPDATE songs SET note = 'mid2A' WHERE note = 'mmid2A'")
        conn.execute("""
            UPDATE artists SET song_count = (
                SELECT COUNT(*) FROM songs WHERE songs.artist_id = artists.id
            )
        """)

        conn.commit()
    finally:
        conn.close()


def search_songs(query: str, limit: int = 20, offset: int = 0) -> list[dict]:
    """
    曲名またはアーティスト名、ふりがなであいまい検索する（カタカナ対応）。

    Args:
        query: 検索文字列。
        limit: 取得する最大件数。
        offset: ページネーション用オフセット。

    Returns:
        楽曲情報の辞書リスト。
    """
    conn = get_connection()
    try:
        # title/name には NFKC 正規化のみ、reading にはひらがな正規化を使用
        nfkc_query = unicodedata.normalize('NFKC', query)
        normalized_query = _hiragana_normalize(query)

        escaped_nfkc = f"%{_escape_like(nfkc_query)}%"
        escaped_normalized = f"%{_escape_like(normalized_query)}%"

        rows = conn.execute("""
            SELECT s.id, s.title, a.name as artist,
                   s.artist_id, a.slug as artist_slug,
                   a.reading as artist_reading,
                   s.lowest_note, s.highest_note, s.falsetto_note, s.note,
                   s.source
            FROM songs s
            JOIN artists a ON s.artist_id = a.id
            WHERE s.title LIKE ? ESCAPE '\\'
               OR a.name LIKE ? ESCAPE '\\'
               OR a.reading LIKE ? ESCAPE '\\'
            ORDER BY a.reading, s.title COLLATE NOCASE
            LIMIT ? OFFSET ?
        """, (escaped_nfkc, escaped_nfkc, escaped_normalized, limit, offset)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def count_songs(query: str = "") -> int:
    """
    楽曲総数を取得する（カタカナ対応）。

    Args:
        query: 検索文字列。空文字なら全件カウント。

    Returns:
        該当する楽曲の件数。
    """
    conn = get_connection()
    try:
        if query:
            # title/name には NFKC 正規化のみ、reading にはひらがな正規化を使用
            nfkc_query = unicodedata.normalize('NFKC', query)
            normalized_query = _hiragana_normalize(query)

            escaped_nfkc = f"%{_escape_like(nfkc_query)}%"
            escaped_normalized = f"%{_escape_like(normalized_query)}%"

            row = conn.execute("""
                SELECT COUNT(*) FROM songs s
                JOIN artists a ON s.artist_id = a.id
                WHERE s.title LIKE ? ESCAPE '\\'
                   OR a.name LIKE ? ESCAPE '\\'
                   OR a.reading LIKE ? ESCAPE '\\'
            """, (escaped_nfkc, escaped_nfkc, escaped_normalized)).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) FROM songs").fetchone()
        return row[0]
    finally:
        conn.close()


def get_song(song_id: int) -> dict | None:
    """
    ID で楽曲を取得する。

    Args:
        song_id: 楽曲 ID。

    Returns:
        楽曲情報の辞書。存在しなければ None。
    """
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT s.id, s.artist_id, s.title, a.name as artist,
                   s.lowest_note, s.highest_note, s.falsetto_note, s.note,
                   s.source
            FROM songs s
            JOIN artists a ON s.artist_id = a.id
            WHERE s.id = ?
        """, (song_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_songs_by_ids(song_ids: list[int]) -> dict[int, dict]:
    """
    ID リストで楽曲を一括取得する。

    Args:
        song_ids: 取得する楽曲 ID のリスト。

    Returns:
        {song_id: song_dict} の辞書。存在しない ID はキーに含まれない。
    """
    if not song_ids:
        return {}
    conn = get_connection()
    try:
        placeholders = ",".join("?" * len(song_ids))
        rows = conn.execute(f"""
            SELECT s.id, s.artist_id, s.title, a.name as artist,
                   s.lowest_note, s.highest_note, s.falsetto_note, s.note,
                   s.source
            FROM songs s
            JOIN artists a ON s.artist_id = a.id
            WHERE s.id IN ({placeholders})
        """, song_ids).fetchall()
        return {row["id"]: dict(row) for row in rows}
    finally:
        conn.close()


def get_artist(artist_id: int) -> dict | None:
    """
    ID でアーティストを取得する。

    Args:
        artist_id: アーティスト ID。

    Returns:
        アーティスト情報の辞書。存在しなければ None。
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, name, slug, song_count, reading FROM artists WHERE id = ?",
            (artist_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_artists(limit: int = 100, offset: int = 0) -> list[dict]:
    """
    アーティスト一覧を取得する（reading 順）。

    Args:
        limit: 取得する最大件数。
        offset: ページネーション用オフセット。

    Returns:
        アーティスト情報の辞書リスト。
    """
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT id, name, slug, song_count, reading
            FROM artists
            WHERE song_count > 0
            ORDER BY reading
            LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@lru_cache(maxsize=256)
def count_artists(query: str = "") -> int:
    """
    アーティスト総数を取得する（カタカナ対応）。

    songs.db は実行時読み取り専用のため lru_cache でキャッシュしている。
    同一クエリでのページ遷移ごとに DB をスキャンするコストを排除する。

    Args:
        query: 検索文字列。空文字なら全件カウント。

    Returns:
        該当するアーティストの件数。
    """
    conn = get_connection()
    try:
        if query:
            mode = _query_mode(query)
            nfkc_query = unicodedata.normalize('NFKC', query)
            escaped_nfkc = f"%{_escape_like(nfkc_query)}%"
            if mode == "kana":
                normalized_query = _hiragana_normalize(query)
                escaped_normalized = f"{_escape_like(normalized_query)}%"  # 前方一致
                row = conn.execute(
                    "SELECT COUNT(*) FROM artists WHERE song_count > 0 AND reading LIKE ? ESCAPE '\\'",
                    (escaped_normalized,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) FROM artists WHERE song_count > 0 AND name LIKE ? ESCAPE '\\'",
                    (escaped_nfkc,),
                ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) FROM artists WHERE song_count > 0"
            ).fetchone()
        return row[0]
    finally:
        conn.close()


def search_artists(query: str, limit: int = 100, offset: int = 0) -> list[dict]:
    """
    アーティストを検索する。

    かな入力なら reading 前方一致、その他は name 部分一致で検索する。

    Args:
        query: 検索文字列。
        limit: 取得する最大件数。
        offset: ページネーション用オフセット。

    Returns:
        アーティスト情報の辞書リスト。
    """
    conn = get_connection()
    try:
        mode = _query_mode(query)
        nfkc_query = unicodedata.normalize('NFKC', query)
        escaped_nfkc = f"%{_escape_like(nfkc_query)}%"

        if mode == "kana":
            normalized_query = _hiragana_normalize(query)
            escaped_normalized = f"{_escape_like(normalized_query)}%"  # 前方一致
            params = (escaped_normalized, limit, offset)
            rows = conn.execute("""
                SELECT id, name, slug, song_count, reading
                FROM artists
                WHERE song_count > 0 AND reading LIKE ? ESCAPE '\\'
                ORDER BY reading
                LIMIT ? OFFSET ?
            """, params).fetchall()
        else:
            params = (escaped_nfkc, limit, offset)
            rows = conn.execute("""
                SELECT id, name, slug, song_count, reading
                FROM artists
                WHERE song_count > 0 AND name LIKE ? ESCAPE '\\'
                ORDER BY reading
                LIMIT ? OFFSET ?
            """, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def _consonant_row(text: str) -> int:
    """
    先頭文字から五十音の行番号（0〜9）を返す。

    Args:
        text: ひらがな読み仮名文字列。

    Returns:
        0=あ行, 1=か行, 2=さ行, 3=た行, 4=な行, 5=は行, 6=ま行, 7=や行, 8=ら行, 9=わ行, 99=該当なし。
    """
    if not text:
        return 99

    code = ord(text[0])
    # カタカナをひらがなに変換して判定
    if 0x30A1 <= code <= 0x30F6:
        code -= 0x60

    if 0x3041 <= code <= 0x3093:
        if code <= 0x304A:
            return 0  # あ行
        if code <= 0x3054:
            return 1  # か行
        if code <= 0x305E:
            return 2  # さ行
        if code <= 0x3069:
            return 3  # た行
        if code <= 0x306E:
            return 4  # な行
        if code <= 0x307D:
            return 5  # は行
        if code <= 0x3082:
            return 6  # ま行
        if code <= 0x3088:
            return 7  # や行
        if code <= 0x308D:
            return 8  # ら行
        return 9  # わ行

    return 99


def get_artist_index_page(char: str, limit: int = 10) -> int | None:
    """
    五十音インデックス文字に対応する最初のページ番号を返す。

    全アーティストを reading 順に並べ、指定された行（あ行〜わ行）が
    最初に出現するページ番号（0-indexed）を返す。

    Args:
        char: 五十音インデックス文字（例: "あ", "か"）。
        limit: 1ページあたりの件数。

    Returns:
        該当するページ番号（0-indexed）。見つからない場合は None。
    """
    if not char or limit <= 0:
        return None

    normalized = _hiragana_normalize(unicodedata.normalize("NFKC", char))
    target_row = _consonant_row(normalized)
    if target_row == 99:
        return None

    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT reading
            FROM artists
            WHERE song_count > 0
            ORDER BY reading
            """
        ).fetchall()

        for index, row in enumerate(rows):
            if _consonant_row(row["reading"] or "") == target_row:
                return index // limit

        return 0
    finally:
        conn.close()


def get_artist_songs(artist_id: int) -> list[dict]:
    """
    特定のアーティストの楽曲一覧を取得する。

    Args:
        artist_id: アーティスト ID。

    Returns:
        楽曲情報の辞書リスト（曲名順）。
    """
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT s.id, s.artist_id, s.title, a.name as artist,
                   s.lowest_note, s.highest_note, s.falsetto_note, s.note,
                   s.source
            FROM songs s
            JOIN artists a ON s.artist_id = a.id
            WHERE s.artist_id = ?
            ORDER BY s.title
        """, (artist_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_songs_raw(query: str = "") -> list[dict]:
    """
    音域フィルタ用に楽曲を全件取得する（ページネーションなし）。

    通常の get_all_songs / search_songs はページネーション前提のため、
    フィルタ後にページネーションしたい場合にこちらを使用する。
    全件取得後にルーター側で Python フィルタを適用し、
    その後 offset/limit でスライスすること。

    Args:
        query: 楽曲名・アーティスト名での絞り込み文字列。空文字なら全件返す。

    Returns:
        楽曲情報の辞書リスト（アーティスト50音順 → 曲名順）。
    """
    conn = get_connection()
    try:
        if query:
            nfkc_query = unicodedata.normalize('NFKC', query)
            normalized_query = _hiragana_normalize(query)
            escaped_nfkc = f"%{_escape_like(nfkc_query)}%"
            escaped_normalized = f"%{_escape_like(normalized_query)}%"
            rows = conn.execute("""
                SELECT s.id, s.title, a.name as artist,
                       s.artist_id, a.slug as artist_slug,
                       a.reading as artist_reading,
                       s.lowest_note, s.highest_note, s.falsetto_note, s.note,
                       s.source
                FROM songs s
                JOIN artists a ON s.artist_id = a.id
                WHERE s.title LIKE ? ESCAPE '\\'
                   OR a.name LIKE ? ESCAPE '\\'
                   OR a.reading LIKE ? ESCAPE '\\'
                ORDER BY a.reading, s.title COLLATE NOCASE
            """, (escaped_nfkc, escaped_nfkc, escaped_normalized)).fetchall()
        else:
            rows = conn.execute("""
                SELECT s.id, s.title, a.name as artist,
                       s.artist_id, a.slug as artist_slug,
                       a.reading as artist_reading,
                       s.lowest_note, s.highest_note, s.falsetto_note, s.note,
                       s.source
                FROM songs s
                JOIN artists a ON s.artist_id = a.id
                ORDER BY a.reading, s.title COLLATE NOCASE
            """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_songs(limit: int = 20, offset: int = 0) -> list[dict]:
    """
    全曲を取得する（アーティスト名50音順 → 曲名順）。

    Args:
        limit: 取得する最大件数。
        offset: ページネーション用オフセット。

    Returns:
        楽曲情報の辞書リスト。
    """
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT s.id, s.title, a.name as artist,
                   s.artist_id, a.slug as artist_slug,
                   a.reading as artist_reading,
                   s.lowest_note, s.highest_note, s.falsetto_note, s.note,
                   s.source
            FROM songs s
            JOIN artists a ON s.artist_id = a.id
            ORDER BY a.reading, s.title COLLATE NOCASE
            LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
