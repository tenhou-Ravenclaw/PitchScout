"""
recommender.py — おすすめ曲・似てるアーティスト

analyzeの結果とsongs.dbを照合して:
  1. 音域に合ったおすすめ曲（地声平均も考慮）
  2. 声質が似てるアーティスト
を返す。

歌唱力分析スコアは analysis/scoring.py に移動。

【おすすめ曲の配分】
  - DISCOVERY_SLOTS(4曲)は必ずお気に入り以外のアーティストから選ぶ
  - 残り枠(最大6曲)はお気に入りアーティストの曲で埋める
  - お気に入り登録がない場合は全枠を通常推薦に使用
"""

import math
import numpy as np
from note_converter import NOTE_TABLE, hz_to_label_and_hz
from db.songs import get_connection

# ============================================================
# カラオケ表記 ↔ Hz 変換
# ============================================================
_LABEL_TO_HZ = {label: hz for _, label, hz in NOTE_TABLE}

# ★ voice-key.news は mid1A/mid1A#/mid1B を使うが、
#    NOTE_TABLE は A3→mid2A にマッピングしている（A始まり区切り）。
#    DB内の692曲がサイレントに除外されるバグを修正。
#    同様に lowA/lowA#/lowB と lo* の表記揺れも対応。
_NOTE_ALIASES = {
    # mid1 A/A#/B → mid2 A/A#/B と同じ周波数
    "mid1A":   _LABEL_TO_HZ["mid2A"],     # 221.0
    "mid1A#":  _LABEL_TO_HZ["mid2A#"],    # 234.141
    "mid1B":   _LABEL_TO_HZ["mid2B"],     # 248.064
    # loX → lowX の表記揺れ
    "loC":     _LABEL_TO_HZ.get("lowC",  65.704),
    "loC#":    _LABEL_TO_HZ.get("lowC#", 69.611),
    "loD":     _LABEL_TO_HZ.get("lowD",  73.75),
    "loD#":    _LABEL_TO_HZ.get("lowD#", 78.135),
    "loE":     _LABEL_TO_HZ.get("lowE",  82.781),
    "loF":     _LABEL_TO_HZ.get("lowF",  87.704),
    "loF#":    _LABEL_TO_HZ.get("lowF#", 92.919),
    "loG":     _LABEL_TO_HZ.get("lowG",  98.444),
    "loG#":    _LABEL_TO_HZ.get("lowG#", 104.298),
    "loA":     _LABEL_TO_HZ.get("lowA",  110.5),
    "loA#":    _LABEL_TO_HZ.get("lowA#", 117.071),
    "loB":     _LABEL_TO_HZ.get("lowB",  124.032),
}
_LABEL_TO_HZ.update(_NOTE_ALIASES)


def label_to_hz(label: str) -> float | None:
    """カラオケ表記(mid2C等) → Hz。見つからなければNone"""
    if not label:
        return None
    return _LABEL_TO_HZ.get(label)


def _semitones(hz1: float, hz2: float) -> float:
    """2周波数間の半音数（hz2 > hz1 で正）"""
    if hz1 <= 0 or hz2 <= 0:
        return 0.0
    return 12.0 * math.log2(hz2 / hz1)


# ============================================================
# 1. おすすめ曲
# ============================================================

# お気に入りアーティスト以外から必ず確保する曲数
DISCOVERY_SLOTS = 4
# お気に入りアーティストに割り当てる最大曲数
FAV_MAX_SLOTS = 6
# アーティスト多様性フィルタ: 同一アーティスト最大曲数
MAX_PER_ARTIST = 2


