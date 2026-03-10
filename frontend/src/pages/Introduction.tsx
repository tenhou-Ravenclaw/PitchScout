/**
 * 【Introduction.tsx】
 * 役割：アプリを開いた瞬間に表示される、大きな二択のメニュー画面です。
 * 特徴：「新規録音（RECORD）」と「分析画面（ANALYSIS）」を画面の左右で斜めに分割して表示します。
 */

import React from 'react';
// アイコン素材（マイク、時計）をインポート
import { MicrophoneIcon, MagnifyingGlassIcon } from '@heroicons/react/24/solid';
// この画面専用のスタイルシート（斜め分割やネオンエフェクト）
import '../Introduction.css';

/** 画面が外から受け取る関数（クリック時の動き）の定義 */
interface Props {
    onRecordClick: () => void;  // 左側をクリックした時
    onHistoryClick?: () => void; // 右側（ANALYSIS）をクリックした時
}

/**
 * イントロダクション画面本体。
 * @param onRecordClick 新規録音ボタン押下時の処理
 * @param onHistoryClick ANALYSISボタン押下時の処理
 */
const Introduction: React.FC<Props> = ({ onRecordClick, onHistoryClick }) => {
    const [hoveredSide, setHoveredSide] = React.useState<'left' | 'right' | null>(null);

    const handleHover = (side: 'left' | 'right'): void => {
        setHoveredSide((prev) => (prev === side ? prev : side));
    };

    const containerClassName = `landing-container${
        hoveredSide === 'left'
            ? ' is-hover-left'
            : hoveredSide === 'right'
                ? ' is-hover-right'
                : ''
    }`;

    return (
        /** ヘッダー分のレイアウトは Layout 側で処理されるため、ここでは追加余白を持たせません */
        <div className={containerClassName}>

            {/* ── 左側 / 赤色セクション: NEW RECORD ── */}
            <div
                className="landing-section left group cursor-pointer animate-slide-in-left"
                onClick={onRecordClick}
                onPointerEnter={() => handleHover('left')}
                onPointerMove={() => handleHover('left')}
                onPointerLeave={() => setHoveredSide(null)}
            >
                {/* 背景：細かいドット模様の装飾 */}
                <div className="landing-pattern left"></div>

                {/* 背景：巨大なマイクアイコン（装飾用） */}
                <MicrophoneIcon className="landing-bg-icon left" />

                {/* 文字コンテンツ */}
                <div className="landing-content flex flex-col justify-center h-full">
                    <h2 className="landing-title primary group-hover:scale-105 group-hover:translate-x-4">
                        NEW<br />RECORD
                    </h2>
                    <p className="landing-subtitle left">
                        Start Here
                    </p>
                </div>
            </div>

            {/* ── 右側 / 青色セクション: ANALYSIS ── */}
            <div
                className="landing-section right group cursor-pointer animate-slide-in-right"
                onClick={onHistoryClick}
                onPointerEnter={() => handleHover('right')}
                onPointerMove={() => handleHover('right')}
                onPointerLeave={() => setHoveredSide(null)}
            >
                {/* 背景：四角いパターンの装飾 */}
                <div className="landing-pattern right"></div>

                {/* 背景：巨大な虫眼鏡アイコン（装飾用） */}
                <MagnifyingGlassIcon className="landing-bg-icon right" />

                {/* 文字コンテンツ */}
                <div className="landing-content flex flex-col justify-center items-end h-full">
                    <h2 className="landing-title secondary text-right group-hover:scale-105 group-hover:-translate-x-4">
                        ANALYSIS
                    </h2>
                    <p className="landing-subtitle right text-right">
                        Check Result
                    </p>
                </div>
            </div>
        </div>
    );
};

export default React.memo(Introduction);