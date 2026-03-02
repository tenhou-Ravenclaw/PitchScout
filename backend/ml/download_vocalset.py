"""
download_vocalset.py — Zenodo API を使って VocalSet をダウンロード＆学習データを構築

【概要】
  VocalSet（CC BY 4.0、商用利用可）を Zenodo から直接ダウンロードし、
  地声/裏声の学習データセットを bootstrap 自動ラベリングで構築する。

  VocalSet の内容:
    20人のプロ歌手（男性9・女性11）が5母音 × 複数テクニックで歌唱した
    モノラル WAV 録音（10.1時間）。
    テクニック: straight / vibrato / breathy / belt / vocal_fry /
               trillo / trill / inhaled / spoken / messa_di_voce 等。

  VocalSet にはフォルダ名による地声/裏声ラベルがないため、
  音響特徴量（H1-H2, 倍音数, HNR, スペクトル重心）の閾値で
  高確信度フレームだけを自動ラベリングする（bootstrap 方式）。
  曖昧なフレームは捨てる（精度 > 量）。

【使い方】
  # 標準: ダウンロード → データ構築
  python download_vocalset.py

  # データ構築後に自動で学習まで実行
  python download_vocalset.py --train

  # 既にダウンロード済みの場合はスキップ
  python download_vocalset.py --skip-download

  # 手動で展開済みのフォルダを指定
  python download_vocalset.py --skip-download --data-dir /path/to/VocalSet

【ライセンス】
  VocalSet: CC BY 4.0（商用利用可、帰属表示必要）
  出典: Wilkins, J. et al. "VocalSet: A Singing Voice Dataset." ISMIR 2018.
  DOI: 10.5281/zenodo.1442513
"""

import os
import sys
import argparse
import zipfile
import glob
import urllib.request
import urllib.error
import json
import numpy as np

# ml/ から実行時に親ディレクトリ (backend/) の analysis パッケージを見つける
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# ============================================================
# 設定
# ============================================================

# Zenodo レコード ID（VocalSet 1.2）
# https://zenodo.org/records/1442513
ZENODO_RECORD_ID = "1442513"
ZENODO_API_BASE  = "https://zenodo.org/api/records"

DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "vocalset_data")
DATA_DIR     = os.path.join(os.path.dirname(__file__), "training_data")
DATASET_PATH = os.path.join(DATA_DIR, "dataset.npz")

# ============================================================
# bootstrap_labels.py と同じ高確信度閾値
# VocalSet はフォルダ名による地声/裏声ラベルがないため、
# 音響特徴量で「確実に地声」「確実に裏声」なフレームだけを使う
# ============================================================

# 地声の高確信度条件（全て満たす）
CHEST_CRITERIA = {
    "h1_h2_max":    0.0,   # H1-H2 <= 0dB（H2が強い ＝ 豊かな倍音）
    "hcount_min":   6,     # 倍音6本以上
    "hnr_min":      0.60,  # HNR高い（周期的な振動）
    "centroid_r_min": 5.0, # スペクトル重心/f0 >= 5（高次倍音あり）
    "f0_max":       500.0, # 500Hz以上の地声は稀
}

# 裏声の高確信度条件（全て満たす）
# 【設計方針】
#   声楽研究で最も信頼性が高い指標は H1-H2（第1倍音と第2倍音の差）。
#   - 地声: H2 ≥ H1 → H1-H2 ≤ 0 dB
#   - 裏声: H1 >> H2 → H1-H2 ≥ 6 dB が高確信度
#   HNR・centroid_r はプロ歌手では個人差が大きく AND 条件に向かないため除外。
FALSETTO_CRITERIA = {
    "h1_h2_min": 6.0,  # H1-H2 >= 6dB（裏声で最も信頼できる指標）
    "hcount_max": 7,   # 倍音7本以下（プロ裏声でも 4〜7 本程度）
}


def is_confident_chest(feat: np.ndarray) -> bool:
    """高確信度で地声と言えるか"""
    h1_h2, hcount, slope, hnr, cr, f0 = feat
    return (
        h1_h2 <= CHEST_CRITERIA["h1_h2_max"]
        and hcount >= CHEST_CRITERIA["hcount_min"]
        and hnr    >= CHEST_CRITERIA["hnr_min"]
        and cr     >= CHEST_CRITERIA["centroid_r_min"]
        and f0     <  CHEST_CRITERIA["f0_max"]
    )