def recommend_songs(
    chest_min_hz: float,
    chest_max_hz: float,
    chest_avg_hz: float,
    falsetto_max_hz: float | None = None,
    limit: int = 10,
    favorite_artist_ids: list[int] | None = None,
) -> list[dict]:
    """
    ユーザーの音域に合った楽曲をスコア順で返す。

    favorite_artist_ids が指定されている場合:
      - DISCOVERY_SLOTS(4曲)はお気に入り以外のアーティストから選ぶ
      - 残り枠(最大FAV_MAX_SLOTS=6曲)はお気に入りアーティストの曲で埋める
      - お気に入りに合う曲が少ない場合は通常曲で補完

    スコアリング:
      - 楽曲の音域がユーザーの地声範囲に収まるほど高スコア
      - 楽曲の中心音がユーザーの平均に近いほど高スコア
      - 裏声がある場合、裏声最高音も上限として考慮
      - 完全に範囲内ならボーナス加点
    """
    fav_ids: set[int] = set(favorite_artist_ids) if favorite_artist_ids else set()

    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT s.id, s.title, a.id as artist_id, a.name as artist,
                   s.lowest_note, s.highest_note, s.falsetto_note, s.source
            FROM songs s
            JOIN artists a ON s.artist_id = a.id
            WHERE s.lowest_note IS NOT NULL AND s.highest_note IS NOT NULL
        """).fetchall()

        # 裏声があればそこまで上限を広げる
        effective_max = chest_max_hz
        if falsetto_max_hz and falsetto_max_hz > chest_max_hz:
            effective_max = falsetto_max_hz

        fav_candidates: list[dict] = []
        normal_candidates: list[dict] = []

        for row in rows:
            r = dict(row)
            lo_hz = label_to_hz(r["lowest_note"])
            hi_hz = label_to_hz(r["highest_note"])
            # label_to_hz は未知ラベルで None、0Hz では無効値として明示的に None チェックする
            if lo_hz is None or hi_hz is None or lo_hz <= 0 or hi_hz <= 0 or lo_hz > hi_hz:
                continue

            # ペナルティ（半音単位）
            low_penalty = 0.0
            high_penalty = 0.0

            if lo_hz < chest_min_hz:
                low_penalty = _semitones(lo_hz, chest_min_hz)
            if hi_hz > effective_max:
                high_penalty = _semitones(effective_max, hi_hz)

            # 中心音のずれ
            song_center = math.sqrt(lo_hz * hi_hz)
            center_diff = abs(_semitones(chest_avg_hz, song_center)) if chest_avg_hz > 0 else 0.0

            # スコア計算
            score = 100.0
            score -= low_penalty * 6.0
            score -= high_penalty * 8.0
            score -= center_diff * 2.0

            if low_penalty == 0 and high_penalty == 0:
                score += 5.0

            if score <= 30:
                continue

            entry = {
                "id": r["id"],
                "title": r["title"],
                "artist": r["artist"],
                "artist_id": r["artist_id"],
                "lowest_note": r["lowest_note"],
                "highest_note": r["highest_note"],
                "match_score": round(min(100.0, score), 1),
            }

            if fav_ids and r["artist_id"] in fav_ids:
                fav_candidates.append(entry)
            else:
                normal_candidates.append(entry)

        fav_candidates.sort(key=lambda x: x["match_score"], reverse=True)
        normal_candidates.sort(key=lambda x: x["match_score"], reverse=True)

        # --- 枠配分 ---
        # お気に入りがない場合は全部 normal に
        if not fav_ids:
            fav_slots = 0
        else:
            fav_slots = min(FAV_MAX_SLOTS, limit - DISCOVERY_SLOTS)

        discovery_slots = limit - fav_slots

        def pick_with_diversity(candidates: list[dict], n: int) -> list[dict]:
            """
            アーティスト多様性フィルタ付きで n 曲選ぶ。

            同一アーティストの曲が MAX_PER_ARTIST 曲を超えて選ばれないよう制限し、
            推薦結果の多様性を確保する。candidates はスコア降順でソート済みを前提とする。

            Args:
                candidates: 推薦候補の楽曲リスト（スコア降順ソート済み）。
                n: 選択する最大曲数。

            Returns:
                アーティスト多様性を考慮して選んだ楽曲リスト（最大 n 曲）。
            """
            result_list: list[dict] = []
            artist_count: dict[str, int] = {}
            for c in candidates:
                name = c["artist"]
                if artist_count.get(name, 0) >= MAX_PER_ARTIST:
                    continue
                artist_count[name] = artist_count.get(name, 0) + 1
                result_list.append(c)
                if len(result_list) >= n:
                    break
            return result_list

        # お気に入りアーティスト枠
        fav_picks = pick_with_diversity(fav_candidates, fav_slots)
        fav_artist_names_used = {c["artist"] for c in fav_picks}

        # ディスカバリー枠: お気に入りアーティストを除外
        discovery_pool = [c for c in normal_candidates if c["artist"] not in fav_artist_names_used]
        discovery_picks = pick_with_diversity(discovery_pool, discovery_slots)

        # お気に入り枠が埋まらなかった場合は normal で補完
        shortfall = fav_slots - len(fav_picks)
        if shortfall > 0:
            extra_pool = [
                c for c in normal_candidates
                if c["artist"] not in fav_artist_names_used
                and c not in discovery_picks
            ]
            extra_picks = pick_with_diversity(extra_pool, shortfall)
            discovery_picks.extend(extra_picks)

        combined = fav_picks + discovery_picks

        # --- キー変更おすすめを付与、artist_id を削除 ---
        result_final = []
        for c in combined:
            key_info = recommend_key_for_song(
                c.get("lowest_note"), c.get("highest_note"),
                chest_min_hz, effective_max,
            )
            c.update(key_info)
            c.pop("artist_id", None)
            # お気に入りアーティストの曲かどうかフラグを付ける
            c["is_favorite_artist"] = c["artist"] in {
                name for entry in fav_picks for name in [entry["artist"]]
            }
            result_final.append(c)

        return result_final[:limit]

    finally:
        conn.close()


# ============================================================
# 2. チャレンジ曲推薦
# ============================================================

def _challenge_reason(high_penalty: float, low_penalty: float, center_diff: float) -> str:
    """
    チャレンジ曲の主な難易度要因を日本語で説明する。

    Args:
        high_penalty: 最高音ペナルティ（半音数）。
        low_penalty:  最低音ペナルティ（半音数）。
        center_diff:  中心音のずれ（半音数）。

    Returns:
        難易度要因の説明文字列。
    """
    if high_penalty >= 2.0:
        semitones = round(high_penalty)
        return f"最高音が約{semitones}半音高い（練習で届く範囲）"
    if low_penalty >= 1.0:
        semitones = round(low_penalty)
        return f"最低音が約{semitones}半音低い"
    if center_diff >= 3.0:
        return "音域の中心がやや高め"
    return "もう少しで歌える曲"


def recommend_challenge_songs(
    chest_min_hz: float,
    chest_max_hz: float,
    chest_avg_hz: float,
    falsetto_max_hz: float | None = None,
    limit: int = 5,
) -> list[dict]:
    """
    チャレンジ曲（あと少しで歌える曲）をスコア順で返す。

    通常推薦（recommend_songs）がスコア30以下で切り捨てる楽曲のうち、
    ユーザーの音域をわずかに超えるだけの曲（高音ペナルティ 1〜5半音）を対象とする。
    低音が大幅に不足する曲（3半音超）や音域が極端に離れた曲は除外する。

    Args:
        chest_min_hz:    ユーザーの地声最低音 (Hz)。
        chest_max_hz:    ユーザーの地声最高音 (Hz)。
        chest_avg_hz:    ユーザーの地声平均音 (Hz)。
        falsetto_max_hz: ユーザーの裏声最高音 (Hz)。None なら地声のみ考慮。
        limit:           返す最大曲数。

    Returns:
        チャレンジ曲のリスト（match_score 降順、各曲に challenge_reason を付与）。
    """
    effective_max = chest_max_hz
    if falsetto_max_hz and falsetto_max_hz > chest_max_hz:
        effective_max = falsetto_max_hz

    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT s.id, s.title, a.id as artist_id, a.name as artist,
                   s.lowest_note, s.highest_note
            FROM songs s
            JOIN artists a ON s.artist_id = a.id
            WHERE s.lowest_note IS NOT NULL AND s.highest_note IS NOT NULL
        """).fetchall()

        candidates: list[dict] = []
        for row in rows:
            r = dict(row)
            lo_hz = label_to_hz(r["lowest_note"])
            hi_hz = label_to_hz(r["highest_note"])
            if lo_hz is None or hi_hz is None or lo_hz <= 0 or hi_hz <= 0 or lo_hz > hi_hz:
                continue

            low_penalty = _semitones(lo_hz, chest_min_hz) if lo_hz < chest_min_hz else 0.0
            high_penalty = _semitones(effective_max, hi_hz) if hi_hz > effective_max else 0.0
            song_center = math.sqrt(lo_hz * hi_hz)
            center_diff = abs(_semitones(chest_avg_hz, song_center)) if chest_avg_hz > 0 else 0.0

            score = 100.0
            score -= low_penalty * 6.0
            score -= high_penalty * 8.0
            score -= center_diff * 2.0

            # チャレンジ曲: スコア 5〜30 かつ低音ペナルティが軽微・高音ペナルティが現実的な範囲
            if not (5.0 < score <= 30.0):
                continue
            if low_penalty > 3.0:
                continue  # 低音が大幅不足な曲は喉への負担が大きいため除外
            if high_penalty > 5.0:
                continue  # 5半音以上高い曲は短期練習で届かないため除外

            key_info = recommend_key_for_song(
                r["lowest_note"], r["highest_note"],
                chest_min_hz, effective_max,
            )
            candidates.append({
                "id": r["id"],
                "title": r["title"],
                "artist": r["artist"],
                "artist_id": r["artist_id"],
                "lowest_note": r["lowest_note"],
                "highest_note": r["highest_note"],
                "match_score": round(score, 1),
                "challenge_reason": _challenge_reason(high_penalty, low_penalty, center_diff),
                **key_info,
            })

        candidates.sort(key=lambda x: x["match_score"], reverse=True)

        # アーティスト多様性フィルタ
        result: list[dict] = []
        artist_count: dict[str, int] = {}
        for c in candidates:
            name = c["artist"]
            if artist_count.get(name, 0) >= MAX_PER_ARTIST:
                continue
            artist_count[name] = artist_count.get(name, 0) + 1
            c.pop("artist_id", None)
            result.append(c)
            if len(result) >= limit:
                break

        return result
    finally:
        conn.close()


