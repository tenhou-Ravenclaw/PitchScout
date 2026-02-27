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

  /** ── アニメーション終了ハンドラー ──
   * 波形（Wave）のアニメーションが終わったタイミングで呼ばれます。
   */
  const handleWaveAnimationEnd = () => {
    setIsVisible(false); // 表示フラグをOFFにする
  };

  /** ── 画面遷移の実行 ──
   * isVisible が false になった瞬間、親へ通知し、URLをトップ（/）に切り替えます。
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
        />
        {/* 2つ目の要素：波形（アニメーションが設定されており、終了後に非表示化をトリガーします） */}
        <img
          src={waveImg}
          alt="wave"
          className="logo-splash-element logo-splash-wave"
          onAnimationEnd={handleWaveAnimationEnd}
        />
      </div>
    </div>
  );
};