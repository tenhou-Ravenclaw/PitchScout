"""
note_converter.py

日本の歌唱コミュニティ標準の音域表記を使用（A4=442Hz基準）

オクターブ対応:
  Octave 1  → lowlow  (例: lowlowC)
  Octave 2  → low     (例: lowC, lowF#)
  Octave 3  → mid1    (例: mid1C, mid1F#)
  Octave 4  → mid2    (例: mid2C, mid2F#)
  Octave 5  → hi      (例: hiC, hiF#)
  Octave 6  → hihi    (例: hihiC)
  Octave 7  → hihihi  (例: hihihiC)
"""

import math

# ========== 対応表 (A4=442Hz基準) ==========
NOTE_TABLE = [
    # Octave 1 - lowlow
    ("C1",   "lowlowC",    32.852),
    ("C#1",  "lowlowC#",   34.805),
    ("D1",   "lowlowD",    36.875),
    ("D#1",  "lowlowD#",   39.068),
    ("E1",   "lowlowE",    41.391),
    ("F1",   "lowlowF",    43.852),
    ("F#1",  "lowlowF#",   46.46),
    ("G1",   "lowlowG",    49.222),
    ("G#1",  "lowlowG#",   52.149),
    ("A1",   "lowA",    55.25),
    ("A#1",  "lowA#",   58.535),
    ("B1",   "lowB",    62.016),
    # Octave 2 - low
    ("C2",   "lowC",       65.704),
    ("C#2",  "lowC#",      69.611),
    ("D2",   "lowD",       73.75),
    ("D#2",  "lowD#",      78.135),
    ("E2",   "lowE",       82.781),
    ("F2",   "lowF",       87.704),
    ("F#2",  "lowF#",      92.919),
    ("G2",   "lowG",       98.444),
    ("G#2",  "lowG#",     104.298),
    ("A2",   "mid1A",      110.5),
    ("A#2",  "mid1A#",     117.071),
    ("B2",   "mid1B",      124.032),
    # Octave 3 - mid1
    ("C3",   "mid1C",     131.407),
    ("C#3",  "mid1C#",    139.221),
    ("D3",   "mid1D",     147.5),
    ("D#3",  "mid1D#",    156.271),
    ("E3",   "mid1E",     165.563),
    ("F3",   "mid1F",     175.408),
    ("F#3",  "mid1F#",    185.838),
    ("G3",   "mid1G",     196.889),
    ("G#3",  "mid1G#",    208.596),
    ("A3",   "mid2A",     221.0),
    ("A#3",  "mid2A#",    234.141),
    ("B3",   "mid2B",     248.064),
    # Octave 4 - mid2
    ("C4",   "mid2C",     262.815),
    ("C#4",  "mid2C#",    278.443),
    ("D4",   "mid2D",     295.0),
    ("D#4",  "mid2D#",    312.541),
    ("E4",   "mid2E",     331.126),
    ("F4",   "mid2F",     350.816),
    ("F#4",  "mid2F#",    371.676),
    ("G4",   "mid2G",     393.777),
    ("G#4",  "mid2G#",    417.192),
    ("A4",   "hiA",     442.0),
    ("A#4",  "hiA#",    468.283),
    ("B4",   "hiB",     496.128),
    # Octave 5 - hi
    ("C5",   "hiC",       525.63),
    ("C#5",  "hiC#",      556.885),
    ("D5",   "hiD",       589.999),
    ("D#5",  "hiD#",      625.082),
    ("E5",   "hiE",       662.252),
    ("F5",   "hiF",       701.631),
    ("F#5",  "hiF#",      743.352),
    ("G5",   "hiG",       787.554),
    ("G#5",  "hiG#",      834.385),
    ("A5",   "hihiA",       884.0),
    ("A#5",  "hihiA#",      936.565),
    ("B5",   "hihiB",       992.256),
    # Octave 6 - hihi
    ("C6",   "hihiC",    1051.259),
    ("C#6",  "hihiC#",   1113.77),
    ("D6",   "hihiD",    1179.998),
    ("D#6",  "hihiD#",   1250.165),
    ("E6",   "hihiE",    1324.503),
    ("F6",   "hihiF",    1403.263),
    ("F#6",  "hihiF#",   1486.705),
    ("G6",   "hihiG",    1575.109),
    ("G#6",  "hihiG#",   1668.77),
    ("A6",   "hihihiA",    1768.0),
    ("A#6",  "hihihiA#",   1873.131),
    ("B6",   "hihihiB",    1984.513),
    # Octave 7 - hihihi
    ("C7",   "hihihiC",  2102.518),
    ("C#7",  "hihihiC#", 2227.54),
    ("D7",   "hihihiD",  2359.997),
    ("D#7",  "hihihiD#", 2500.33),
    ("E7",   "hihihiE",  2649.007),
]

_FREQS = [row[2] for row in NOTE_TABLE]

# label → NOTE_TABLE インデックス（音高順位）のキャッシュ
# NOTE_TABLE は低音から高音順なのでインデックス = 音高順位
_LABEL_TO_RANK: dict[str, int] = {row[1]: i for i, row in enumerate(NOTE_TABLE)}


def label_to_rank(label: str) -> int:
    """
    音階ラベル（例: "mid2C"）を音高順位（0始まり）に変換する。

    NOTE_TABLE の先頭が最低音（lowlowC）であるため、
    インデックスをそのまま音高順位として使用できる。
    未知ラベルは -1 を返す（比較時に最低音扱い）。

    Args:
        label: 音階ラベル文字列（例: "mid2C", "hiA", "lowlowG"）

    Returns:
        NOTE_TABLE 上のインデックス（0 = 最低音）。未知ラベルは -1。
    """
    return _LABEL_TO_RANK.get(label, -1)


def hz_to_label_and_hz(hz: float) -> tuple:
    """
    Hz → (ラベル, 定義Hz) を対応表から返す。
    対数スケールで最近傍を探索（音楽的に正しい距離計算）。
    """
    if hz <= 0:
        return "unknown", 0.0

    log_hz    = math.log2(hz)
    log_freqs = [math.log2(f) for f in _FREQS]
    idx       = min(range(len(log_freqs)), key=lambda i: abs(log_freqs[i] - log_hz))

    _, label, defined_hz = NOTE_TABLE[idx]
    return label, defined_hz


# 後方互換（librosaのnote文字列から変換）
def to_japanese_notation(note: str) -> str:
    for note_name, label, _ in NOTE_TABLE:
        if note_name == note:
            return label
    return note