def is_confident_falsetto(feat: np.ndarray) -> bool:
    """高確信度で裏声と言えるか"""
    h1_h2, hcount, slope, hnr, cr, f0 = feat
    return (
        h1_h2  >= FALSETTO_CRITERIA["h1_h2_min"]
        and hcount <= FALSETTO_CRITERIA["hcount_max"]
        and f0     >= 220.0  # A3(220Hz)以上、男性低裏声をカバー
    )


# ============================================================
# Zenodo API
# ============================================================

def fetch_record_info(record_id: str) -> dict:
    """
    Zenodo API からレコード情報を取得する。

    Args:
        record_id: Zenodo レコード ID

    Returns:
        レコード情報の辞書

    Raises:
        RuntimeError: API 取得失敗時
    """
    url = f"{ZENODO_API_BASE}/{record_id}"
    print(f"[INFO] Zenodo API を確認中: {url}")
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        raise RuntimeError(f"Zenodo API への接続に失敗しました: {e}")


def resolve_download_urls(record_id: str) -> list[dict]:
    """
    Zenodo API からダウンロード可能な ZIP ファイルの URL リストを取得する。

    Args:
        record_id: Zenodo レコード ID

    Returns:
        [{"filename": str, "url": str, "size": int}, ...] の形式のリスト
    """
    info = fetch_record_info(record_id)
    files = info.get("files", [])
    result = []
    for f in files:
        name = f.get("key", "")
        if name.lower().endswith(".zip"):
            # Zenodo API v2 のリンク形式に対応
            links = f.get("links", {})
            url   = links.get("self", f.get("links", {}).get("download", ""))
            if not url:
                # フォールバック: 直接 URL を構築
                url = f"{ZENODO_API_BASE}/{record_id}/files/{name}/content"
            result.append({
                "filename": name,
                "url": url,
                "size": f.get("size", 0),
            })
    return result


def _progress_hook(downloaded: int, total: int) -> None:
    """ダウンロード進捗を表示するコールバック"""
    if total > 0:
        pct  = downloaded / total * 100
        done = int(pct / 2)
        bar  = "█" * done + "░" * (50 - done)
        mb   = downloaded / (1024 ** 2)
        total_mb = total / (1024 ** 2)
        print(f"\r  [{bar}] {pct:5.1f}%  {mb:.0f}/{total_mb:.0f} MB", end="", flush=True)
    else:
        mb = downloaded / (1024 ** 2)
        print(f"\r  {mb:.0f} MB ダウンロード済み...", end="", flush=True)


def download_file(url: str, dest_path: str) -> bool:
    """
    URL からファイルをストリーミングダウンロードする。

    Args:
        url:       ダウンロード URL
        dest_path: 保存先パス

    Returns:
        成功した場合 True
    """
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    print(f"  URL:  {url}")
    print(f"  保存先: {dest_path}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PitchScout-ML/1.0"})
        with urllib.request.urlopen(req, timeout=300) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            chunk = 1024 * 1024  # 1MB ずつ読む
            downloaded = 0
            with open(dest_path, "wb") as f:
                while True:
                    data = resp.read(chunk)
                    if not data:
                        break
                    f.write(data)
                    downloaded += len(data)
                    _progress_hook(downloaded, total)
        print()  # 改行
        return True
    except Exception as e:
        print(f"\n  [ERROR] ダウンロード失敗: {e}")
        return False


