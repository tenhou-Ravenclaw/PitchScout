/**
 * 【HomePage.tsx】
 * 役割：トップ画面で Vocal Range Analysis の要点を表示します。
 * 特徴：Analysis と同じ音域カードを再利用し、録音メニューへの導線を配置します。
 */
import React from "react";
import {
  MicrophoneIcon,
  QuestionMarkCircleIcon,
} from "@heroicons/react/24/solid";
import { AnalysisResult } from "../api";
import { useIntegratedRangeDisplay } from "../hooks/useIntegratedRangeDisplay";
import VocalRangeAnalysisCard from "../components/ui/cards/VocalRangeAnalysisCard";
import logo from "../assets/logo.png";

/** HomePage が外から受け取るプロパティ */
interface HomePageProps {
  /** 解析結果データ */
  result: AnalysisResult | null;
  /** ログイン中かどうか */
  isAuthenticated: boolean;
  /** 録音ページへ進むボタン押下時の処理 */
  onRecordClick: () => void;
  /** 使い方ガイドへ進むボタン押下時の処理 */
  onGuideClick: () => void;
  /** 履歴ページへ進むボタン押下時の処理 */
  onHistoryClick: () => void;
  /** お気に入りページへ進むボタン押下時の処理 */
  onFavoritesClick: () => void;
  /** 検索ボックスの初期値 */
  initialSearchQuery: string;
  /** 検索実行時の処理 */
  onSearchSubmit: (query: string) => void;
  /** 表示するユーザー名 */
  userName: string | null;
  /** ログアウトボタン押下時の処理 */
  onLogoutClick: () => void;
}

const HomePage: React.FC<HomePageProps> = ({
  result,
  isAuthenticated,
  onRecordClick,
  onGuideClick,
  onHistoryClick,
  onFavoritesClick,
  initialSearchQuery,
  onSearchSubmit,
  userName,
  onLogoutClick,
}) => {
  const [searchInput, setSearchInput] =
    React.useState<string>(initialSearchQuery);

  React.useEffect(() => {
    setSearchInput(initialSearchQuery);
  }, [initialSearchQuery]);

  const { displayData } = useIntegratedRangeDisplay({
    result,
    isAuthenticated,
    limit: 20,
  });

  const hasDisplayData = !!displayData && !displayData.error;

  return (
    <div className="min-h-[calc(100vh-80px)] bg-transparent p-4 sm:p-8 font-sans text-slate-200">
      <div className="w-full max-w-6xl mx-auto space-y-4">
        <div className="flex items-end gap-4 px-1">
          <img
            src={logo}
            alt="PitchScout Logo"
            className="w-12 h-12 sm:w-14 sm:h-14 md:w-20 md:h-20 lg:w-24 lg:h-24 rounded-lg shadow-lg object-cover shrink-0"
          />
          <h1 className="inline-block text-3xl sm:text-4xl md:text-6xl lg:text-7xl leading-none font-black italic text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-fuchsia-400 to-fuchsia-400 drop-shadow-[0_0_15px_rgba(255,255,255,0.3)] tracking-wide">
            PitchScout
          </h1>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-3">
          <div className="lg:col-span-2">
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  onSearchSubmit(searchInput);
                }
              }}
              placeholder="曲名・アーティスト名で検索（Enterで実行）"
              aria-label="楽曲検索"
              className="w-full rounded-xl px-4 py-4 bg-slate-800/80 border border-slate-700 text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
            />
          </div>

          <button
            type="button"
            onClick={() => onSearchSubmit(searchInput)}
            className="w-full btn-primary-cyan rounded-xl px-6 py-4 text-base sm:text-lg font-bold"
          >
            検索
          </button>

          <button
            type="button"
            onClick={onGuideClick}
            className="w-full rounded-xl px-6 py-4 text-base sm:text-lg font-bold inline-flex items-center justify-center gap-2 border border-cyan-500/40 bg-slate-900/60 hover:bg-slate-800/70 transition-colors"
          >
            <QuestionMarkCircleIcon className="w-6 h-6 text-cyan-400" />
            使い方ガイド
          </button>
        </div>

        {hasDisplayData ? (
          <VocalRangeAnalysisCard
            data={displayData}
            topRightContent={
              isAuthenticated ? (
                <div className="flex flex-col items-end gap-1">
                  <p className="text-xs sm:text-sm text-slate-300 font-medium">
                    ログイン中: {userName || "ユーザー"}
                  </p>
                  <button
                    type="button"
                    onClick={onLogoutClick}
                    className="text-xs text-slate-300 hover:text-rose-400 border border-slate-600 hover:border-rose-500/50 rounded-lg px-3 py-1.5 transition-colors"
                  >
                    ログアウト
                  </button>
                </div>
              ) : undefined
            }
          />
        ) : (
          <div className="flex flex-col items-center justify-center min-h-[28vh] text-slate-400 p-8 bg-slate-900/60 backdrop-blur-md rounded-3xl border border-white/10">
            <div className="text-4xl mb-3">🎤</div>
            <p className="text-base font-bold mb-1">分析データがありません</p>
            <p className="text-sm">
              録音して解析を完了すると、ここに音域結果が表示されます。
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <button
            type="button"
            onClick={onRecordClick}
            className="w-full btn-primary-cyan rounded-xl px-6 py-4 text-base sm:text-lg font-bold inline-flex items-center justify-center gap-2"
          >
            <MicrophoneIcon className="w-6 h-6" />
            録音
          </button>

          <button
            type="button"
            onClick={onFavoritesClick}
            className="w-full rounded-xl px-6 py-4 text-base sm:text-lg font-bold inline-flex items-center justify-center border border-cyan-500/40 bg-slate-900/60 hover:bg-slate-800/70 transition-colors"
          >
            お気に入り
          </button>

          <button
            type="button"
            onClick={onHistoryClick}
            className="w-full rounded-xl px-6 py-4 text-base sm:text-lg font-bold inline-flex items-center justify-center border border-cyan-500/40 bg-slate-900/60 hover:bg-slate-800/70 transition-colors"
          >
            履歴
          </button>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
