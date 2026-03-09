"""CSV内部整合性修正スクリプト

artists_check_fixed.csv を正として、songs_check_fixed.csv との整合性を修正する。
3つの修正を順番に実行:
1. 重複アーティスト統合（artists CSV + songs CSV）
2. artist_name 表記統一（songs CSV）
3. song_count 再計算（artists CSV）
"""

import csv
import sys
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
SONGS_CSV = OUTPUT_DIR / "songs_check_fixed.csv"
ARTISTS_CSV = OUTPUT_DIR / "artists_check_fixed.csv"


def load_csv(path: Path) -> list[dict[str, str]]:
    """CSVファイルを読み込み、辞書のリストとして返す。"""
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    """辞書のリストをCSVファイルに書き出す。"""
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fix_duplicate_artists(
    songs: list[dict[str, str]], artists: list[dict[str, str]]
) -> tuple[int, int]:
    """修正1: 重複アーティストを統合する。

    統合先の名前に songs の artist_name を書き換え、
    削除対象を artists から除去する。

    Returns:
        (書き換えた曲数, 削除したアーティスト数) のタプル
    """
    # (統合先名, [削除対象名のリスト])
    merge_rules: list[tuple[str, list[str]]] = [
        ("＝LOVE", ["=LOVE"]),
        ("イナメトオル【40mP】", ["イナメトオル【40mp】"]),
        ("−真天地開闢集団−ジグザグ", ["-真天地開闢集団- ジグザグ"]),
        ("Hilcrhyme", ["Hilcrhyme)ヒルクライム"]),
        ("FUNKY MONKEY BABYS", ["FUNKY MONKEY BΛBY'S"]),
        ("My Little Lover", ["MY LITTLE LOVER"]),
        ("L'Arc~en~Ciel", ["L'Arc-en-Ciel"]),
        ("T.M.Revolution", ["T.M.Revolution[西川貴教]"]),
        ("reGretGirl", ["reGretGirl[リグレットガール]"]),
        ("須田景凪[バルーン]", ["須田景凪【バルーン】セルフカバー"]),
        ("GReeeeN", ["GReeeeN[現GRe4N BOYZ]", "GReeeeN [現 GRe4N BOYZ]"]),
        ("桜高軽音部", ["桜高軽音部[放課後ティータイム]", "放課後ティータイム"]),
    ]

    # songs CSV 用: 削除対象名 → 統合先名
    song_rename_map: dict[str, str] = {}
    # artists CSV 用: 削除対象名の集合
    delete_names: set[str] = set()

    for keep_name, del_names in merge_rules:
        for dn in del_names:
            song_rename_map[dn] = keep_name
            delete_names.add(dn)

    # songs の artist_name にはアーティストCSVと異なる表記がある場合がある
    # 例: songs では "-真天地開闢集団-ジグザグ"（スペースなし）だが
    #     artists の削除対象は "-真天地開闢集団- ジグザグ"（スペースあり）
    # → songs 側の表記も統合先に変換する追加マッピング
    extra_song_renames: dict[str, str] = {
        "-真天地開闢集団-ジグザグ": "−真天地開闢集団−ジグザグ",
        "Hilcrhyme(ヒルクライム": "Hilcrhyme",
        "FUNKY MONKEY BΛBY\u2019S": "FUNKY MONKEY BABYS",
    }
    song_rename_map.update(extra_song_renames)

    # songs の artist_name を書き換え
    renamed_count = 0
    for song in songs:
        old = song["artist_name"]
        if old in song_rename_map:
            song["artist_name"] = song_rename_map[old]
            renamed_count += 1

    # artists から削除対象を除去
    original_len = len(artists)
    artists[:] = [a for a in artists if a["name"] not in delete_names]
    deleted_count = original_len - len(artists)

    print(f"[修正1] 重複アーティスト統合: {renamed_count} 曲を書き換え, {deleted_count} アーティストを削除")
    return renamed_count, deleted_count


