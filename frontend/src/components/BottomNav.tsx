import React from "react";
import { useNavigate } from "react-router-dom";
import {
  MusicalNoteIcon,
  HeartIcon,
  ChartBarIcon,
  UserCircleIcon,
} from "@heroicons/react/24/outline";
import { MicrophoneIcon as MicrophoneIconSolid } from "@heroicons/react/24/solid";

interface BottomNavProps {
  currentPath: string;
  isAuthenticated?: boolean;
}

const RECORDING_PATHS = new Set(["/menu", "/record", "/karaoke", "/upload"]);

const BottomNav: React.FC<BottomNavProps> = ({ currentPath, isAuthenticated = false }) => {
  const navigate = useNavigate();

  const getItemClass = (path: string) =>
    currentPath === path
      ? "text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.8)]"
      : "text-slate-500 hover:text-slate-400";

  const isRecordingActive = RECORDING_PATHS.has(currentPath);

  return (
    <div className="md:hidden fixed bottom-0 left-0 w-full bg-slate-950 border-t border-slate-800 shadow-[0_-5px_20px_rgba(0,0,0,0.5)] z-50 px-2 pb-safe">
      <div className="flex justify-between items-end h-16 pb-2">

        {/* 1. 楽曲一覧 */}
        <button
          onClick={() => navigate("/songs")}
          className={`flex-1 flex flex-col items-center justify-end h-full py-1 ${getItemClass("/songs")}`}
        >
          <MusicalNoteIcon className="w-6 h-6 mb-1" />
          <span className="text-[10px] font-medium">アーティスト</span>
        </button>

        {/* 2. お気に入り */}
        <button
          onClick={() => navigate("/favorites")}
          className={`flex-1 flex flex-col items-center justify-end h-full py-1 ${getItemClass("/favorites")}`}
        >
          <HeartIcon className="w-6 h-6 mb-1" />
          <span className="text-[10px] font-medium">お気に入り</span>
        </button>

        {/* 3. 録音 (Center - Special) */}
        <div className="flex-1 flex justify-center h-full relative group">
          <button
            onClick={() => navigate("/menu")}
            className={`absolute -top-6 w-14 h-14 rounded-full flex items-center justify-center border-4 active:scale-95 transition-all duration-300 ${isRecordingActive
              ? "bg-slate-900 border-cyan-400 shadow-[0_0_20px_rgba(34,211,238,0.6)] scale-105"
              : "bg-slate-900 border-slate-800 shadow-[0_0_15px_rgba(0,0,0,0.8)] hover:border-slate-700"
              }`}
            aria-label="録音"
          >
            <MicrophoneIconSolid className={`w-8 h-8 transition-colors ${isRecordingActive
              ? "text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,1)] animate-pulse"
              : "text-slate-400 group-hover:text-cyan-200"
              }`} />
          </button>
          <div className="flex flex-col justify-end pb-1 h-full pt-8">
            <span
              className={`text-[10px] font-medium transition-colors ${isRecordingActive
                ? "text-cyan-400 drop-shadow-[0_0_5px_rgba(34,211,238,0.8)]"
                : "text-slate-500 group-hover:text-cyan-400"
                }`}
            >
              録音
            </span>
          </div>
        </div>

        {/* 4. 声域分析 */}
        <button
          onClick={() => navigate("/analysis")}
          className={`flex-1 flex flex-col items-center justify-end h-full py-1 ${currentPath === "/analysis" || currentPath === "/result"
            ? "text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.8)]"
            : "text-slate-500 hover:text-slate-400"
            }`}
        >
          <ChartBarIcon className="w-6 h-6 mb-1" />
          <span className="text-[10px] font-medium">声域分析</span>
        </button>

        {/* 5. マイページ / ログイン */}
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

export default React.memo(BottomNav);
