"""
download_training_data.py — GTSingerからML学習データを自動構築

【概要】
  NeurIPS 2024のGTSingerデータセット（CC BY-NC-SA 4.0）から
  地声/裏声の学習データを自動ダウンロード＆構築する。

  GTSingerの構造:
    {Language}/{Singer}/Mixed_Voice_and_Falsetto/{Song}/
      ├── Control_Group/     ← 通常歌唱（＝地声）
      ├── Falsetto_Group/    ← 裏声で歌唱
      └── Mixed_Voice_Group/ ← ミックスボイス

  Control_Group → 地声ラベル、Falsetto_Group → 裏声ラベルとして使用。
  Mixed_Voice_Groupは曖昧なので除外。

【使い方】
  # Step 1: GTSingerの日本語データ（最小セット、約2GB）をダウンロード
  python download_training_data.py

  # Step 2: 学習
  python train_classifier.py

  # 全言語をダウンロード（約54GB、精度は上がるが時間がかかる）
  python download_training_data.py --all

  # 特定言語を指定
  python download_training_data.py --langs Japanese English Korean

【ライセンス】
  GTSinger: CC BY-NC-SA 4.0（非商用、研究目的OK）
  プロトタイプ / 学術利用は問題なし。商用リリース時は確認が必要。
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
REPO_ID = "GTSinger/GTSinger"
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "gtsinger_data")
DATA_DIR = os.path.join(os.path.dirname(__file__), "training_data")
DATASET_PATH = os.path.join(DATA_DIR, "dataset.npz")

# 日本語 + テナー/バス = 男声の地声・裏声が最も豊富
DEFAULT_LANGS = ["Japanese"]

ALL_LANGS = [
    "Japanese", "English", "Chinese", "Korean",
    "French", "German", "Italian", "Spanish", "Russian",
]

# GTSingerのフォルダ名 → ラベル
FOLDER_LABEL_MAP = {
    "Control_Group": "chest",       # 通常歌唱 = 地声
    "Falsetto_Group": "falsetto",   # 裏声
    # Mixed_Voice_Group は除外（曖昧）
}


def check_huggingface_cli():
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


def download_language(lang: str):
    """
    HuggingFace CLIで特定言語のMixed_Voice_and_Falsettoフォルダをダウンロード。
    WAVファイルのみ。
    """
    print(f"\n=== {lang} をダウンロード中... ===")

    # huggingface-cli download で特定パスだけ取得
    cmd = [
        "huggingface-cli", "download",
        REPO_ID,
        "--repo-type", "dataset",
        "--include", f"{lang}/*/Mixed_Voice_and_Falsetto/**/*.wav",
        "--local-dir", DOWNLOAD_DIR,
    ]

    print(f"  コマンド: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=3600,
        )
        if result.returncode != 0:
            print(f"  [WARN] ダウンロードに問題: {result.stderr[:500]}")
            # フォールバック: pythonでダウンロード
            return download_language_python(lang)
        else:
            print(f"  [OK] ダウンロード完了")
            return True
    except subprocess.TimeoutExpired:
        print(f"  [ERROR] タイムアウト（1時間超過）")
        return False
    except FileNotFoundError:
        return download_language_python(lang)


def download_language_python(lang: str):
    """Pythonのhuggingface_hubでダウンロード（CLIが使えない場合のフォールバック）"""
    print(f"  [INFO] Python APIでダウンロード中...")
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(
            repo_id=REPO_ID,
            repo_type="dataset",
            allow_patterns=[f"{lang}/*/Mixed_Voice_and_Falsetto/**/*.wav"],
            local_dir=DOWNLOAD_DIR,
        )
        print(f"  [OK] ダウンロード完了")
        return True
    except Exception as e:
        print(f"  [ERROR] ダウンロード失敗: {e}")
        return False


def collect_labeled_wavs(langs: list[str]) -> dict[str, list[str]]:
    """
    ダウンロード済みWAVファイルをラベルごとに収集。

    Returns:
        {"chest": [wav_path, ...], "falsetto": [wav_path, ...]}
    """
    labeled: dict[str, list[str]] = {"chest": [], "falsetto": []}

    for lang in langs:
        lang_dir = os.path.join(DOWNLOAD_DIR, lang)
        if not os.path.isdir(lang_dir):
            print(f"  [SKIP] {lang} ディレクトリなし")
            continue

        # 再帰的にWAVを探す
        for folder_name, label in FOLDER_LABEL_MAP.items():
            pattern = os.path.join(lang_dir, "**", folder_name, "*.wav")
            wavs = glob.glob(pattern, recursive=True)
            labeled[label].extend(wavs)
            if wavs:
                print(f"  {lang}/{folder_name}: {len(wavs)} WAVファイル → {label}")

    return labeled


def process_wavs_to_dataset(labeled_wavs: dict[str, list[str]]):
    """
    WAVファイルから特徴量を抽出。
    GTSingerはフォルダ名でラベル済みなので、bootstrap_labelsの
    高確信度フィルタは使わず、全有効フレームの特徴量を抽出する。
    """
    import librosa
    import torch
    import torchcrepe
    from analysis.features import extract_features

    all_features = []
    all_labels = []

    for label_name, wav_paths in labeled_wavs.items():
        if not wav_paths:
            continue

        label_int = 0 if label_name == "chest" else 1
        print(f"\n--- {label_name} ({len(wav_paths)} ファイル) を処理中 ---")

        for i, wav_path in enumerate(wav_paths):
            if (i + 1) % 10 == 0:
                print(f"  進捗: {i + 1}/{len(wav_paths)}")

            try:
                feats = _extract_all_features(wav_path)
                if feats is not None and len(feats) > 0:
                    labels = np.full(len(feats), label_int, dtype=np.int32)
                    all_features.append(feats)
                    all_labels.append(labels)
            except Exception as e:
                print(f"  [WARN] {wav_path}: {e}")
                continue

    if not all_features:
        print("\n[ERROR] 特徴量を1つも抽出できませんでした。")
        return False

    features = np.vstack(all_features)
    labels = np.concatenate(all_labels)

    # 既存データに追加
    if os.path.exists(DATASET_PATH):
        existing = np.load(DATASET_PATH)
        features = np.vstack([existing["features"], features])
        labels = np.concatenate([existing["labels"], labels])
        print(f"\n既存データに追加")

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


def _extract_all_features(wav_path: str) -> np.ndarray | None:
    """
    WAVファイルから全有効フレームの特徴量を抽出（高確信度フィルタなし）。
    GTSingerのラベル済みデータ用。
    """
    import librosa
    import torch
    import torchcrepe
    from analysis.features import extract_features

    y, sr = librosa.load(wav_path, sr=None, mono=True)
    if len(y) / sr < 1.0:
        return None

    y = y.astype(np.float32)
    y = y / (np.max(np.abs(y)) + 1e-8) * 0.95

    # CREPE
    sr_crepe = 16000
    y_16k = librosa.resample(y, orig_sr=sr, target_sr=sr_crepe) if sr != sr_crepe else y.copy()
    audio_tensor = torch.tensor(np.copy(y_16k)).unsqueeze(0)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    hop_length = 80

    try:
        f0, conf = torchcrepe.predict(
            audio=audio_tensor, sample_rate=sr_crepe,
            hop_length=hop_length, fmin=65, fmax=1400,
            model='tiny', batch_size=2048, device=device,
            return_periodicity=True,
        )
        f0_np = f0.squeeze().detach().cpu().numpy()
        conf_np = conf.squeeze().detach().cpu().numpy()
    except Exception as e:
        print(f"    CREPE失敗: {e}")
        return None

    valid_mask = (conf_np >= 0.3) & (f0_np >= 65) & (f0_np <= 1324)
    valid_indices = np.where(valid_mask)[0]

    if len(valid_indices) < 5:
        return None

    frame_len = 2048
    feats = []
    for idx in valid_indices:
        f0_val = f0_np[idx]
        center = int(idx) * hop_length
        start = max(0, center - frame_len // 2)
        end = min(len(y_16k), center + frame_len // 2)
        frame = y_16k[start:end]

        if len(frame) < 512:
            continue

        feat = extract_features(frame, sr_crepe, f0_val)
        if feat is not None:
            feats.append(feat)

    if not feats:
        return None

    return np.array(feats, dtype=np.float32)


def main():
    parser = argparse.ArgumentParser(
        description="GTSingerデータセットから地声/裏声の学習データを構築"
    )
    parser.add_argument(
        "--langs", nargs="+", default=None,
        help=f"ダウンロードする言語 (例: Japanese English)",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="全言語をダウンロード（約54GB）",
    )
    parser.add_argument(
        "--skip-download", action="store_true",
        help="ダウンロード済みデータを使って特徴量抽出のみ実行",
    )
    parser.add_argument(
        "--train", action="store_true",
        help="データ構築後に自動でtrain_classifier.pyを実行",
    )
    args = parser.parse_args()

    # 言語選択
    if args.all:
        langs = ALL_LANGS
    elif args.langs:
        langs = args.langs
    else:
        langs = DEFAULT_LANGS

    print(f"対象言語: {', '.join(langs)}")
    print(f"ライセンス: CC BY-NC-SA 4.0（非商用・研究目的OK）")
    print()

    # ダウンロード
    if not args.skip_download:
        # huggingface-cli確認
        if not check_huggingface_cli():
            install_huggingface_hub()

        for lang in langs:
            download_language(lang)

    # WAVファイル収集
    print(f"\n=== WAVファイルを収集中 ===")
    labeled_wavs = collect_labeled_wavs(langs)

    total = sum(len(v) for v in labeled_wavs.values())
    if total == 0:
        print("[ERROR] WAVファイルが見つかりません。")
        print("  ダウンロードに失敗したか、まだ実行されていません。")
        print(f"  期待するパス: {DOWNLOAD_DIR}/{{言語}}/*/Mixed_Voice_and_Falsetto/")
        sys.exit(1)

    print(f"\n合計: 地声={len(labeled_wavs['chest'])} / 裏声={len(labeled_wavs['falsetto'])} ファイル")

    # 特徴量抽出＆データセット構築
    success = process_wavs_to_dataset(labeled_wavs)

    if success and args.train:
        print(f"\n=== 学習を開始 ===")
        subprocess.run([sys.executable, "train_classifier.py"], check=True)


if __name__ == "__main__":
    main()