def fix_artist_name_notation(
    songs: list[dict[str, str]], artists: list[dict[str, str]]
) -> int:
    """修正2: songs CSV の artist_name を artists CSV の name に統一する。

    Returns:
        書き換えた曲数
    """
    artist_names: set[str] = {a["name"] for a in artists}

    # 明示的な変換マッピング（songs表記 → artists正式名）
    explicit_map: dict[str, str] = {
        # アポストロフィ統一 ' → \u2019
        "B'z": "B\u2019z",
        "SHE'S": "SHE\u2019S",
        "OKAMOTO'S": "OKAMOTO\u2019S",
        "Amber's": "Amber\u2019s",
        "JAY'ED": "JAY\u2019ED",
        "JITTERIN'JINN": "JITTERIN\u2019JINN",
        "La'cryma Christi": "La\u2019cryma Christi",
        "SOMETIME'S": "SOMETIME\u2019S",
        "SOUL'd OUT": "SOUL\u2019d OUT",
        "μ's": "μ\u2019s",
        "Fischer's[フィッシャーズ]": "Fischer\u2019s[フィッシャーズ]",
        "んだほ & ぺけたん from Fischer's": "んだほ & ぺけたん from Fischer\u2019s",
        # 全角チルダ → 半角チルダ + アポストロフィ統一
        "L'Arc〜en〜Ciel": "L\u2019Arc~en~Ciel",
        # 大文字小文字
        "[ALEXANDROS]": "[Alexandros]",
        "Gackt": "GACKT",
        "REOL": "Reol",
        # 名前の違い
        "CK": "C&K",
        "Motoki Ohmori[大森元貴]": "大森元貴",
        "ゲスの極み乙女。": "ゲスの極み乙女",
        "櫻坂46": "桜坂46",
        # 閉じ括弧の欠落
        "Nissy(西島隆弘": "Nissy(西島隆弘)",
        "LIP×LIP(勇次郎・愛蔵/CV:内山昂輝・島崎信長": "LIP×LIP(勇次郎・愛蔵/CV:内山昂輝・島崎信長)",
        "シュヴァルグラン(CV.夏吉ゆうこ": "シュヴァルグラン(CV.夏吉ゆうこ)",
        "シン(阿部サダヲ": "シン(阿部サダヲ)",
        "千石撫子(花澤香菜": "千石撫子(花澤香菜)",
        "浦島太郎(桐谷健太": "浦島太郎(桐谷健太)",
        "Lanndo feat.Eve,suis(from ヨルシカ": "Lanndo feat.Eve,suis(from ヨルシカ)",
        "ハマいく[濱家隆一(かまいたち": "ハマいく[濱家隆一(かまいたち)]",
    }

    # マッピング先が artists CSV に存在するか検証
    errors: list[str] = []
    for old, new in explicit_map.items():
        if new not in artist_names:
            errors.append(f"  マッピング先が artists CSV に存在しない: \"{old}\" → \"{new}\"")
    if errors:
        print("[エラー] マッピング検証失敗:")
        for e in errors:
            print(e)
        sys.exit(1)

    renamed_count = 0
    for song in songs:
        old = song["artist_name"]
        if old in explicit_map:
            song["artist_name"] = explicit_map[old]
            renamed_count += 1

    print(f"[修正2] artist_name 表記統一: {renamed_count} 曲を書き換え")
    return renamed_count


def fix_song_count(
    songs: list[dict[str, str]], artists: list[dict[str, str]]
) -> int:
    """修正3: artists CSV の song_count を songs CSV から再計算する。

    Returns:
        更新したアーティスト数
    """
    # songs CSV から各 artist_name の曲数をカウント
    count_map: dict[str, int] = {}
    for song in songs:
        name = song["artist_name"]
        count_map[name] = count_map.get(name, 0) + 1

    updated_count = 0
    for artist in artists:
        name = artist["name"]
        actual = count_map.get(name, 0)
        current = int(artist["song_count"])
        if current != actual:
            artist["song_count"] = str(actual)
            updated_count += 1

    print(f"[修正3] song_count 再計算: {updated_count} アーティストを更新")
    return updated_count


