/**
 * 【MenuPage.tsx】
 * 役割：解析モード（通常・カラオケ・アップロード）を選択するためのメインメニュー画面です。
 * 特徴：サイバーパンク風のグリッド背景、ネオン輝くタイル型ボタン、解析中のステータスバナーを備えています。
 */
import React from 'react';
import { MicrophoneIcon, MusicalNoteIcon, CloudArrowUpIcon, ClockIcon } from '@heroicons/react/24/solid';

/** MenuPage が受け取るプロパティ */
interface MenuPageProps {
    /** 通常録音ボタンのクリック処理 */
    onNormalClick: () => void;
    /** カラオケ録音ボタンのクリック処理 */
    onKaraokeClick: () => void;
    /** ファイルアップロードボタンのクリック処理 */
    onUploadClick: () => void;
    /** 履歴ボタンのクリック処理 */
    onHistoryClick?: () => void;
    /** 解析中かどうか */
    isAnalyzing: boolean;
}

const MenuPage: React.FC<MenuPageProps> = ({ onNormalClick, onKaraokeClick, onUploadClick, onHistoryClick, isAnalyzing }) => {

    return (
        <div className="min-h-[100dvh] relative bg-transparent overflow-hidden">

            {/* ── 背景装飾: サイバーグリッド ── */}
            <div className="absolute inset-0 z-0 pointer-events-none bg-[linear-gradient(rgba(6,182,212,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(6,182,212,0.05)_1px,transparent_1px)] [background-size:40px_40px]"></div>
            <div className="absolute inset-0 z-0 pointer-events-none opacity-30 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,0,0,0.8)_2px,rgba(0,0,0,0.8)_4px)]"></div>
            {/* 中央のぼんやりした光の演出 */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-cyan-500/10 rounded-full blur-[120px] pointer-events-none"></div>

            <div className="relative z-10 container mx-auto px-4 h-full flex flex-col justify-center min-h-[calc(100vh-80px)] py-12">

                {/* ── ヘッダータイトル ── */}
                <div className="mb-12 text-center md:text-left md:ml-12">
                    <h1 className="text-6xl md:text-8xl font-black italic title-gradient-cyber mb-4 drop-shadow-[0_0_15px_rgba(255,255,255,0.3)] tracking-wide">
                        RECORD
                    </h1>
                </div>

                {/* ── 解析中バナー ──
                   💡 解析が動いている間は、新しい録音ボタンを押せなくし、警告を表示します。
                */}
                {isAnalyzing && (
                    <div className="w-full max-w-6xl mx-auto mb-8 p-4 bg-slate-800/90 border-2 border-cyan-400 rounded-xl shadow-[0_0_20px_rgba(34,211,238,0.4)] animate-pulse text-center backdrop-blur-sm z-20">
                        <span className="text-xl md:text-2xl font-bold text-cyan-400 italic tracking-wider">
                            🔄 現在、バックグラウンドで音声を解析中です...
                        </span>
                        <br />
                        <span className="text-sm md:text-base font-medium text-slate-300 mt-2 inline-block">
                            解析が完了すると自動的に結果画面へ移動します。解析中は新しく録音できませんが、履歴は閲覧できます。
                        </span>
                    </div>
                )}

                {/* ── メニューボタンのグリッド配置 ── */}
                <div className="grid grid-cols-1 md:grid-cols-12 gap-6 w-full max-w-6xl mx-auto transition-all duration-300">

                    {/* 1. 通常録音ボタン (大きなタイル) */}
                    <button
                        onClick={onNormalClick}
                        disabled={isAnalyzing} // 解析中は無効化
                        className="group relative col-span-1 md:col-span-6 row-span-2 h-64 md:h-auto bg-slate-900/80 backdrop-blur-md border-4 border-cyan-400 transform -skew-x-3 hover:skew-x-0 transition-all duration-300 shadow-[8px_8px_0px_0px_rgba(6,182,212,0.6)] hover:shadow-[0px_0px_40px_rgba(6,182,212,1)]"
                    >
                        {/* 内部装飾の光の漏れ */}
                        <div className="absolute -top-1/2 -left-1/2 w-full h-full bg-cyan-400/20 blur-[60px] rounded-full pointer-events-none"></div>
                        <div className="absolute inset-0 flex flex-col items-center justify-center z-10 p-8">
                            <MicrophoneIcon className="w-24 h-24 md:w-32 md:h-32 text-cyan-400 group-hover:text-cyan-300 transition-colors duration-300 drop-shadow-[0_0_15px_rgba(6,182,212,0.8)] animate-pulse" />
                            <h2 className="text-3xl md:text-5xl font-black italic text-white mt-4 tracking-tighter uppercase transform -skew-x-6 drop-shadow-[0_0_10px_rgba(6,182,212,0.8)]">
                                Start<br />Recording
                            </h2>
                        </div>
                    </button>

                    {/* 2. カラオケモード (中サイズ) */}
                    <button
                        onClick={onKaraokeClick}
                        disabled={isAnalyzing}
                        className="group relative col-span-1 md:col-span-6 h-40 bg-slate-900/80 border-4 border-pink-500 transform -skew-x-3 hover:skew-x-0 transition-all duration-300 shadow-[8px_8px_0px_0px_rgba(236,72,153,0.6)] hover:shadow-[0px_0px_40px_rgba(236,72,153,1)]"
                    >
                        <div className="absolute inset-0 flex items-center justify-between px-8 z-10">
                            <h2 className="text-2xl md:text-3xl font-black italic text-white tracking-tighter uppercase transform -skew-x-6 drop-shadow-[0_0_10px_rgba(236,72,153,0.8)]">
                                Karaoke<br />Mode
                            </h2>
                            <MusicalNoteIcon className="w-16 h-16 text-pink-500 group-hover:text-pink-400 drop-shadow-[0_0_15px_rgba(236,72,153,0.8)]" />
                        </div>
                    </button>

                    {/* 3. アップロード (小サイズ) */}
                    <button
                        onClick={onUploadClick}
                        disabled={isAnalyzing}
                        className="group relative col-span-1 md:col-span-3 h-40 bg-slate-900/80 border-4 border-yellow-400 transform -skew-x-3 hover:skew-x-0 transition-all duration-300 shadow-[8px_8px_0px_0px_rgba(250,204,21,0.6)]"
                    >
                        <div className="absolute inset-0 flex flex-col items-center justify-center z-10 p-4">
                            <CloudArrowUpIcon className="w-10 h-10 text-yellow-400 group-hover:text-yellow-300 mb-2 drop-shadow-[0_0_10px_rgba(250,204,21,0.8)]" />
                            <h2 className="text-xl font-bold italic text-white tracking-tighter uppercase transform -skew-x-6">Upload</h2>
                        </div>
                    </button>

                    {/* 4. 履歴ボタン (小サイズ) — 解析中でも閲覧は可能なので disabled にしない */}
                    <button
                        onClick={onHistoryClick}
                        className="group relative col-span-1 md:col-span-3 h-40 bg-slate-900/80 border-4 border-emerald-400 transform -skew-x-3 hover:skew-x-0 transition-all duration-300 shadow-[8px_8px_0px_0px_rgba(52,211,153,0.6)]"
                    >
                        <div className="absolute inset-0 flex flex-col items-center justify-center z-10 p-4">
                            <ClockIcon className="w-10 h-10 text-emerald-400 group-hover:text-emerald-300 mb-2 drop-shadow-[0_0_10px_rgba(52,211,153,0.8)]" />
                            <h2 className="text-xl font-bold italic text-white tracking-tighter uppercase transform -skew-x-6">History</h2>
                        </div>
                    </button>

                </div>
            </div>
        </div>
    );
};

export default MenuPage;