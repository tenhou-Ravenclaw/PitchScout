"""
labeler.py — 地声/裏声ラベリングツール

使い方:
  1. 全部地声の音声を登録:
     python labeler.py add chest voice_chest1.wav
     python labeler.py add chest voice_chest2.wav

  2. 全部裏声の音声を登録:
     python labeler.py add falsetto voice_falsetto1.wav

  3. 混在音声を時間範囲でラベル付け:
     python labeler.py add chest mixed.wav --start 0.0 --end 3.5
     python labeler.py add falsetto mixed.wav --start 3.5 --end 7.0

  4. 現在のデータセット確認:
     python labeler.py stats

  5. データセットをクリア:
     python labeler.py clear

データは training_data/ フォルダに .npz で保存される。
"""

import os
import sys
import argparse
import numpy as np
import librosa
import torch
import torchcrepe

# ml/ から実行時に親ディレクトリ (backend/) の analysis パッケージを見つける
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from analysis.features import extract_features, FEATURE_NAMES

DATA_DIR = os.path.join(os.path.dirname(__file__), "training_data")
DATASET_PATH = os.path.join(DATA_DIR, "dataset.npz")


def _run_crepe_simple(y: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray]:
    """CREPE でf0推定（ラベリング用、シンプル版）"""
    sr_crepe = 16000
    y_16k = librosa.resample(y, orig_sr=sr, target_sr=sr_crepe) if sr != sr_crepe else y.copy()

    audio_tensor = torch.tensor(np.copy(y_16k)).unsqueeze(0)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    hop_length = 80

    # decoderの互換性問題を回避
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

    # フォールバック: decoderなし
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