def download_vocalset(dest_dir: str) -> list[str]:
    """
    Zenodo から VocalSet の ZIP ファイルをダウンロードする。

    Args:
        dest_dir: ZIP ファイルの保存先ディレクトリ

    Returns:
        ダウンロードした ZIP ファイルのパスリスト
    """
    print("\n=== Zenodo から VocalSet をダウンロード中 ===")
    print(f"  レコード ID: {ZENODO_RECORD_ID}")
    print(f"  保存先: {dest_dir}")
    print(f"  ※ 合計約 8GB あるため時間がかかります（Wi-Fi 推奨）\n")

    try:
        zip_files = resolve_download_urls(ZENODO_RECORD_ID)
    except RuntimeError as e:
        print(f"  [ERROR] {e}")
        return []

    if not zip_files:
        print("  [ERROR] ダウンロード可能な ZIP ファイルが見つかりませんでした。")
        return []

    print(f"  ファイル数: {len(zip_files)} 個")
    for f in zip_files:
        mb = f["size"] / (1024 ** 2)
        print(f"    - {f['filename']} ({mb:.0f} MB)")

    downloaded_paths = []
    for f in zip_files:
        dest_path = os.path.join(dest_dir, f["filename"])

        if os.path.exists(dest_path):
            print(f"\n  [SKIP] 既存ファイルを使用: {f['filename']}")
            downloaded_paths.append(dest_path)
            continue

        print(f"\n  ダウンロード中: {f['filename']}")
        if download_file(f["url"], dest_path):
            downloaded_paths.append(dest_path)
            print(f"  [OK] {f['filename']}")
        else:
            print(f"  [WARN] {f['filename']} のダウンロードに失敗しました。スキップします。")

    return downloaded_paths


def extract_zips(zip_paths: list[str], dest_dir: str) -> str:
    """
    ZIP ファイルを展開する。

    Args:
        zip_paths: ZIP ファイルのパスリスト
        dest_dir:  展開先ディレクトリ

    Returns:
        展開先のルートディレクトリパス
    """
    print(f"\n=== ZIP を展開中 ===")
    os.makedirs(dest_dir, exist_ok=True)

    for zip_path in zip_paths:
        filename = os.path.basename(zip_path)
        print(f"  展開中: {filename} ...", end="", flush=True)
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(dest_dir)
            print(" [OK]")
        except zipfile.BadZipFile:
            print(f"\n  [ERROR] {filename} は壊れた ZIP ファイルです。再ダウンロードしてください。")
        except Exception as e:
            print(f"\n  [ERROR] 展開失敗: {e}")

    return dest_dir


def collect_wav_paths(data_dir: str) -> list[str]:
    """
    指定ディレクトリ以下の WAV ファイルを再帰的に収集する。

    Args:
        data_dir: ルートディレクトリ

    Returns:
        WAV ファイルのパスリスト（重複なし・ソート済み）
    """
    if not os.path.isdir(data_dir):
        print(f"  [ERROR] ディレクトリが見つかりません: {data_dir}")
        return []

    wavs: list[str] = []
    for pattern in ("**/*.wav", "**/*.WAV"):
        wavs.extend(glob.glob(os.path.join(data_dir, pattern), recursive=True))

    paths = sorted(set(wavs))
    print(f"  WAV ファイル数: {len(paths)}")
    return paths


# ============================================================
# 音声処理・特徴量抽出
# ============================================================

def _run_crepe(y: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, int, int]:
    """
    CREPE で f0 と信頼度を推定する。

    Args:
        y:  モノラル波形 (float32)
        sr: サンプルレート

    Returns:
        (f0_np, conf_np, y_16k, sr_crepe, hop_length)
    """
    import librosa
    import torch
    import torchcrepe

    sr_crepe   = 16000
    y_16k      = librosa.resample(y, orig_sr=sr, target_sr=sr_crepe) if sr != sr_crepe else y.copy()
    audio_tensor = torch.tensor(np.copy(y_16k)).unsqueeze(0)
    device     = "cuda" if torch.cuda.is_available() else "cpu"
    hop_length = 80

    for decoder_fn in [
        lambda: torchcrepe.decode.viterbi,
        lambda: torchcrepe.decode.weighted_argmax,
    ]:
        try:
            f0, conf = torchcrepe.predict(
                audio=audio_tensor, sample_rate=sr_crepe,
                hop_length=hop_length, fmin=65, fmax=1400,
                model="tiny", batch_size=2048, device=device,
                return_periodicity=True, decoder=decoder_fn(),
            )
            return (
                f0.squeeze().detach().cpu().numpy(),
                conf.squeeze().detach().cpu().numpy(),
                y_16k, sr_crepe, hop_length,
            )
        except (AttributeError, TypeError):
            continue

    # フォールバック: デコーダ引数なし
    f0, conf = torchcrepe.predict(
        audio=audio_tensor, sample_rate=sr_crepe,
        hop_length=hop_length, fmin=65, fmax=1400,
        model="tiny", batch_size=2048, device=device,
        return_periodicity=True,
    )
    return (
        f0.squeeze().detach().cpu().numpy(),
        conf.squeeze().detach().cpu().numpy(),
        y_16k, sr_crepe, hop_length,
    )