# ============================================================
# 3. 似てるアーティスト
# ============================================================
def find_similar_artists(
    chest_min_hz: float,
    chest_max_hz: float,
    chest_avg_hz: float,
    limit: int = 5,
) -> list[dict]:
    """
    ユーザーの音域に最も近いアーティストを返す。
    各アーティストの全楽曲の中央値(最低音/最高音)で比較。
    """
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT a.id, a.name, a.song_count,
                   s.lowest_note, s.highest_note
            FROM songs s
            JOIN artists a ON s.artist_id = a.id
            WHERE s.lowest_note IS NOT NULL AND s.highest_note IS NOT NULL
        """).fetchall()

        artists: dict[int, dict] = {}
        for row in rows:
            r = dict(row)
            aid = r["id"]
            lo_hz = label_to_hz(r["lowest_note"])
            hi_hz = label_to_hz(r["highest_note"])
            if lo_hz is None or hi_hz is None or lo_hz <= 0 or hi_hz <= 0:
                continue
            if aid not in artists:
                artists[aid] = {
                    "id": aid,
                    "name": r["name"],
                    "song_count": r["song_count"],
                    "lows": [],
                    "highs": [],
                }
            artists[aid]["lows"].append(lo_hz)
            artists[aid]["highs"].append(hi_hz)

        results = []
        for data in artists.values():
            if len(data["lows"]) < 2:
                continue

            med_low = float(np.median(data["lows"]))
            med_high = float(np.median(data["highs"]))
            med_center = math.sqrt(med_low * med_high)

            low_diff = abs(_semitones(med_low, chest_min_hz))
            high_diff = abs(_semitones(med_high, chest_max_hz))
            center_diff = (
                abs(_semitones(med_center, chest_avg_hz)) if chest_avg_hz > 0 else 99.0
            )

            similarity = 100.0 - (low_diff * 3.0 + high_diff * 3.0 + center_diff * 4.0)

            if similarity > 20:
                lo_label, _ = hz_to_label_and_hz(med_low)
                hi_label, _ = hz_to_label_and_hz(med_high)
                results.append({
                    "id": data["id"],
                    "name": data["name"],
                    "song_count": data["song_count"],
                    "typical_lowest": lo_label,
                    "typical_highest": hi_label,
                    "similarity_score": round(min(100.0, similarity), 1),
                })

        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:limit]
    finally:
        conn.close()


# ============================================================
# 4. 声質タイプ判定
# ============================================================
def classify_voice_type(
    chest_min_hz: float,
    chest_max_hz: float,
    chest_avg_hz: float,
    falsetto_max_hz: float | None,
    chest_ratio: float,
) -> dict:
    """
    音域と声区比率から声質タイプを判定。

    Returns:
        {
            "voice_type":   "ハイトーン" etc,
            "description":  説明文,
            "range_class":  "テノール" etc,
        }
    """
    if chest_avg_hz >= 350:
        range_class = "ハイテノール"
    elif chest_avg_hz >= 280:
        range_class = "テノール"
    elif chest_avg_hz >= 220:
        range_class = "バリトン"
    elif chest_avg_hz >= 160:
        range_class = "バス・バリトン"
    else:
        range_class = "バス"

    range_st = _semitones(chest_min_hz, chest_max_hz) if chest_min_hz > 0 and chest_max_hz > 0 else 0
    has_wide_range = range_st >= 15
    uses_falsetto = chest_ratio < 85
    high_voice = chest_max_hz >= 400

    if high_voice and uses_falsetto:
        voice_type = "ハイトーン・ミックス"
        description = "高音域を裏声と地声を切り替えて歌うタイプ。J-POPの多くの楽曲に対応できます。"
    elif high_voice and not uses_falsetto:
        voice_type = "パワフル・ハイトーン"
        description = "地声で高音域まで出せるパワフルなタイプ。力強い歌唱が持ち味です。"
    elif has_wide_range and uses_falsetto:
        voice_type = "表現力豊かなミックス"
        description = "広い音域を地声と裏声で使い分ける表現力豊かなタイプ。バラードからアップテンポまで幅広く対応。"
    elif has_wide_range:
        voice_type = "ワイドレンジ"
        description = "広い音域を地声でカバーできるタイプ。安定感のある歌唱が特徴です。"
    elif uses_falsetto:
        voice_type = "ファルセット主体"
        description = "裏声を多用する繊細な歌唱タイプ。やわらかい声質が魅力です。"
    elif chest_max_hz >= 350:
        voice_type = "ミドル・ハイ"
        description = "中〜高音域が得意なバランスの取れたタイプ。多くのポップスに対応できます。"
    else:
        voice_type = "ロー・ミドル"
        description = "中〜低音域が安定したタイプ。落ち着いた楽曲や渋い曲が合います。"

    return {
        "voice_type": voice_type,
        "description": description,
        "range_class": range_class,
    }


# ============================================================
# 5. キー変更おすすめ
# ============================================================
def recommend_key_for_song(
    song_lowest_note: str | None,
    song_highest_note: str | None,
    user_min_hz: float,
    user_max_hz: float,
) -> dict:
    """
    楽曲に対してユーザーの音域に最適なキー変更を計算。

    Returns:
        {
            "recommended_key": int (-7〜+7, 0=原曲キー),
            "fit": "perfect" | "good" | "ok" | "hard",
        }
    """
    song_lo = label_to_hz(song_lowest_note) if song_lowest_note else None
    song_hi = label_to_hz(song_highest_note) if song_highest_note else None

    if not song_lo or not song_hi or user_min_hz <= 0 or user_max_hz <= 0:
        return {"recommended_key": 0, "fit": "unknown"}

    best_shift = 0
    best_score = -9999.0

    for shift in range(-7, 8):
        factor = 2.0 ** (shift / 12.0)
        lo = song_lo * factor
        hi = song_hi * factor

        low_pen = _semitones(lo, user_min_hz) if lo < user_min_hz else 0.0
        high_pen = _semitones(user_max_hz, hi) if hi > user_max_hz else 0.0
        shift_pen = abs(shift) * 2.0

        score = 100.0 - low_pen * 6.0 - high_pen * 10.0 - shift_pen

        if score > best_score:
            best_score = score
            best_shift = shift

    if best_score >= 90:
        fit = "perfect"
    elif best_score >= 70:
        fit = "good"
    elif best_score >= 50:
        fit = "ok"
    else:
        fit = "hard"

    return {"recommended_key": best_shift, "fit": fit}


# ============================================================
# 6. 統合音域集計（複数の分析履歴レコードから集計）
# ============================================================

def _get_falsetto_min_hz_from_result(result: dict) -> float | None:
    """
    result_json から裏声最低音 Hz を取得する。

    新形式（falsetto_min_hz キー）と旧形式（falsetto_min ラベル文字列）の
    両方に対応する互換ヘルパー。

    Args:
        result: 分析レコードの result_json フィールド。

    Returns:
        裏声最低音 (Hz)。取得できない場合は None。
    """
    if result.get("falsetto_min_hz"):
        return float(result["falsetto_min_hz"])
    if result.get("falsetto_min"):
        # 旧データ形式: ラベル文字列（例: "mid2E"）を Hz に変換
        return label_to_hz(result["falsetto_min"])
    return None

def aggregate_vocal_range(
    records: list[dict],
    favorite_artist_ids: list[int] | None = None,
) -> dict | None:
    """
    複数の分析履歴レコードから統合音域と総合分析を計算する。

    database_supabase.py の DB 取得ロジックを分離し、ビジネスロジック層に集約。
    DB 取得は呼び出し元（routers/users.py）が行い、本関数はレコードリストを受け取る。

    Args:
        records: get_analysis_history() が返すレコードのリスト
        favorite_artist_ids: お気に入りアーティストIDリスト（おすすめ曲の優先度に使用）

    Returns:
        統合音域・タイプ・おすすめ曲・アーティスト・歌唱力指標を含む辞書。
        有効データがない場合は None。
    """
    if not records:
        return None

    # Hz値のリストを収集
    chest_min_values: list[float] = []
    chest_max_values: list[float] = []
    falsetto_min_values: list[float] = []
    falsetto_max_values: list[float] = []
    overall_min_values: list[float] = []
    overall_max_values: list[float] = []
    chest_ratio_values: list[float] = []

    # 歌唱力指標の収集
    range_scores: list[float] = []
    stability_scores: list[float] = []
    expression_scores: list[float] = []
    overall_scores: list[float] = []

    valid_count = 0
    for record in records:
        # result_json がある場合はそこから取得
        if record.get("result_json"):
            result = record["result_json"]
            if result.get("chest_min_hz"):
                chest_min_values.append(result["chest_min_hz"])
            if result.get("chest_max_hz"):
                chest_max_values.append(result["chest_max_hz"])
            hz = _get_falsetto_min_hz_from_result(result)
            if hz:
                falsetto_min_values.append(hz)
            if result.get("falsetto_max_hz"):
                falsetto_max_values.append(result["falsetto_max_hz"])
            if result.get("overall_min_hz"):
                overall_min_values.append(result["overall_min_hz"])
            if result.get("overall_max_hz"):
                overall_max_values.append(result["overall_max_hz"])
            if result.get("chest_ratio") is not None:
                chest_ratio_values.append(result["chest_ratio"])

            # 歌唱力指標
            if result.get("singing_analysis"):
                sa = result["singing_analysis"]
                if sa.get("range_score") is not None:
                    range_scores.append(sa["range_score"])
                if sa.get("stability_score") is not None:
                    stability_scores.append(sa["stability_score"])
                if sa.get("expression_score") is not None:
                    expression_scores.append(sa["expression_score"])
                if sa.get("overall_score") is not None:
                    overall_scores.append(sa["overall_score"])

            valid_count += 1
        # 古い形式の場合は直接取得
        elif record.get("vocal_range_min_hz") or record.get("vocal_range_max_hz"):
            if record.get("vocal_range_min_hz"):
                overall_min_values.append(record["vocal_range_min_hz"])
                chest_min_values.append(record["vocal_range_min_hz"])
            if record.get("vocal_range_max_hz"):
                overall_max_values.append(record["vocal_range_max_hz"])
                chest_max_values.append(record["vocal_range_max_hz"])
            if record.get("falsetto_max_hz"):
                falsetto_max_values.append(record["falsetto_max_hz"])
            valid_count += 1

    if valid_count == 0:
        return None

    # 統合値を計算（最小値と最大値を採用）
    aggregated: dict = {
        "data_count": valid_count,
        "limit": len(records),
    }

    # 音域情報
    if overall_min_values:
        overall_min_hz = min(overall_min_values)
        overall_min_label, overall_min_hz_val = hz_to_label_and_hz(overall_min_hz)
        aggregated["overall_min"] = overall_min_label
        aggregated["overall_min_hz"] = overall_min_hz_val

    if overall_max_values:
        overall_max_hz = max(overall_max_values)
        overall_max_label, overall_max_hz_val = hz_to_label_and_hz(overall_max_hz)
        aggregated["overall_max"] = overall_max_label
        aggregated["overall_max_hz"] = overall_max_hz_val

    chest_min_hz_val: float | None = None
    if chest_min_values:
        chest_min_hz = min(chest_min_values)
        chest_min_label, chest_min_hz_val = hz_to_label_and_hz(chest_min_hz)
        aggregated["chest_min"] = chest_min_label
        aggregated["chest_min_hz"] = chest_min_hz_val

    chest_max_hz_val: float | None = None
    if chest_max_values:
        chest_max_hz = max(chest_max_values)
        chest_max_label, chest_max_hz_val = hz_to_label_and_hz(chest_max_hz)
        aggregated["chest_max"] = chest_max_label
        aggregated["chest_max_hz"] = chest_max_hz_val

    if falsetto_min_values:
        falsetto_min_hz = min(falsetto_min_values)
        falsetto_min_label, falsetto_min_hz_val = hz_to_label_and_hz(falsetto_min_hz)
        aggregated["falsetto_min"] = falsetto_min_label
        aggregated["falsetto_min_hz"] = falsetto_min_hz_val

    falsetto_max_hz_val: float | None = None
    if falsetto_max_values:
        falsetto_max_hz = max(falsetto_max_values)
        falsetto_max_label, falsetto_max_hz_val = hz_to_label_and_hz(falsetto_max_hz)
        aggregated["falsetto_max"] = falsetto_max_label
        aggregated["falsetto_max_hz"] = falsetto_max_hz_val

    # 地声比率の平均（pipeline.py が 0〜100 のパーセント値で格納するためそのまま平均）
    avg_chest_ratio = sum(chest_ratio_values) / len(chest_ratio_values) if chest_ratio_values else 80.0
    aggregated["chest_ratio"] = avg_chest_ratio
    aggregated["falsetto_ratio"] = 100.0 - avg_chest_ratio

    # 歌唱力指標の平均
    if range_scores or stability_scores or expression_scores or overall_scores:
        aggregated["singing_analysis"] = {}
        if range_scores:
            aggregated["singing_analysis"]["range_score"] = sum(range_scores) / len(range_scores)
        if stability_scores:
            aggregated["singing_analysis"]["stability_score"] = sum(stability_scores) / len(stability_scores)
        if expression_scores:
            aggregated["singing_analysis"]["expression_score"] = sum(expression_scores) / len(expression_scores)
        if overall_scores:
            aggregated["singing_analysis"]["overall_score"] = sum(overall_scores) / len(overall_scores)

        # 音域の半音数を計算
        if chest_min_hz_val and chest_max_hz_val:
            aggregated["singing_analysis"]["range_semitones"] = round(
                12 * math.log2(chest_max_hz_val / chest_min_hz_val)
            )

    # 声質タイプ・おすすめ曲・似てるアーティストを追加（chest Hz が揃っている場合のみ）
    if chest_min_hz_val and chest_max_hz_val:
        # 幾何平均で chest_avg を算出
        chest_avg_hz = math.sqrt(chest_min_hz_val * chest_max_hz_val)

        aggregated["voice_type"] = classify_voice_type(
            chest_min_hz_val,
            chest_max_hz_val,
            chest_avg_hz,
            falsetto_max_hz_val,
            avg_chest_ratio,
        )

        aggregated["similar_artists"] = find_similar_artists(
            chest_min_hz_val,
            chest_max_hz_val,
            chest_avg_hz,
            limit=5,
        )

        aggregated["recommended_songs"] = recommend_songs(
            chest_min_hz_val,
            chest_max_hz_val,
            chest_avg_hz,
            falsetto_max_hz_val,
            limit=10,
            favorite_artist_ids=list(favorite_artist_ids) if favorite_artist_ids else [],
        )

    return aggregated