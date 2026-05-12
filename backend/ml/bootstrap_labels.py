"""
bootstrap_labels.py — 自動ラベリング（手動不要）

【コンセプト】
  ルールベース分類器の「高確信度」予測のみを学習データとして使う。
  地声/裏声の判定が曖昧なフレームは捨て、明確なフレームだけで学習する。

  これにより:
  - 手動ラベリング不要
  - 歌った音声ファイルを投げるだけでOK
  - ルールベースが苦手な「曖昧ゾーン」をMLが補完

使い方:
  # 音声ファイルを指定（複数可、地声裏声混在OK）
  python bootstrap_labels.py singing1.wav singing2.wav singing3.wav

  # カラオケ音源（MelBandRoformers 分離済み）も使える
  python bootstrap_labels.py vocals1.wav vocals2.wav

  # フォルダ内の全WAVを処理
  python bootstrap_labels.py audio_folder/

  # 確認
  python labeler.py stats

  # 学習
  python train_classifier.py
"""

import os
import sys
import glob
import numpy as np
import librosa
import torch
import torchcrepe

# ml/ から実行時に親ディレクトリ (backend/) の analysis パッケージを見つける
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from analysis.features import extract_features

DATA_DIR = os.path.join(os.path.dirname(__file__), "training_data")
DATASET_PATH = os.path.join(DATA_DIR, "dataset.npz")

# ============================================================
# 高確信度の閾値
# これらの条件を「全て」満たすフレームだけをラベル付きデータとして使う
# ============================================================

# 地声の高確信度条件（全て満たす）
CHEST_CRITERIA = {
    "h1_h2_max": 0.0,        # H1-H2 <= 0dB（H2が強い）
    "hcount_min": 6,          # 倍音6本以上
    "hnr_min": 0.60,          # HNR高い（周期的）
    "centroid_r_min": 5.0,    # スペクトル重心/f0 >= 5（高次倍音あり）
}

# 裏声の高確信度条件（全て満たす）
# 【設計方針】
#   声楽研究で最も信頼性が高い指標は H1-H2（第1倍音と第2倍音の差）。
#   - 地声: H2 ≥ H1 → H1-H2 ≤ 0 dB
#   - 裏声: H1 >> H2 → H1-H2 ≥ 6 dB が高確信度
#   HNR・centroid_r はプロ歌手では個人差が大きく AND 条件に向かないため除外。
FALSETTO_CRITERIA = {
    "h1_h2_min": 6.0,   # H1-H2 >= 6dB（裏声で最も信頼できる指標）
    "hcount_max": 7,     # 倍音7本以下（プロ裏声でも 4〜7 本程度）
}


def is_confident_chest(feat: np.ndarray) -> bool:
    """高確信度で地声と言えるか"""
    h1_h2, hcount, slope, hnr, cr, f0 = feat
    return (
        h1_h2 <= CHEST_CRITERIA["h1_h2_max"]
        and hcount >= CHEST_CRITERIA["hcount_min"]
        and hnr >= CHEST_CRITERIA["hnr_min"]
        and cr >= CHEST_CRITERIA["centroid_r_min"]
        and f0 < 500  # 500Hz以上の地声は稀
    )


def is_confident_falsetto(feat: np.ndarray) -> bool:
    """高確信度で裏声と言えるか"""
    h1_h2, hcount, slope, hnr, cr, f0 = feat
    return (
        h1_h2 >= FALSETTO_CRITERIA["h1_h2_min"]
        and hcount <= FALSETTO_CRITERIA["hcount_max"]
        and f0 >= 220  # A3(220Hz)以上、男性低裏声をカバー（元は 270Hz で男声が除外されていた）
    )


def _run_crepe(y: np.ndarray, sr: int):
    """CREPE実行"""
    sr_crepe = 16000
    y_16k = librosa.resample(y, orig_sr=sr, target_sr=sr_crepe) if sr != sr_crepe else y.copy()
    audio_tensor = torch.tensor(np.copy(y_16k)).unsqueeze(0)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    hop_length = 80

    for decoder_fn in [
        lambda: torchcrepe.decode.viterbi,
        lambda: torchcrepe.decode.weighted_argmax,
    ]:
        try:
            f0, conf = torchcrepe.predict(
                audio=audio_tensor, sample_rate=sr_crepe,
                hop_length=hop_length, fmin=65, fmax=1400,
                model='tiny', batch_size=2048, device=device,
                return_periodicity=True, decoder=decoder_fn(),
            )
            return (
                f0.squeeze().detach().cpu().numpy(),
                conf.squeeze().detach().cpu().numpy(),
                y_16k, sr_crepe, hop_length,
            )
        except (AttributeError, TypeError):
            continue

    f0, conf = torchcrepe.predict(
        audio=audio_tensor, sample_rate=sr_crepe,
        hop_length=hop_length, fmin=65, fmax=1400,
        model='tiny', batch_size=2048, device=device,
        return_periodicity=True,
    )
    return (
        f0.squeeze().detach().cpu().numpy(),
        conf.squeeze().detach().cpu().numpy(),
        y_16k, sr_crepe, hop_length,
    )


