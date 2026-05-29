/**
 * 【LogoSplash.tsx】
 * 役割：アプリ起動時に表示されるアニメーション付きのスプラッシュ画面です。
 * 特徴：2つのロゴ画像（ヒストグラムと波形）を順番に表示し、演出が終わると自動的にトップ画面へ移動させます。
 */

import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
// ロゴに使用する画像アセットと専用のCSSを読み込みます
import histogramImg from "../../assets/new-logo-histogram.png";
import waveImg from "../../assets/new-logo-wave.png";
import "../../styles/LogoSplash.css";

interface LogoSplashProps {
  onAnimationEnd: () => void; // アニメーション終了時に親（App.tsx）へ知らせる関数
}

export const LogoSplash: React.FC<LogoSplashProps> = ({ onAnimationEnd }) => {
  // スプラッシュを表示し続けるかどうかの状態管理
  const [isVisible, setIsVisible] = useState(true);
  const navigate = useNavigate();

  /** ── スプラッシュ終了ハンドラー ──
   * 波形アニメーション終了またはフェイルセーフタイマー満了で呼ばれます。
   */
  const handleWaveAnimationEnd = (): void => {
    setIsVisible(false); // 表示フラグをOFFにする
  };

  /** ── アニメーション完了タイマー ──
   * <img> の animationend イベントは animation-delay と組み合わせた場合に
   * Safari 等で発火しないことがあるため、アニメーション総時間（delay 1s + duration 3s = 4000ms）
   * に合わせたタイマーをメインの終了トリガーとする。
   * prefers-reduced-motion 時は即時終了。
   */
  useEffect(() => {
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (prefersReducedMotion) {
      handleWaveAnimationEnd();
      return;
    }

    // CSS: animation-delay(1s) + animation-duration(3s) = 4000ms
    const splashTimeout: ReturnType<typeof setTimeout> = setTimeout(() => {
      handleWaveAnimationEnd();
    }, 4000);

    return () => {
      clearTimeout(splashTimeout);
    };
  }, []);

  /** ── 画面遷移の実行 ──
   * 変更: isVisible が false になった時点で親へ通知し、URLをトップへ統一します。
   */
  useEffect(() => {
    if (!isVisible) {
      onAnimationEnd();
      navigate("/", { replace: true }); // 履歴に残さない形で遷移
    }
  }, [isVisible, navigate, onAnimationEnd]);

  // すでに非表示なら何も描画しません
  if (!isVisible) {
    return null;
  }

  return (
    <div className="logo-splash-overlay">
      <div className="logo-splash-container">
        {/* 1つ目の要素：ヒストグラム（静止、または先行して表示） */}
        <img
          src={histogramImg}
          alt="histogram"
          className="logo-splash-element logo-splash-histogram"
          // 追加: スプラッシュ用画像は最優先で取得して、リロード時の待ちを減らす
          fetchPriority="high"
          // 追加: 初期演出で使うため遅延読み込みを無効化
          loading="eager"
          // 追加: デコードを前倒しして初回描画を速くする
          decoding="sync"
        />
        {/* 2つ目の要素：波形（アニメーションが設定されており、終了後に非表示化をトリガーします） */}
        <img
          src={waveImg}
          alt="wave"
          className="logo-splash-element logo-splash-wave"
          onAnimationEnd={handleWaveAnimationEnd}
          // 追加: 2枚目画像も優先ロードして演出開始時の空白を防ぐ
          fetchPriority="high"
          // 追加: スプラッシュ用なので lazy を使わず即時ロードする
          loading="eager"
          // 追加: 体感遅延を抑えるため同期デコードを指定
          decoding="sync"
        />
      </div>
    </div>
  );
};
