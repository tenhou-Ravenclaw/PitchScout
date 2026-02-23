/**
 * 【Home.tsx】
 * 役割：録音開始、カラオケモード、アップロード、履歴確認への導線となるメインメニュー画面です。
 * 💡 設計図（FRONTEND_STRUCTURE.md）に基づく移動案：
 * 1. 移動先: src/features/home/pages/Home.tsx (または src/pages/Home.tsx)
 * 2. 背景のグリッドやスキャンラインなどの装飾を「CyberBackground」のような共通部品にすると
 * 他の画面でも使い回しやすくなります。
 */

import React from 'react';
// アイコン素材の読み込み
import { MicrophoneIcon, MusicalNoteIcon, CloudArrowUpIcon, ClockIcon } from '@heroicons/react/24/solid';
// 分析中の状態（バックグラウンドで動いているか）を把握するためのコンテキスト
import { useAnalysis } from './contexts/AnalysisContext';

/**
 * プロパティの定義 (Props)
 * 親コンポーネント（AppRoutes等）から「ボタンを押した時に何をするか」を受け取ります。
 */
interface Props {
    onNormalClick: () => void;  // 「マイクで録音」ボタン
    onKaraokeClick: () => void; // 「カラオケモード」ボタン
    onUploadClick: () => void;  // 「アップロード」ボタン
    onHistoryClick?: () => void; // 「履歴」ボタン
}