def extract_from_audio(wav_path: str, label: str,
                       start_sec: float = None, end_sec: float = None):
    """
    音声ファイルからフレームごとの特徴量＋ラベルを抽出。

    Returns:
        features: shape=(N, 6)
        labels:   shape=(N,)  0=chest, 1=falsetto
    """
    print(f"[INFO] 読み込み中: {wav_path}")
    y, sr = librosa.load(wav_path, sr=None, mono=True)

    # 時間範囲でトリミング
    if start_sec is not None:
        y = y[int(start_sec * sr):]
    if end_sec is not None:
        end_sample = int(end_sec * sr)
        if start_sec is not None:
            end_sample -= int(start_sec * sr)
        y = y[:end_sample]

    duration = len(y) / sr
    print(f"[INFO] 長さ: {duration:.2f}s, ラベル: {label}")

    if duration < 0.5:
        print("[ERROR] 音声が短すぎます（0.5秒以上必要）")
        return None, None

    # 正規化
    y = y.astype(np.float32)
    y = y / (np.max(np.abs(y)) + 1e-8) * 0.95

    # CREPE
    print("[INFO] CREPE実行中...")
    f0_np, conf_np, y_16k, sr_crepe, hop_length = _run_crepe_simple(y, sr)

    # confidence フィルタ
    valid_mask = (conf_np >= 0.3) & (f0_np >= 65) & (f0_np <= 1324)
    valid_indices = np.where(valid_mask)[0]
    print(f"[INFO] 有効フレーム: {len(valid_indices)} / {len(f0_np)}")

    if len(valid_indices) < 5:
        print("[ERROR] 有効フレームが少なすぎます")
        return None, None

    # 特徴量抽出
    features_list = []
    frame_len = 2048
    label_int = 0 if label == "chest" else 1

    for idx in valid_indices:
        f0 = f0_np[idx]
        center = int(idx) * hop_length
        start = max(0, center - frame_len // 2)
        end = min(len(y_16k), center + frame_len // 2)
        frame = y_16k[start:end]

        if len(frame) < 512:
            continue

        feat = extract_features(frame, sr_crepe, f0)
        if feat is not None:
            features_list.append(feat)

    if not features_list:
        print("[ERROR] 特徴量が抽出できませんでした")
        return None, None

    features = np.array(features_list, dtype=np.float32)
    labels = np.full(len(features), label_int, dtype=np.int32)

    print(f"[OK] {len(features)} フレーム抽出完了")
    return features, labels


def load_dataset():
    """保存済みデータセットを読み込み"""
    if os.path.exists(DATASET_PATH):
        data = np.load(DATASET_PATH)
        return data["features"], data["labels"]
    return np.empty((0, 6), dtype=np.float32), np.empty(0, dtype=np.int32)


def save_dataset(features: np.ndarray, labels: np.ndarray):
    """データセットを保存"""
    os.makedirs(DATA_DIR, exist_ok=True)
    np.savez(DATASET_PATH, features=features, labels=labels)
    n_chest = int(np.sum(labels == 0))
    n_falsetto = int(np.sum(labels == 1))
    print(f"[OK] 保存完了: {DATASET_PATH}")
    print(f"     地声: {n_chest} フレーム / 裏声: {n_falsetto} フレーム / 合計: {len(labels)}")


def cmd_add(args):
    """音声ファイルを追加"""
    label = args.label
    if label not in ("chest", "falsetto"):
        print("[ERROR] ラベルは chest または falsetto を指定")
        return

    features, labels = extract_from_audio(
        args.file, label,
        start_sec=args.start, end_sec=args.end,
    )
    if features is None:
        return

    # 既存データに追加
    existing_feat, existing_labels = load_dataset()
    all_feat = np.vstack([existing_feat, features]) if len(existing_feat) > 0 else features
    all_labels = np.concatenate([existing_labels, labels]) if len(existing_labels) > 0 else labels

    save_dataset(all_feat, all_labels)


def cmd_stats(args):
    """データセット統計"""
    features, labels = load_dataset()
    if len(labels) == 0:
        print("データセットが空です。 labeler.py add で音声を追加してください。")
        return

    n_chest = int(np.sum(labels == 0))
    n_falsetto = int(np.sum(labels == 1))
    print(f"=== データセット統計 ===")
    print(f"  地声:   {n_chest:6d} フレーム")
    print(f"  裏声:   {n_falsetto:6d} フレーム")
    print(f"  合計:   {len(labels):6d} フレーム")
    print(f"  バランス: 地声 {n_chest / len(labels) * 100:.1f}% / 裏声 {n_falsetto / len(labels) * 100:.1f}%")

    print(f"\n=== 特徴量統計 ===")
    for i, name in enumerate(FEATURE_NAMES):
        chest_vals = features[labels == 0, i]
        falsetto_vals = features[labels == 1, i]
        print(f"  {name:12s}  "
              f"地声: {np.mean(chest_vals):7.2f} ±{np.std(chest_vals):5.2f}  "
              f"裏声: {np.mean(falsetto_vals):7.2f} ±{np.std(falsetto_vals):5.2f}"
              if len(chest_vals) > 0 and len(falsetto_vals) > 0
              else f"  {name:12s}  データ不足")


def cmd_clear(args):
    """データセットをクリア"""
    if os.path.exists(DATASET_PATH):
        os.remove(DATASET_PATH)
        print("[OK] データセットを削除しました")
    else:
        print("データセットが見つかりません")


def main():
    parser = argparse.ArgumentParser(description="地声/裏声ラベリングツール")
    sub = parser.add_subparsers(dest="command")

    # add
    p_add = sub.add_parser("add", help="音声ファイルを追加")
    p_add.add_argument("label", choices=["chest", "falsetto"], help="ラベル")
    p_add.add_argument("file", help="WAVファイルパス")
    p_add.add_argument("--start", type=float, default=None, help="開始時刻(秒)")
    p_add.add_argument("--end", type=float, default=None, help="終了時刻(秒)")
    p_add.set_defaults(func=cmd_add)

    # stats
    p_stats = sub.add_parser("stats", help="データセット統計")
    p_stats.set_defaults(func=cmd_stats)

    # clear
    p_clear = sub.add_parser("clear", help="データセットをクリア")
    p_clear.set_defaults(func=cmd_clear)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()