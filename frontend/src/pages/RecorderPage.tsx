/**
 * 【RecorderPage.tsx】
 * 役割：音声の録音（マイクまたはカラオケ）を行うためのページです。
 * 特徴：現在のURL（/record または /karaoke）を判断して、モードを自動で切り替えます。
 */
import React from "react";
// ── 画面遷移や場所（URL）を把握するためのフック ──
import { useNavigate, useLocation } from "react-router-dom";
// 実際の録音ロジックを担当するコンポーネント
import Recorder from "../components/Recorder";
// アプリ全体の共有データを扱うためのフック
import { useAppContext } from "../contexts/AppContext";
// 解析結果の型定義
import { AnalysisResult } from "../api";

const RecorderPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  // 共有データから「結果をセットする機能」と「履歴フラグを操作する機能」を取得します
  const { setResult, setIsFromHistory } = useAppContext();
  
  /** ── モード判定 ──
   * URLが "/karaoke" であれば、カラオケ録音モード（BGM除去あり）になります。
   */
  const isKaraokeMode = location.pathname === "/karaoke";

  /** ── 解析完了時の処理 ──
   * 録音・解析が終わると、この関数が呼ばれて結果画面へ移動します。
   */
  const handleResult = (data: AnalysisResult) => {
    setResult(data);       // 解析結果をアプリ全体で共有
    setIsFromHistory(false); // 「いま録音したばかり」なので履歴フラグをOFFにする
    navigate("/result");   // 簡易結果画面へ移動
  };

  return (
    <div className="min-h-[calc(100vh-80px)] bg-transparent p-6 sm:p-8 overflow-hidden font-sans text-slate-300">
      {/* ── 戻るボタン ── */}
      <button
        onClick={() => navigate("/menu")}
        className="mb-6 text-slate-500 hover:text-cyan-400 font-bold flex items-center gap-2 transition-colors"
      >
        &larr; メニューに戻る
      </button>

      {/* ── 録音カード本体 ── */}
      <div className="max-w-3xl mx-auto bg-slate-900/80 backdrop-blur-xl p-8 sm:p-12 rounded-3xl shadow-[0_0_30px_rgba(0,0,0,0.8)] border border-slate-700/50 relative overflow-hidden">
        {/* 背景の光の装飾（グラデーション） */}
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-fuchsia-500/10 rounded-full blur-3xl pointer-events-none"></div>

        {/* ── タイトル表示 ── */}
        <h2 className="text-3xl sm:text-4xl font-black italic text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-fuchsia-400 mb-8 text-center drop-shadow-[0_0_8px_rgba(34,211,238,0.8)] tracking-wider">
          {isKaraokeMode ? "KARAOKE RECORDING" : "MIC RECORDING"}
        </h2>

        {/* ── 録音機（Recorder）の呼び出し ──
           💡 isKaraokeMode に応じて Demucs（AIによる伴奏除去）を使うかどうかを決めます。
        */}
        <Recorder onResult={handleResult} initialUseDemucs={isKaraokeMode} />
      </div>
    </div>
  );
};

export default RecorderPage;