/**
 * 【Landing.tsx】
 * 役割：アプリの「入り口」となるトップ画面です。
 * 画面を左右（スマホでは上下）に大きく2分割し、「新規録音」か「履歴確認」かを
 * 直感的に選べるサイバーパンク風のデザインになっています。
 * 💡 設計図（FRONTEND_STRUCTURE.md）に基づく移動案：
 * 1. 移動先: src/features/home/pages/Landing.tsx
 */

import React from 'react';
// アイコン素材（マイクと時計）をインポート
import { MicrophoneIcon, ClockIcon } from '@heroicons/react/24/solid';
// この画面専用のCSS（ネオン演出など）を読み込み
import './HomePage.css';

/** * プロパティの定義 (Props)
 * 親コンポーネント（AppRoutes等）から、ボタンを押した時の動作を受け取ります。
 */
interface Props {
    onRecordClick: () => void;   // 「NEW RECORD」側を押した時の処理
    onHistoryClick?: () => void;  // 「HISTORY」側を押した時の処理
}

const Landing: React.FC<Props> = ({ onRecordClick, onHistoryClick }) => {
    return (
        /** * landing-container: 画面いっぱいの背景
         * pt-20: 上部の共通ヘッダーと重ならないように余白を空けます。
         */
        <div className="landing-container pt-20">

            {/* ── 左側：RECORD セクション（赤色のネオン演出） ── */}
            <div
                className="landing-section left group cursor-pointer animate-slide-in-left"
                onClick={onRecordClick}
            >
                {/* 背景のドットパターン（網目状の装飾） */}
                <div className="absolute inset-0 opacity-30 mix-blend-overlay" style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='6' height='6' xmlns='http://www.w3.org/2000/svg'%3E%3Crect width='1' height='1' fill='%23fff' fill-opacity='0.15'/%3E%3C/svg%3E\")", backgroundSize: '6px 6px' }}></div>

                {/* 背景の巨大なマイクアイコン（透かし装飾）
                    装飾用なので、少し斜めに回転させて透明度を下げて配置しています。
                */}
                <MicrophoneIcon className="absolute w-[20rem] h-[20rem] md:w-[40rem] md:h-[40rem] -left-10 top-[25%] -translate-y-1/2 md:bottom-[-5rem] md:top-auto md:translate-y-0 text-white opacity-10 transform -rotate-12 pointer-events-none" />

                {/* 中央のテキストコンテンツ */}
                <div className="landing-content flex flex-col justify-center items-start h-full">
                    <h2 className="text-5xl sm:text-6xl md:text-[7vw] font-black italic tracking-tighter text-white drop-shadow-[5px_5px_0px_rgba(0,0,0,0.3)] leading-none transition-all duration-300 group-hover:scale-105 group-hover:text-pink-400">
                        NEW<br />RECORD
                    </h2>
                    <p className="mt-4 text-sm md:text-lg font-bold text-pink-500 tracking-[0.3em] uppercase opacity-70 group-hover:opacity-100 transition-opacity">
                        Analyze Voice
                    </p>
                </div>

                {/* 右端の境界線ライト（ホバー時に光る） */}
                <div className="absolute top-0 right-0 w-[2px] h-full bg-gradient-to-b from-transparent via-pink-500 to-transparent opacity-30 group-hover:opacity-100 transition-opacity shadow-[0_0_15px_rgba(236,72,153,0.5)]"></div>
            </div>

            {/* ── 右側：HISTORY セクション（青色のネオン演出） ── */}
            <div
                className="landing-section right group cursor-pointer animate-slide-in-right"
                onClick={onHistoryClick}
            >
                {/* 背景のドットパターン */}
                <div className="absolute inset-0 opacity-30 mix-blend-overlay" style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='10' height='10' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M0 0h5v5H0zM5 5h5v5H5z' fill='%23fff' fill-opacity='0.12'/%3E%3C/svg%3E\")", backgroundSize: '10px 10px' }}></div>

                {/* 背景の巨大な時計アイコン（透かし装飾） */}
                <ClockIcon className="absolute w-[20rem] h-[20rem] md:w-[40rem] md:h-[40rem] -right-10 top-[75%] -translate-y-1/2 md:top-[-5rem] md:translate-y-0 text-white opacity-10 transform rotate-12 pointer-events-none" />

                {/* 中央のテキストコンテンツ */}
                <div className="landing-content flex flex-col justify-center items-end h-full">
                    <h2 className="text-5xl sm:text-6xl md:text-[7vw] font-black italic tracking-tighter text-white drop-shadow-[5px_5px_0px_rgba(0,0,0,0.3)] leading-none text-right transition-all duration-300 group-hover:scale-105 group-hover:text-cyan-400">
                        MY<br />HISTORY
                    </h2>
                    <p className="mt-4 text-sm md:text-lg font-bold text-cyan-500 tracking-[0.3em] uppercase opacity-70 group-hover:opacity-100 transition-opacity">
                        View Results
                    </p>
                </div>

                {/* 左端の境界線ライト */}
                <div className="absolute top-0 left-0 w-[2px] h-full bg-gradient-to-b from-transparent via-cyan-500 to-transparent opacity-30 group-hover:opacity-100 transition-opacity shadow-[0_0_15px_rgba(34,211,238,0.5)]"></div>
            </div>
        </div>
    );
};

export default Landing;