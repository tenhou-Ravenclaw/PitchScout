"""
download_singStyle111.py — SingStyle111からML学習データを自動構築

【概要】
  SingStyle111データセット（CC BY 4.0、商用利用可）から
  地声/裏声の学習データを自動ダウンロード＆構築する。

  GTSingerとの違い:
    GTSinger → Control_Group/Falsetto_Group のフォルダ名でラベル済み
    SingStyle111 → スタイルベースフォルダ（pop/folk/opera等）、ラベルなし

  そのため、bootstrap_labels.py と同じ音響的自動ラベリングを使う:
    音響特徴量（H1-H2, 倍音数, HNR, スペクトル重心）の閾値で
    「確実に地声」「確実に裏声」なフレームだけをデータとして使用。
    曖昧なフレームは捨てる（精度 > 量）。

【使い方】
  # Step 1: ダウンロード＆学習データ構築
  python download_singStyle111.py

  # Step 2: 学習
  python train_classifier.py

  # ダウンロードせず既存ディレクトリからデータ構築のみ
  python download_singStyle111.py --skip-download

  # 手動でダウンロードした音声フォルダを指定
  python download_singStyle111.py --skip-download --data-dir /path/to/wavs

  # データ構築後に自動で学習まで実行
  python download_singStyle111.py --train

【ライセンス】
  SingStyle111: CC BY 4.0（商用利用可、帰属表示必要）
  GTSinger（CC BY-NC-SA 4.0）と異なり商用利用が可能。

  帰属表示例:
    "This product uses the SingStyle111 dataset (CC BY 4.0)."
"""

import os
import sys
import argparse
import subprocess
import glob
import numpy as np

# ml/ から実行時に親ディレクトリ (backend/) の analysis パッケージを見つける
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# ============================================================
# 設定
# ============================================================

# HuggingFace データセットID
# ※ 正確なIDは https://huggingface.co/datasets で "SingStyle111" を検索して確認してください
REPO_ID = "SingStyle111/SingStyle111"

DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "singstyle111_data")
DATA_DIR = os.path.join(os.path.dirname(__file__), "training_data")
DATASET_PATH = os.path.join(DATA_DIR, "dataset.npz")

# ============================================================
# bootstrap_labels.py と同じ高確信度閾値
# SingStyle111はラベルなしデータなので音響特徴で自動判定する
# ============================================================

# 地声の高確信度条件（全て満たす）
CHEST_CRITERIA = {
    "h1_h2_max": 0.0,      # H1-H2 <= 0dB（H2が強い ＝ 豊かな倍音）
    "hcount_min": 6,        # 倍音6本以上
    "hnr_min": 0.60,        # HNR高い（周期的な振動）
    "centroid_r_min": 5.0,  # スペクトル重心/f0 >= 5（高次倍音あり）
    "f0_max": 500.0,        # 500Hz以上の地声は稀
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
        and hnr >= CHEST_CRITERIA["hnr_min"]
        and cr >= CHEST_CRITERIA["centroid_r_min"]
        and f0 < CHEST_CRITERIA["f0_max"]
    )


def is_confident_falsetto(feat: np.ndarray) -> bool:
    """高確信度で裏声と言えるか"""
    h1_h2, hcount, slope, hnr, cr, f0 = feat
    return (
        h1_h2 >= FALSETTO_CRITERIA["h1_h2_min"]
        and hcount <= FALSETTO_CRITERIA["hcount_max"]
        and f0 >= 220.0  # A3(220Hz)以上、男性低裏声をカバー
    )