def process_file(wav_path: str) -> tuple[np.ndarray, np.ndarray]:
    """
    1ファイルから高確信度フレームを抽出。

    Returns:
        features: shape=(N, 6)
        labels:   shape=(N,)  0=chest, 1=falsetto
    """
    print(f"\n[INFO] 処理中: {wav_path}")
    y, sr = librosa.load(wav_path, sr=None, mono=True)
    duration = len(y) / sr
    print(f"  長さ: {duration:.1f}s")

    if duration < 1.0:
        print(f"  [SKIP] 短すぎ")
        return np.empty((0, 6), dtype=np.float32), np.empty(0, dtype=np.int32)

    y = y.astype(np.float32)
    y = y / (np.max(np.abs(y)) + 1e-8) * 0.95

    f0_np, conf_np, y_16k, sr_crepe, hop_length = _run_crepe(y, sr)

    valid_mask = (conf_np >= 0.3) & (f0_np >= 65) & (f0_np <= 1324)
    valid_indices = np.where(valid_mask)[0]
    print(f"  有効フレーム: {len(valid_indices)}")

    if len(valid_indices) < 10:
        print(f"  [SKIP] 有効フレーム不足")
        return np.empty((0, 6), dtype=np.float32), np.empty(0, dtype=np.int32)

    chest_feats = []
    falsetto_feats = []
    frame_len = 2048

    for idx in valid_indices:
        f0 = f0_np[idx]
        center = int(idx) * hop_length
        start = max(0, center - frame_len // 2)
        end = min(len(y_16k), center + frame_len // 2)
        frame = y_16k[start:end]

        if len(frame) < 512:
            continue

        feat = extract_features(frame, sr_crepe, f0)
        if feat is None:
            continue

        if is_confident_chest(feat):
            chest_feats.append(feat)
        elif is_confident_falsetto(feat):
            falsetto_feats.append(feat)
        # それ以外（曖昧）は捨てる

    n_chest = len(chest_feats)
    n_falsetto = len(falsetto_feats)
    n_skipped = len(valid_indices) - n_chest - n_falsetto
    print(f"  → 地声: {n_chest} / 裏声: {n_falsetto} / 曖昧(除外): {n_skipped}")

    if n_chest + n_falsetto == 0:
        return np.empty((0, 6), dtype=np.float32), np.empty(0, dtype=np.int32)

    features = []
    labels = []
    if chest_feats:
        features.extend(chest_feats)
        labels.extend([0] * n_chest)
    if falsetto_feats:
        features.extend(falsetto_feats)
        labels.extend([1] * n_falsetto)

    return np.array(features, dtype=np.float32), np.array(labels, dtype=np.int32)


def collect_wav_paths(args: list[str]) -> list[str]:
    """引数からWAVファイルパスを収集"""
    paths = []
    for arg in args:
        if os.path.isdir(arg):
            # フォルダ内のWAVを再帰的に収集
            for ext in ['*.wav', '*.WAV', '*.mp3', '*.MP3', '*.flac', '*.FLAC', '*.m4a', '*.M4A', '*.aac', '*.AAC', '*.ogg', '*.OGG']:
                paths.extend(glob.glob(os.path.join(arg, '**', ext), recursive=True))
        elif os.path.isfile(arg):
            paths.append(arg)
        else:
            print(f"[WARN] 見つかりません: {arg}")
    return sorted(set(paths))


def main():
    if len(sys.argv) < 2:
        print("使い方:")
        print("  python bootstrap_labels.py singing1.wav singing2.wav ...")
        print("  python bootstrap_labels.py audio_folder/")
        print()
        print("音声ファイルから高確信度フレームを自動抽出してラベル付きデータを生成します。")
        print("手動ラベリングは不要です。")
        sys.exit(1)

    wav_paths = collect_wav_paths(sys.argv[1:])
    if not wav_paths:
        print("[ERROR] 音声ファイルが見つかりません")
        sys.exit(1)

    print(f"=== {len(wav_paths)} ファイルを処理します ===")

    all_features = []
    all_labels = []

    for path in wav_paths:
        feat, labels = process_file(path)
        if len(feat) > 0:
            all_features.append(feat)
            all_labels.append(labels)

    if not all_features:
        print("\n[ERROR] 有効なデータが1つも抽出できませんでした。")
        print("  音声に歌声が含まれているか確認してください。")
        sys.exit(1)

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
    print(f"\n=== 完了 ===")
    print(f"  地声:   {n_chest} フレーム")
    print(f"  裏声:   {n_falsetto} フレーム")
    print(f"  合計:   {len(labels)} フレーム")
    print(f"  保存先: {DATASET_PATH}")
    print(f"\n次のステップ:")
    print(f"  python train_classifier.py")


if __name__ == "__main__":
    main()