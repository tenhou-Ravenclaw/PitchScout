/**
 * 【BottomNav.tsx】
 * 役割：スマートフォンなどのモバイル端末で画面下部に表示されるナビゲーションバーです。
 * 特徴：現在開いているページ（URL）に合わせてアイコンの色を変え、中央の「録音」ボタンを強調表示します。
 */

import React from "react";
import { useNavigate } from "react-router-dom";
// アイコン素材の読み込み
import {
  MusicalNoteIcon,
  HeartIcon,
  ChartBarIcon,
  UserCircleIcon,
} from "@heroicons/react/24/outline";
import { MicrophoneIcon as MicrophoneIconSolid } from "@heroicons/react/24/solid";

/** ナビゲーションバーが受け取るプロパティ（現在のパスと認証状態） */
interface BottomNavProps {
  currentPath: string;
  isAuthenticated?: boolean;
}

/** ── 「録音中」とみなすURLのセット ── */
const RECORDING_PATHS = new Set([
  "/record",
  "/record/normal",
  "/record/karaoke",
  "/record/upload",
]);

const BottomNav: React.FC<BottomNavProps> = ({
  currentPath,
  isAuthenticated = false,
}) => {
  const navigate = useNavigate();

  /** ── 現在のページに応じたデザインクラスを返す関数 ──
   * 💡 選択中のメニューには光るエフェクト（drop-shadow）を付与します。
   */
  const getItemClass = (path: string) =>
    currentPath === path
      ? "text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.8)]"
      : "text-slate-500 hover:text-slate-400";

  /** 現在のURLが録音関連のページかどうかを判定します */
  const isRecordingActive = RECORDING_PATHS.has(currentPath);

  return (
    /** md:hidden: PCサイズでは非表示にし、スマホサイズでのみ表示します */
    <div className="md:hidden fixed bottom-0 left-0 w-full bg-slate-950 border-t border-slate-800 shadow-[0_-5px_20px_rgba(0,0,0,0.5)] z-50 px-2 pb-safe">
      <div className="flex justify-between items-end h-16 pb-2">
        {/* 1. 楽曲一覧（アーティスト）ボタン */}
        <button
          onClick={() => navigate("/songs")}
          className={`flex-1 flex flex-col items-center justify-end h-full py-1 ${getItemClass("/songs")}`}
        >
          <MusicalNoteIcon className="w-6 h-6 mb-1" />
          <span className="text-[10px] font-medium">アーティスト</span>
        </button>

        {/* 2. お気に入りボタン */}
        <button
          onClick={() => navigate("/favorites")}
          className={`flex-1 flex flex-col items-center justify-end h-full py-1 ${getItemClass("/favorites")}`}
        >
          <HeartIcon className="w-6 h-6 mb-1" />
          <span className="text-[10px] font-medium">お気に入り</span>
        </button>

        {/* 3. 録音 (中央の特殊な強調ボタン)
           💡 他のボタンより上に配置（-top-6）され、録音中ならパルスアニメーションします。
        */}
        <div className="flex-1 flex justify-center h-full relative group">
          <button
            onClick={() => navigate("/record")}
            className={`absolute -top-6 w-14 h-14 rounded-full flex items-center justify-center border-4 active:scale-95 transition-all duration-300 ${
              isRecordingActive
                ? "bg-slate-900 border-cyan-400 shadow-[0_0_20px_rgba(34,211,238,0.6)] scale-105"
                : "bg-slate-900 border-slate-800 shadow-[0_0_15px_rgba(0,0,0,0.8)] hover:border-slate-700"
            }`}
            aria-label="録音"
          >
            <MicrophoneIconSolid
              className={`w-8 h-8 transition-colors ${
                isRecordingActive
                  ? "text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,1)] animate-pulse"
                  : "text-slate-400 group-hover:text-cyan-200"
              }`}
            />
          </button>
          <div className="flex flex-col justify-end pb-1 h-full pt-8">
            <span
              className={`text-[10px] font-medium transition-colors ${
                isRecordingActive
                  ? "text-cyan-400 drop-shadow-[0_0_5px_rgba(34,211,238,0.8)]"
                  : "text-slate-500 group-hover:text-cyan-400"
              }`}
            >
              録音
            </span>
          </div>
        </div>

        {/* 4. 声域分析ボタン */}
        <button
          onClick={() => navigate("/analysis")}
          className={`flex-1 flex flex-col items-center justify-end h-full py-1 ${
            currentPath === "/analysis" || currentPath === "/result"
              ? "text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.8)]"
              : "text-slate-500 hover:text-slate-400"
          }`}
        >
          <ChartBarIcon className="w-6 h-6 mb-1" />
          <span className="text-[10px] font-medium">声域分析</span>
        </button>

        {/* 5. マイページ / ログインボタン */}
        <button
          onClick={() => navigate(isAuthenticated ? "/history" : "/login")}
          className={`flex-1 flex flex-col items-center justify-end h-full py-1 ${getItemClass(isAuthenticated ? "/history" : "/login")}`}
        >
          <UserCircleIcon className="w-6 h-6 mb-1" />
          <span className="text-[10px] font-medium">
            {isAuthenticated ? "マイページ" : "ログイン"}
          </span>
        </button>
      </div>
    </div>
  );
};

// 無駄な再読み込みを防ぐためにメモ化しています
export default React.memo(BottomNav);