def validate(songs: list[dict[str, str]], artists: list[dict[str, str]]) -> bool:
    """修正後の整合性を検証する。

    Returns:
        全検証に合格した場合 True
    """
    artist_names = {a["name"] for a in artists}
    artist_ids = [a["id"] for a in artists]
    ok = True

    # 1. songs の全 artist_name が artists の name に存在する
    unmatched: dict[str, int] = {}
    for song in songs:
        an = song["artist_name"]
        if an not in artist_names:
            unmatched[an] = unmatched.get(an, 0) + 1
    if unmatched:
        ok = False
        print("\n[検証NG] songs に存在するが artists にないアーティスト:")
        for name, cnt in sorted(unmatched.items()):
            print(f"  [{cnt}曲] \"{name}\"")

    # 2. artists の song_count が songs の実曲数と一致する
    count_map: dict[str, int] = {}
    for song in songs:
        name = song["artist_name"]
        count_map[name] = count_map.get(name, 0) + 1

    mismatches: list[str] = []
    for artist in artists:
        name = artist["name"]
        expected = count_map.get(name, 0)
        actual = int(artist["song_count"])
        if expected != actual:
            mismatches.append(f"  \"{name}\": song_count={actual}, 実曲数={expected}")
    if mismatches:
        ok = False
        print("\n[検証NG] song_count 不一致:")
        for m in mismatches:
            print(m)

    # 3. artists に名前・IDの重複がない
    seen_names: dict[str, int] = {}
    seen_ids: dict[str, int] = {}
    dup_names: list[str] = []
    dup_ids: list[str] = []
    for a in artists:
        if a["name"] in seen_names:
            dup_names.append(f"  \"{a['name']}\" (id={a['id']} と id={seen_names[a['name']]})")
        seen_names[a["name"]] = a["id"]
        if a["id"] in seen_ids:
            dup_ids.append(f"  id={a['id']}")
        seen_ids[a["id"]] = 1
    if dup_names:
        ok = False
        print("\n[検証NG] アーティスト名の重複:")
        for d in dup_names:
            print(d)
    if dup_ids:
        ok = False
        print("\n[検証NG] アーティストIDの重複:")
        for d in dup_ids:
            print(d)

    if ok:
        print("\n[検証OK] 全チェック合格")
    return ok


def main() -> None:
    """メイン処理: CSV読み込み → 3段階修正 → 検証 → 保存。"""
    print(f"=== CSV内部整合性修正 ===\n")

    # 読み込み
    songs = load_csv(SONGS_CSV)
    artists = load_csv(ARTISTS_CSV)
    print(f"読み込み: songs={len(songs)}曲, artists={len(artists)}アーティスト\n")

    # 修正1: 重複アーティスト統合
    fix_duplicate_artists(songs, artists)

    # 修正2: artist_name 表記統一
    fix_artist_name_notation(songs, artists)

    # 修正3: song_count 再計算
    fix_song_count(songs, artists)

    # 検証
    print("\n=== 検証 ===")
    ok = validate(songs, artists)

    if not ok:
        print("\n[警告] 検証に失敗した項目があります。CSV は保存しません。")
        sys.exit(1)

    # 保存
    song_fields = ["id", "artist_name", "title", "lowest_note", "highest_note", "falsetto_note", "source"]
    artist_fields = ["id", "name", "slug", "song_count", "reading"]
    save_csv(SONGS_CSV, songs, song_fields)
    save_csv(ARTISTS_CSV, artists, artist_fields)

    print(f"\n保存完了: {SONGS_CSV.name}, {ARTISTS_CSV.name}")

    # 変更サマリー
    print(f"\n=== サマリー ===")
    print(f"  songs: {len(songs)} 曲")
    print(f"  artists: {len(artists)} アーティスト")


if __name__ == "__main__":
    main()
