"""
マージ済みデータをCSV出力する（目視確認用）

出力:
  - output/merged_artists.csv
  - output/merged_songs.csv
"""
import json
import csv
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")


def main() -> None:
    """マージ済みJSON → CSV変換"""
    # アーティストデータ読み込み
    with open(os.path.join(OUTPUT_DIR, "merged_artists.json"), encoding="utf-8") as f:
        artists: list[dict] = json.load(f)

    # アーティストID→名前のマッピング
    artist_name_map: dict[int, str] = {a["id"]: a["name"] for a in artists}

    # 楽曲データ読み込み
    with open(os.path.join(OUTPUT_DIR, "merged_songs.json"), encoding="utf-8") as f:
        songs: list[dict] = json.load(f)

    # アーティストCSV出力
    artists_csv_path = os.path.join(OUTPUT_DIR, "merged_artists.csv")
    with open(artists_csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "名前", "reading", "曲数", "slug"])
        for a in artists:
            writer.writerow([a["id"], a["name"], a.get("reading", ""), a["song_count"], a["slug"]])

    print(f"アーティストCSV出力完了: {artists_csv_path} ({len(artists)}件)")

    # 楽曲CSV出力
    songs_csv_path = os.path.join(OUTPUT_DIR, "merged_songs.csv")
    with open(songs_csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "曲名", "アーティスト名", "最低音", "最高音", "裏声最高音", "備考", "ソース"])
        for s in songs:
            artist_name = artist_name_map.get(s["artist_id"], f"(不明: {s['artist_id']})")
            writer.writerow([
                s["id"],
                s["title"],
                artist_name,
                s.get("lowest_note", ""),
                s.get("highest_note", ""),
                s.get("falsetto_note", ""),
                s.get("note", ""),
                s.get("source", ""),
            ])

    print(f"楽曲CSV出力完了: {songs_csv_path} ({len(songs)}件)")


if __name__ == "__main__":
    main()