const Home: React.FC<Props> = ({ onNormalClick, onKaraokeClick, onUploadClick, onHistoryClick }) => {
    // 現在、裏側で音声解析が走っているかどうかを取得します
    const { isAnalyzing } = useAnalysis();

    return (
        <div className="min-h-[100dvh] relative bg-transparent overflow-hidden">

            {/* ── 背景演出：サイバーパンク・グリッド ──
                青い格子状の背景（Grid）を作っています。
            */}
            <div
                className="absolute inset-0 z-0 pointer-events-none bg-[linear-gradient(rgba(6,182,212,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(6,182,212,0.05)_1px,transparent_1px)] [background-size:40px_40px] [background-position:center_center]"
            ></div>
            
            {/* ── 背景演出：スキャンライン ──
                ブラウン管テレビのような横線（Scanlines）のテクスチャを重ねています。
            */}
            <div
                className="absolute inset-0 z-0 pointer-events-none opacity-30 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,0,0,0.8)_2px,rgba(0,0,0,0.8)_4px)]"
            ></div>
            
            {/* ── 背景演出：光の溜まり（Glow） ──
                中央に大きなぼかした光を配置して奥行きを出しています。
            */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-cyan-500/10 rounded-full blur-[120px] pointer-events-none z-0"></div>

            {/* メインコンテンツエリア */}
            <div className="relative z-10 container mx-auto px-4 h-full flex flex-col justify-center min-h-[calc(100vh-80px)] py-12">

                {/* タイトルセクション */}
                <div className="mb-12 text-center md:text-left md:ml-12">
                    <h1 className="text-6xl md:text-8xl font-black italic text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-fuchsia-400 to-yellow-400 mb-4 drop-shadow-[0_0_15px_rgba(255,255,255,0.3)] tracking-wide">
                        RECORD
                    </h1>
                </div>

                {/* ── 解析中バナー ──
                    解析が終わるまで、新しい録音ボタンを押せないように案内を出します。
                */}
                {isAnalyzing && (
                    <div className="w-full max-w-6xl mx-auto mb-8 p-4 bg-slate-800/90 border-2 border-cyan-400 rounded-xl shadow-[0_0_20px_rgba(34,211,238,0.4)] animate-pulse text-center backdrop-blur-sm z-20">
                        <span className="text-xl md:text-2xl font-bold text-cyan-400 italic tracking-wider">
                            🔄 現在、バックグラウンドで音声を解析中です...
                        </span>
                        <br />
                        <span className="text-sm md:text-base font-medium text-slate-300 mt-2 inline-block">
                            解析が完了すると自動的に結果画面へ移動します。新しく録音することはできません。
                        </span>
                    </div>
                )}

                {/* ── メニューボタンのグリッド配置 ──
                    画面幅に合わせて、12分割のグリッドでボタンを並べています。
                */}
                <div className="grid grid-cols-1 md:grid-cols-12 gap-6 w-full max-w-6xl mx-auto transition-all duration-300">

                    {/* 1. 通常録音ボタン（Hugeサイズ / 12列中6列使用） */}
                    <button
                        onClick={onNormalClick}
                        disabled={isAnalyzing} // 解析中は無効化
                        className="group relative col-span-1 md:col-span-6 row-span-2 h-64 md:h-auto bg-slate-900/80 backdrop-blur-md bg-gradient-to-br from-cyan-900/40 to-slate-900/80 border-4 border-cyan-400 transform -skew-x-3 hover:skew-x-0 transition-all duration-300 shadow-[8px_8px_0px_0px_rgba(6,182,212,0.6)] hover:shadow-[0px_0px_40px_rgba(6,182,212,1)] hover:border-cyan-300 hover:scale-[1.02] overflow-hidden focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-cyan-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 disabled:opacity-50 disabled:pointer-events-none"
                    >
                        {/* ホバー時の光漏れ演出（Light Leak） */}
                        <div className="absolute -top-1/2 -left-1/2 w-full h-full bg-cyan-400/20 blur-[60px] rounded-full pointer-events-none group-hover:bg-cyan-400/40 transition-all duration-500"></div>
                        <div className="absolute inset-0 opacity-20 z-0" style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='6' height='6' xmlns='http://www.w3.org/2000/svg'%3E%3Crect width='1' height='1' fill='%23fff' fill-opacity='0.15'/%3E%3C/svg%3E\")", backgroundSize: '6px 6px' }}></div>

                        <div className="absolute inset-0 flex flex-col items-center justify-center z-10 p-8">
                            <MicrophoneIcon className="w-24 h-24 md:w-32 md:h-32 text-cyan-400 group-hover:text-cyan-300 transition-colors duration-300 drop-shadow-[0_0_15px_rgba(6,182,212,0.8)] group-hover:drop-shadow-[0_0_25px_rgba(6,182,212,1)] animate-pulse" />
                            <h2 className="text-3xl md:text-5xl font-black italic text-white mt-4 tracking-tighter uppercase transform -skew-x-6 drop-shadow-[0_0_10px_rgba(6,182,212,0.8)] group-hover:drop-shadow-[0_0_20px_rgba(6,182,212,1)]">
                                Start<br />Recording
                            </h2>
                        </div>
                    </button>

                    {/* 2. カラオケモード（Mediumサイズ / 12列中6列使用） */}
                    <button
                        onClick={onKaraokeClick}
                        disabled={isAnalyzing}
                        className="group relative col-span-1 md:col-span-6 h-40 bg-slate-900/80 backdrop-blur-md bg-gradient-to-br from-pink-900/40 to-slate-900/80 border-4 border-pink-500 transform -skew-x-3 hover:skew-x-0 transition-all duration-300 shadow-[8px_8px_0px_0px_rgba(236,72,153,0.6)] hover:shadow-[0px_0px_40px_rgba(236,72,153,1)] hover:border-pink-400 hover:scale-[1.02] overflow-hidden focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-pink-300 focus-visible:ring-offset-4 focus-visible:ring-offset-slate-900 disabled:opacity-50 disabled:pointer-events-none"
                    >
                        <div className="absolute -bottom-1/2 -right-1/2 w-64 h-64 bg-pink-500/20 blur-[50px] rounded-full pointer-events-none group-hover:bg-pink-500/40 transition-all duration-500"></div>
                        <div className="absolute inset-0 opacity-20 z-0" style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='6' height='6' xmlns='http://www.w3.org/2000/svg'%3E%3Crect width='1' height='1' fill='%23fff' fill-opacity='0.15'/%3E%3C/svg%3E\")", backgroundSize: '6px 6px' }}></div>

                        <div className="absolute inset-0 flex items-center justify-between px-8 z-10">
                            <div className="text-left">
                                <h2 className="text-2xl md:text-3xl font-black italic text-white tracking-tighter uppercase transform -skew-x-6 drop-shadow-[0_0_10px_rgba(236,72,153,0.8)] group-hover:drop-shadow-[0_0_20px_rgba(236,72,153,1)]">
                                    Karaoke<br />Mode
                                </h2>
                            </div>
                            <MusicalNoteIcon className="w-16 h-16 text-pink-500 group-hover:text-pink-400 transition-colors duration-300 drop-shadow-[0_0_15px_rgba(236,72,153,0.8)] group-hover:drop-shadow-[0_0_25px_rgba(236,72,153,1)]" />
                        </div>
                    </button>

                    {/* 3. アップロード（Smallサイズ / 12列中3列使用） */}
                    <button
                        onClick={onUploadClick}
                        disabled={isAnalyzing}
                        className="group relative col-span-1 md:col-span-3 h-40 bg-slate-900/80 backdrop-blur-md bg-gradient-to-br from-yellow-900/40 to-slate-900/80 border-4 border-yellow-400 transform -skew-x-3 hover:skew-x-0 transition-all duration-300 shadow-[8px_8px_0px_0px_rgba(250,204,21,0.6)] hover:shadow-[0px_0px_30px_rgba(250,204,21,1)] hover:border-yellow-300 hover:scale-[1.02] overflow-hidden focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-yellow-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 disabled:opacity-50 disabled:pointer-events-none"
                    >
                        <div className="absolute -top-1/4 -right-1/4 w-32 h-32 bg-yellow-400/20 blur-[40px] rounded-full pointer-events-none group-hover:bg-yellow-400/40 transition-all duration-500"></div>
                        <div className="absolute inset-0 flex flex-col items-center justify-center z-10 p-4">
                            <CloudArrowUpIcon className="w-10 h-10 text-yellow-400 group-hover:text-yellow-300 mb-2 transition-colors duration-300 drop-shadow-[0_0_10px_rgba(250,204,21,0.8)] group-hover:drop-shadow-[0_0_20px_rgba(250,204,21,1)]" />
                            <h2 className="text-xl font-bold italic text-white tracking-tighter uppercase transform -skew-x-6 drop-shadow-[0_0_8px_rgba(250,204,21,0.8)] group-hover:drop-shadow-[0_0_15px_rgba(250,204,21,1)]">
                                Upload
                            </h2>
                        </div>
                    </button>

                    {/* 4. 履歴（Smallサイズ / 12列中3列使用） */}
                    <button
                        onClick={onHistoryClick}
                        disabled={isAnalyzing}
                        className="group relative col-span-1 md:col-span-3 h-40 bg-slate-900/80 backdrop-blur-md bg-gradient-to-br from-emerald-900/40 to-slate-900/80 border-4 border-emerald-400 transform -skew-x-3 hover:skew-x-0 transition-all duration-300 shadow-[8px_8px_0px_0px_rgba(52,211,153,0.6)] hover:shadow-[0px_0px_30px_rgba(52,211,153,1)] hover:border-emerald-300 hover:scale-[1.02] overflow-hidden focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-emerald-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 disabled:opacity-50 disabled:pointer-events-none"
                    >
                        <div className="absolute -bottom-1/4 -left-1/4 w-32 h-32 bg-emerald-400/20 blur-[40px] rounded-full pointer-events-none group-hover:bg-emerald-400/40 transition-all duration-500"></div>
                        <div className="absolute inset-0 flex flex-col items-center justify-center z-10 p-4">
                            <ClockIcon className="w-10 h-10 text-emerald-400 group-hover:text-emerald-300 mb-2 transition-colors duration-300 drop-shadow-[0_0_10px_rgba(52,211,153,0.8)] group-hover:drop-shadow-[0_0_20px_rgba(52,211,153,1)]" />
                            <h2 className="text-xl font-bold italic text-white tracking-tighter uppercase transform -skew-x-6 drop-shadow-[0_0_8px_rgba(52,211,153,0.8)] group-hover:drop-shadow-[0_0_15px_rgba(52,211,153,1)]">
                                History
                            </h2>
                        </div>
                    </button>

                </div>
            </div>
        </div>
    );
};

export default Home;