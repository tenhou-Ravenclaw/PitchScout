/**
 * 【LogoSplash.tsx】
 * 役割：アプリ起動時に表示されるアニメーション画面（スプラッシュ画面）です。
 * 2つの画像（ヒストグラムと波形）を順番に動かして、アプリの世界観を演出します。
 * 💡 設計図（FRONTEND_STRUCTURE.md）に基づく移動案：
 * 1. 移動先: src/components/ui/LogoSplash.tsx (または src/app/ 内)
 */

import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
// ロゴに使用する画像とスタイルをインポート
import histogramImg from "../assets/new-logo-histogram.png";
import waveImg from "../assets/new-logo-wave.png";
import "../styles/LogoSplash.css";

interface LogoSplashProps {
  onAnimationEnd: () => void; // アニメーションがすべて終わった時に呼ばれる関数
}

export const LogoSplash: React.FC<LogoSplashProps> = ({ onAnimationEnd }) => {
  // ── 状態管理 (State) ──
  // スプラッシュ画面を表示し続けるかどうかのフラグ
  const [isVisible, setIsVisible] = useState(true);
  const navigate = useNavigate();

  /**
   * 波形（Wave）のアニメーションが終わった時に呼ばれる処理
   */
  const handleWaveAnimationEnd = () => {
    // 表示フラグを false にして、スプラッシュ画面を閉じる準備をする
    setIsVisible(false);
  };

  /**
   * 副作用 (Effects)
   * アニメーションが何らかの理由で止まってしまった場合のための安全策（フォールバック）です。
   */
  useEffect(() => {
    // 5秒経過したら、アニメーションの途中でも強制的に終了させます
    const timer = setTimeout(() => {
      setIsVisible(false);
    }, 5000);
    
    // コンポーネントが消える時にタイマーを解除（メモリ漏れ防止）
    return () => clearTimeout(timer);
  }, []);

  /**
   * 表示フラグが false になった瞬間に実行される処理
   */
  useEffect(() => {
    if (!isVisible) {
      // 親コンポーネント（App.tsx）に「終わったよ」と伝えます
      onAnimationEnd();
      // 強制的にトップページ（/）へ移動させます
      navigate("/", { replace: true });
    }
  }, [isVisible, navigate, onAnimationEnd]);

  // 非表示なら何も描画しない
  if (!isVisible) {
    return null;
  }

  return (
    /**
     * ── 表示 (Render) ──
     * CSSアニメーションを使ってロゴを動かします。
     */
    <div className="logo-splash-overlay">
      <div className="logo-splash-container">
        {/* 1. ヒストグラム画像：最初に表示される要素 */}
        <img
          src={histogramImg}
          alt="histogram"
          className="logo-splash-element logo-splash-histogram"
        />
        {/* 2. 波形画像：ヒストグラムの後に動き出します。
             onAnimationEnd イベントでアニメーションの終了を検知します。
        */}
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