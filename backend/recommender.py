"""
recommender.py — 歌唱力分析・おすすめ曲・似てるアーティスト

analyzeの結果とSupabase楽曲データを照合して:
  1. 歌唱力分析スコア（音域・安定性・表現力）
  2. 音域に合ったおすすめ曲（地声平均も考慮）
  3. 声質が似てるアーティスト
を返す。

【おすすめ曲の配分】
  - DISCOVERY_SLOTS(4曲)は必ずお気に入り以外のアーティストから選ぶ
  - 残り枠(最大6曲)はお気に入りアーティストの曲で埋める
  - お気に入り登録がない場合は全枠を通常推薦に使用
"""

import math
import numpy as np
from note_converter import NOTE_TABLE, hz_to_label_and_hz
from database_supabase import supabase

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
# 1. 歌唱力分析
# ============================================================
def analyze_singing_ability(
    f0_array: np.ndarray,
    conf_array: np.ndarray,
    chest_notes: list[float],
    falsetto_notes: list[float],
    overall_min_hz: float,
    overall_max_hz: float,
) -> dict:
    """
    CREPE解析データから歌唱力指標を算出

    Returns:
        {
            "range_semitones": 音域の広さ(半音),
            "range_score":     音域スコア(0-100),
            "stability_score": 安定性スコア(0-100),
            "expression_score":表現力スコア(0-100),
            "overall_score":   総合スコア(0-100),
        }
    """
    result = {}

    # --- 音域の広さ ---
    # 一般: 1-1.5oct(12-18st), 上手い: 2oct(24st), プロ級: 2.5+oct(30+st)
    range_st = _semitones(overall_min_hz, overall_max_hz)
    range_score = min(100.0, (range_st / 30.0) * 100.0)
    result["range_semitones"] = round(range_st, 1)
    result["range_score"] = round(range_score, 1)

    # --- ピッチ安定性 ---
    stability_score = _compute_stability(f0_array, conf_array)
    result["stability_score"] = round(stability_score, 1)

    # --- 表現力（声区の使い分け＋音域の活用度） ---
    expression_score = _compute_expression(
        chest_notes, falsetto_notes, overall_min_hz, overall_max_hz
    )
    result["expression_score"] = round(expression_score, 1)

    # --- 総合スコア ---
    overall = range_score * 0.30 + stability_score * 0.45 + expression_score * 0.25
    result["overall_score"] = round(overall, 1)

    return result


def _compute_stability(f0: np.ndarray, conf: np.ndarray) -> float:
    """ピッチ安定性スコア (0-100)

    持続音セグメント内のピッチ偏差を計測する。
    隣接フレーム間のピッチ差が1半音以内なら同一音符とみなし、
    3フレーム以上続くセグメントごとにセント標準偏差を算出、
    セグメント長で重み付き平均 → スコア化。
    """
    from config import STABILITY_MIN_SEGMENT, STABILITY_SCALING

    mask = (conf >= 0.3) & (f0 > 0)
    f0_valid = f0[mask]
    if len(f0_valid) < 10:
        return 50.0

    semitone_ratio = 2 ** (1 / 12)  # ≈1.0595
    segments = []
    current_seg = [f0_valid[0]]

    for i in range(1, len(f0_valid)):
        ratio = f0_valid[i] / f0_valid[i - 1]
        if 1 / semitone_ratio <= ratio <= semitone_ratio:
            current_seg.append(f0_valid[i])
        else:
            if len(current_seg) >= STABILITY_MIN_SEGMENT:
                segments.append(current_seg)
            current_seg = [f0_valid[i]]
    if len(current_seg) >= STABILITY_MIN_SEGMENT:
        segments.append(current_seg)

    if not segments:
        return 50.0

    weighted_sum = 0.0
    total_frames = 0
    for seg in segments:
        arr = np.array(seg)
        med = np.median(arr)
        cents = 1200.0 * np.log2(arr / med)
        weighted_sum += float(np.std(cents)) * len(seg)
        total_frames += len(seg)

    avg_std = weighted_sum / total_frames
    # 目安: 10cents=プロ(92), 25cents=上手い素人(80), 40cents=普通のカラオケ(68), 75+=40以下
    return max(0.0, min(100.0, 100.0 - avg_std * STABILITY_SCALING))


def _compute_expression(
    chest_notes: list[float],
    falsetto_notes: list[float],
    overall_min_hz: float,
    overall_max_hz: float,
) -> float:
    """表現力スコア (0-100)"""
    total = len(chest_notes) + len(falsetto_notes)
    if total == 0:
        return 0.0

    score = 30.0  # ベース

    if len(falsetto_notes) > 0 and len(chest_notes) > 0:
        minor = min(len(falsetto_notes), len(chest_notes))
        diversity = minor / total
        score += diversity * 80.0

    all_notes = chest_notes + falsetto_notes
    if len(all_notes) >= 5:
        arr = np.array(all_notes)
        iqr_st = _semitones(float(np.percentile(arr, 25)), float(np.percentile(arr, 75)))
        score += min(30.0, iqr_st * 3.0)

    return min(100.0, score)


# ============================================================
# 2. おすすめ曲
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

    # Supabaseから全曲取得（5,400件程度、メモリ内処理で十分）
    resp = supabase.table("songs").select(
        "id, title, artist_id, lowest_note, highest_note, falsetto_note, source, artists(id, name)"
    ).not_.is_("lowest_note", "null").not_.is_("highest_note", "null").execute()
    rows = resp.data or []

    # 裏声があればそこまで上限を広げる
    effective_max = chest_max_hz
    if falsetto_max_hz and falsetto_max_hz > chest_max_hz:
        effective_max = falsetto_max_hz

    fav_candidates: list[dict] = []
    normal_candidates: list[dict] = []

    for row in rows:
        lo_hz = label_to_hz(row["lowest_note"])
        hi_hz = label_to_hz(row["highest_note"])
        if not lo_hz or not hi_hz or lo_hz > hi_hz:
            continue

        artists_data = row.get("artists") or {}
        artist_name = artists_data.get("name", "")
        artist_id = row["artist_id"]

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
            "id": row["id"],
            "title": row["title"],
            "artist": artist_name,
            "artist_id": artist_id,
            "lowest_note": row["lowest_note"],
            "highest_note": row["highest_note"],
            "match_score": round(min(100.0, score), 1),
        }

        if fav_ids and artist_id in fav_ids:
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
        """アーティスト多様性フィルタ付きで n 曲選ぶ"""
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
    # Supabaseから全曲取得（アーティスト情報つき）
    resp = supabase.table("songs").select(
        "artist_id, lowest_note, highest_note, artists(id, name, song_count)"
    ).not_.is_("lowest_note", "null").not_.is_("highest_note", "null").execute()

    artists: dict[int, dict] = {}
    for row in (resp.data or []):
        artists_data = row.get("artists") or {}
        aid = row["artist_id"]
        lo_hz = label_to_hz(row["lowest_note"])
        hi_hz = label_to_hz(row["highest_note"])
        if not lo_hz or not hi_hz:
            continue
        if aid not in artists:
            artists[aid] = {
                "id": aid,
                "name": artists_data.get("name", ""),
                "song_count": artists_data.get("song_count", 0),
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