def process_file(wav_path: str) -> tuple[np.ndarray, np.ndarray]:
    """
    1 WAV ファイルから高確信度フレームの特徴量を抽出し、
    bootstrap 自動ラベリングで地声/裏声を判定する。

    VocalSet はフォルダ名による地声/裏声ラベルがないため、
    音響閾値を使った自動ラベリングを行う。
    高確信度フレームのみ採用し、曖昧なフレームは捨てる。

    Args:
        wav_path: 処理する WAV ファイルのパス

    Returns:
        (features, labels) — features: shape=(N, 6), labels: shape=(N,)
    """
    import librosa
    from analysis.features import extract_features

    empty = (np.empty((0, 6), dtype=np.float32), np.empty(0, dtype=np.int32))

    try:
        y, sr = librosa.load(wav_path, sr=None, mono=True)
    except Exception as e:
        print(f"  [WARN] 読み込み失敗 {os.path.basename(wav_path)}: {e}")
        return empty

    if len(y) / sr < 1.0:
        return empty

    y = y.astype(np.float32)
    y = y / (np.max(np.abs(y)) + 1e-8) * 0.95

    try:
        f0_np, conf_np, y_16k, sr_crepe, hop_length = _run_crepe(y, sr)
    except Exception as e:
        print(f"  [WARN] CREPE 失敗 {os.path.basename(wav_path)}: {e}")
        return empty

    valid_mask    = (conf_np >= 0.3) & (f0_np >= 65) & (f0_np <= 1324)
    valid_indices = np.where(valid_mask)[0]

    if len(valid_indices) < 10:
        return empty

    chest_feats:   list[np.ndarray] = []
    falsetto_feats: list[np.ndarray] = []
    frame_len = 2048

    for idx in valid_indices:
        f0_val = float(f0_np[idx])
        center = int(idx) * hop_length
        start  = max(0, center - frame_len // 2)
        end    = min(len(y_16k), center + frame_len // 2)
        frame  = y_16k[start:end]

        if len(frame) < 512:
            continue

        feat = extract_features(frame, sr_crepe, f0_val)
        if feat is None:
            continue

        if is_confident_chest(feat):
            chest_feats.append(feat)
        elif is_confident_falsetto(feat):
            falsetto_feats.append(feat)
        # 曖昧なフレームは捨てる（精度優先）

    n_chest    = len(chest_feats)
    n_falsetto = len(falsetto_feats)

    if n_chest + n_falsetto == 0:
        return empty

    features_list: list[np.ndarray] = []
    labels_list:   list[int]        = []
    if chest_feats:
        features_list.extend(chest_feats)
        labels_list.extend([0] * n_chest)
    if falsetto_feats:
        features_list.extend(falsetto_feats)
        labels_list.extend([1] * n_falsetto)

    return np.array(features_list, dtype=np.float32), np.array(labels_list, dtype=np.int32)


def process_wavs_to_dataset(wav_paths: list[str]) -> bool:
    """
    WAV ファイルリストから bootstrap 自動ラベリングで学習データセットを構築し、
    dataset.npz に保存する（既存データがあれば追記）。

    Args:
        wav_paths: 処理する WAV ファイルのパスリスト

    Returns:
        成功した場合 True
    """
    all_features: list[np.ndarray] = []
    all_labels:   list[np.ndarray] = []

    total = len(wav_paths)
    print(f"\n=== {total} ファイルから特徴量を抽出中 ===")
    print(f"  方式: bootstrap 自動ラベリング（音響閾値による高確信度フレームのみ）\n")

    for i, wav_path in enumerate(wav_paths):
        if i == 0 or (i + 1) % 20 == 0:
            pct = (i + 1) / total * 100
            print(f"  [{i + 1}/{total}] ({pct:.0f}%) {os.path.basename(wav_path)}")

        feat, labels = process_file(wav_path)
        if len(feat) > 0:
            all_features.append(feat)
            all_labels.append(labels)
            n_c = int(np.sum(labels == 0))
            n_f = int(np.sum(labels == 1))
            print(f"    → 地声: {n_c} / 裏声: {n_f}")

    if not all_features:
        print("\n[ERROR] 特徴量を 1 つも抽出できませんでした。")
        print("  音声ファイルに歌声が含まれているか確認してください。")
        return False

    features = np.vstack(all_features)
    labels   = np.concatenate(all_labels)

    # 既存データへ追記
    if os.path.exists(DATASET_PATH):
        existing  = np.load(DATASET_PATH)
        n_existing = len(existing["labels"])
        features  = np.vstack([existing["features"], features])
        labels    = np.concatenate([existing["labels"], labels])
        print(f"\n既存データ（{n_existing} フレーム）に追記しました")

    os.makedirs(DATA_DIR, exist_ok=True)
    np.savez(DATASET_PATH, features=features, labels=labels)

    n_chest    = int(np.sum(labels == 0))
    n_falsetto = int(np.sum(labels == 1))
    print(f"\n=== データセット構築完了 ===")
    print(f"  地声:   {n_chest} フレーム")
    print(f"  裏声:   {n_falsetto} フレーム")
    print(f"  合計:   {len(labels)} フレーム")
    print(f"  保存先: {DATASET_PATH}")
    return True


# ============================================================
# エントリポイント
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="VocalSet を Zenodo からダウンロードし、地声/裏声の学習データを構築する",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 標準: ダウンロード → データ構築
  python download_vocalset.py

  # データ構築後に自動で学習まで実行
  python download_vocalset.py --train

  # ダウンロード済みの場合はスキップ
  python download_vocalset.py --skip-download

  # 手動で展開済みのフォルダを指定
  python download_vocalset.py --skip-download --data-dir /path/to/VocalSet

  # GTSinger データを消してから VocalSet だけで学習
  rm ml/training_data/dataset.npz && python download_vocalset.py --train
        """,
    )
    parser.add_argument(
        "--skip-download", action="store_true",
        help="ダウンロード・展開をスキップし、既存データから特徴量抽出のみ実行",
    )
    parser.add_argument(
        "--data-dir", default=None,
        help=f"WAV ファイルのルートディレクトリ（省略時: {DOWNLOAD_DIR}）",
    )
    parser.add_argument(
        "--train", action="store_true",
        help="データ構築後に自動で train_classifier.py を実行",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("VocalSet 学習データ構築スクリプト")
    print("ライセンス: CC BY 4.0（商用利用可、帰属表示必要）")
    print("出典: Wilkins et al., ISMIR 2018 / DOI: 10.5281/zenodo.1442513")
    print("=" * 60)
    print()

    data_dir = args.data_dir or DOWNLOAD_DIR

    # ─── ダウンロード＆展開 ───────────────────────────────────
    if not args.skip_download:
        zip_dir   = os.path.join(DOWNLOAD_DIR, "zips")
        zip_paths = download_vocalset(zip_dir)

        if not zip_paths:
            print("\n[ERROR] ダウンロードに失敗しました。")
            print("  ネットワーク環境を確認するか、手動でダウンロードして")
            print(f"  --skip-download --data-dir <展開先> を指定してください。")
            print(f"  手動ダウンロード URL:")
            print(f"    https://zenodo.org/records/{ZENODO_RECORD_ID}")
            sys.exit(1)

        extract_zips(zip_paths, data_dir)
    else:
        print(f"[INFO] ダウンロードをスキップします。データディレクトリ: {data_dir}")

    # ─── WAV ファイル収集 ─────────────────────────────────────
    print(f"\n=== WAV ファイルを収集中 ===")
    print(f"  ディレクトリ: {data_dir}")
    wav_paths = collect_wav_paths(data_dir)

    if not wav_paths:
        print("[ERROR] WAV ファイルが見つかりません。")
        print(f"  対象ディレクトリ: {data_dir}")
        print(f"  --data-dir で正しいパスを指定してください。")
        sys.exit(1)

    print(f"\n合計 {len(wav_paths)} ファイルを処理します")

    # ─── 特徴量抽出＆データセット構築 ────────────────────────
    success = process_wavs_to_dataset(wav_paths)
    if not success:
        sys.exit(1)

    # ─── 自動学習 ─────────────────────────────────────────────
    if args.train:
        import subprocess
        print(f"\n=== 学習を開始 ===")
        train_script = os.path.join(os.path.dirname(__file__), "train_classifier.py")
        subprocess.run([sys.executable, train_script], check=True)
    else:
        print(f"\n次のステップ:")
        print(f"  python ml/train_classifier.py")


if __name__ == "__main__":
    main()