def check_huggingface_cli() -> bool:
    """huggingface-cliが使えるか確認"""
    try:
        result = subprocess.run(
            ["huggingface-cli", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def install_huggingface_hub():
    """huggingface_hubをインストール"""
    print("[INFO] huggingface-cli をインストール中...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "huggingface_hub[cli]"],
        check=True,
    )


def download_dataset(repo_id: str, local_dir: str) -> bool:
    """
    HuggingFace CLIでSingStyle111の全WAVファイルをダウンロード。

    Args:
        repo_id:   HuggingFace データセットID
        local_dir: ローカル保存先ディレクトリ
    """
    print(f"\n=== SingStyle111 をダウンロード中... ===")
    print(f"  リポジトリ: {repo_id}")
    print(f"  保存先:     {local_dir}")
    print(f"  ※ 初回ダウンロードは数GBあるため時間がかかります")

    cmd = [
        "huggingface-cli", "download",
        repo_id,
        "--repo-type", "dataset",
        "--include", "**/*.wav",
        "--local-dir", local_dir,
    ]

    print(f"\n  コマンド: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=7200,  # 2時間
        )
        if result.returncode != 0:
            print(f"  [WARN] ダウンロードに問題: {result.stderr[:500]}")
            return _download_python(repo_id, local_dir)
        print(f"  [OK] ダウンロード完了")
        return True
    except subprocess.TimeoutExpired:
        print(f"  [ERROR] タイムアウト（2時間超過）")
        return False
    except FileNotFoundError:
        return _download_python(repo_id, local_dir)


def _download_python(repo_id: str, local_dir: str) -> bool:
    """Pythonのhuggingface_hubでダウンロード（CLIが使えない場合のフォールバック）"""
    print(f"  [INFO] Python APIでダウンロード中...")
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(
            repo_id=repo_id,
            repo_type="dataset",
            allow_patterns=["**/*.wav"],
            local_dir=local_dir,
        )
        print(f"  [OK] ダウンロード完了")
        return True
    except Exception as e:
        print(f"  [ERROR] ダウンロード失敗: {e}")
        print(f"\n  手動でダウンロードする場合:")
        print(f"    huggingface-cli download {repo_id} --repo-type dataset --local-dir {local_dir}")
        print(f"  または HuggingFace の当該ページからZIPをダウンロードして:")
        print(f"    python download_singStyle111.py --skip-download --data-dir <解凍先>")
        return False


def collect_wav_paths(data_dir: str) -> list[str]:
    """
    指定ディレクトリ以下のWAVファイルを再帰的に収集。

    Args:
        data_dir: 音声ファイルが格納されたルートディレクトリ
    """
    if not os.path.isdir(data_dir):
        print(f"  [ERROR] ディレクトリが見つかりません: {data_dir}")
        return []

    # .wav / .WAV 両方を対象
    wavs: list[str] = []
    for pattern in ("**/*.wav", "**/*.WAV"):
        wavs.extend(glob.glob(os.path.join(data_dir, pattern), recursive=True))

    paths = sorted(set(wavs))
    print(f"  WAVファイル数: {len(paths)}")
    return paths


def _run_crepe(
    y: np.ndarray, sr: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int, int]:
    """
    CREPEでf0と信頼度を推定する。

    Args:
        y:  モノラル波形 (float32)
        sr: サンプルレート

    Returns:
        (f0_np, conf_np, y_16k, sr_crepe, hop_length)
    """
    import librosa
    import torch
    import torchcrepe

    sr_crepe = 16000
    y_16k = librosa.resample(y, orig_sr=sr, target_sr=sr_crepe) if sr != sr_crepe else y.copy()
    audio_tensor = torch.tensor(np.copy(y_16k)).unsqueeze(0)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    hop_length = 80

    # Viterbi デコーダを優先（より安定したf0推定）
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
    1WAVファイルから高確信度フレームの特徴量を抽出し、
    bootstrap自動ラベリングで地声/裏声を判定する。

    SingStyle111はフォルダ名によるラベルがないため、
    bootstrap_labels.py と同じ音響閾値を使った自動ラベリングを行う。
    高確信度の地声/裏声フレームのみ採用し、曖昧なフレームは捨てる。

    Args:
        wav_path: 処理するWAVファイルのパス

    Returns:
        features: shape=(N, 6) の特徴量配列（N=抽出フレーム数）
        labels:   shape=(N,)   0=地声, 1=裏声
    """
    import librosa
    from analysis.features import extract_features

    empty = (np.empty((0, 6), dtype=np.float32), np.empty(0, dtype=np.int32))

    try:
        y, sr = librosa.load(wav_path, sr=None, mono=True)
    except Exception as e:
        print(f"  [WARN] 読み込み失敗 {os.path.basename(wav_path)}: {e}")
        return empty

    duration = len(y) / sr
    if duration < 1.0:
        return empty

    y = y.astype(np.float32)
    y = y / (np.max(np.abs(y)) + 1e-8) * 0.95

    try:
        f0_np, conf_np, y_16k, sr_crepe, hop_length = _run_crepe(y, sr)
    except Exception as e:
        print(f"  [WARN] CREPE失敗 {os.path.basename(wav_path)}: {e}")
        return empty

    valid_mask = (conf_np >= 0.3) & (f0_np >= 65) & (f0_np <= 1324)
    valid_indices = np.where(valid_mask)[0]

    if len(valid_indices) < 10:
        return empty

    chest_feats: list[np.ndarray] = []
    falsetto_feats: list[np.ndarray] = []
    frame_len = 2048

    for idx in valid_indices:
        f0_val = float(f0_np[idx])
        center = int(idx) * hop_length
        start = max(0, center - frame_len // 2)
        end = min(len(y_16k), center + frame_len // 2)
        frame = y_16k[start:end]

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

    n_chest = len(chest_feats)
    n_falsetto = len(falsetto_feats)

    if n_chest + n_falsetto == 0:
        return empty

    features_list: list[np.ndarray] = []
    labels_list: list[int] = []
    if chest_feats:
        features_list.extend(chest_feats)
        labels_list.extend([0] * n_chest)
    if falsetto_feats:
        features_list.extend(falsetto_feats)
        labels_list.extend([1] * n_falsetto)

    return np.array(features_list, dtype=np.float32), np.array(labels_list, dtype=np.int32)


def process_wavs_to_dataset(wav_paths: list[str]) -> bool:
    """
    WAVファイルリストからbootstrap自動ラベリングで学習データセットを構築し、
    dataset.npz に保存（既存データがあれば追記）する。

    Args:
        wav_paths: 処理するWAVファイルのパスリスト

    Returns:
        成功した場合 True
    """
    all_features: list[np.ndarray] = []
    all_labels: list[np.ndarray] = []

    total = len(wav_paths)
    print(f"\n=== {total} ファイルから特徴量を抽出中 ===")
    print(f"  方式: bootstrap自動ラベリング（音響閾値による高確信度フレームのみ）")

    for i, wav_path in enumerate(wav_paths):
        # 進捗を20ファイルごとに表示
        if i == 0 or (i + 1) % 20 == 0:
            pct = (i + 1) / total * 100
            print(f"\n  [{i + 1}/{total}] ({pct:.0f}%) {os.path.basename(wav_path)}")

        feat, labels = process_file(wav_path)
        if len(feat) > 0:
            all_features.append(feat)
            all_labels.append(labels)
            n_c = int(np.sum(labels == 0))
            n_f = int(np.sum(labels == 1))
            print(f"    → 地声: {n_c} / 裏声: {n_f}")

    if not all_features:
        print("\n[ERROR] 特徴量を1つも抽出できませんでした。")
        print("  音声ファイルに歌声が含まれているか確認してください。")
        return False

    features = np.vstack(all_features)
    labels = np.concatenate(all_labels)

    # 既存データへ追記（GTSingerデータとの合算に対応）
    if os.path.exists(DATASET_PATH):
        existing = np.load(DATASET_PATH)
        n_existing = len(existing["labels"])
        features = np.vstack([existing["features"], features])
        labels = np.concatenate([existing["labels"], labels])
        print(f"\n既存データ（{n_existing} フレーム）に追記しました")

    os.makedirs(DATA_DIR, exist_ok=True)
    np.savez(DATASET_PATH, features=features, labels=labels)

    n_chest = int(np.sum(labels == 0))
    n_falsetto = int(np.sum(labels == 1))
    print(f"\n=== データセット構築完了 ===")
    print(f"  地声:   {n_chest} フレーム")
    print(f"  裏声:   {n_falsetto} フレーム")
    print(f"  合計:   {len(labels)} フレーム")
    print(f"  保存先: {DATASET_PATH}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="SingStyle111データセットから地声/裏声の学習データを構築（bootstrap自動ラベリング）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 標準: ダウンロード＆データ構築
  python download_singStyle111.py

  # 手動でダウンロードした音声フォルダを指定
  python download_singStyle111.py --skip-download --data-dir /path/to/singstyle111/

  # データ構築後に自動で学習まで実行
  python download_singStyle111.py --train

  # カスタムHuggingFaceリポジトリIDを指定
  python download_singStyle111.py --repo-id your_org/your_dataset
        """,
    )
    parser.add_argument(
        "--skip-download", action="store_true",
        help="ダウンロードをスキップし、既存データから特徴量抽出のみ実行",
    )
    parser.add_argument(
        "--data-dir", default=None,
        help=f"音声ファイルのルートディレクトリ（省略時: {DOWNLOAD_DIR}）",
    )
    parser.add_argument(
        "--repo-id", default=REPO_ID,
        help=f"HuggingFace データセットID（省略時: {REPO_ID}）",
    )
    parser.add_argument(
        "--train", action="store_true",
        help="データ構築後に自動でtrain_classifier.pyを実行",
    )
    args = parser.parse_args()

    data_dir = args.data_dir if args.data_dir else DOWNLOAD_DIR

    print("=" * 60)
    print("SingStyle111 学習データ構築スクリプト")
    print("ライセンス: CC BY 4.0（商用利用可、帰属表示必要）")
    print("=" * 60)
    print()
    print("注意: SingStyle111はフォルダ名による地声/裏声ラベルがありません。")
    print("      音響特徴量（H1-H2, 倍音数, HNR等）による自動ラベリングを使用します。")
    print()

    # ─── ダウンロード ───
    if not args.skip_download:
        if not check_huggingface_cli():
            install_huggingface_hub()

        success = download_dataset(args.repo_id, data_dir)
        if not success:
            print("\n[ERROR] ダウンロードに失敗しました。")
            print("  --skip-download と --data-dir で手動ダウンロード済みデータを指定するか、")
            print(f"  HuggingFace（{args.repo_id}）から手動でダウンロードしてください。")
            sys.exit(1)

    # ─── WAVファイル収集 ───
    print(f"\n=== WAVファイルを収集中 ===")
    print(f"  ディレクトリ: {data_dir}")
    wav_paths = collect_wav_paths(data_dir)

    if not wav_paths:
        print("[ERROR] WAVファイルが見つかりません。")
        print(f"  対象ディレクトリ: {data_dir}")
        print(f"  --data-dir で正しいパスを指定してください。")
        sys.exit(1)

    print(f"\n合計 {len(wav_paths)} ファイルを処理します")

    # ─── 特徴量抽出＆データセット構築 ───
    success = process_wavs_to_dataset(wav_paths)

    if not success:
        sys.exit(1)

    # ─── 自動学習 ───
    if args.train:
        print(f"\n=== 学習を開始 ===")
        train_script = os.path.join(os.path.dirname(__file__), "train_classifier.py")
        subprocess.run([sys.executable, train_script], check=True)
    else:
        print(f"\n次のステップ:")
        print(f"  python train_classifier.py")


if __name__ == "__main__":
    main()
