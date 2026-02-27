/**
 * 【AnalysisResultPage.tsx】
 * 役割：歌声の解析結果を詳細に表示するメインページです。
 * 特徴：レーダーチャート、おすすめ曲、似ているアーティストなど、リッチなUIを提供します。
 */

import React, { useState, useEffect } from "react";
import { RadarChart } from "../components/ui/RadarChart";
import {
  AnalysisResult,
  IntegratedVocalRange,
  getIntegratedVocalRange,
  toUserMessage,
} from "../api"; // API通信用の型定義と関数をインポート
import { StarIcon as StarSolid } from "@heroicons/react/24/solid";
import { StarIcon as StarOutline } from "@heroicons/react/24/outline";
import { useToast } from "../hooks/useToast";
import { useFavoriteArtists } from "../hooks/useFavoriteArtists";
import Toast from "../components/ui/Toast";
import { keyBadge } from "../utils/keyBadge";

/** ページが外部（AnalysisRouteなど）から受け取るプロパティの定義 */
interface AnalysisResultPageProps {
  /** 解析結果データ */
  result: AnalysisResult | null;
  /** ログイン中かどうか */
  isAuthenticated: boolean;
}

/**
 * AnalysisResult にエラーが含まれるかを判定します。
 * @param data - 判定対象のデータ
 * @returns エラーが含まれる場合は true
 */
const hasAnalysisError = (
  data: AnalysisResult | IntegratedVocalRange | null,
): data is AnalysisResult & { error: string } => {
  return !!data && "error" in data && typeof data.error === "string" && data.error.length > 0;
};

/* ───── 歌唱力レーダーチャート (SVG) ───── 
 * 音域、安定性、表現力などのスコアを多角形で視覚化します。
 */

/* ════════════════════════════════════════════════
   メインコンポーネント本体
   ════════════════════════════════════════════════ */
const AnalysisResultPage: React.FC<AnalysisResultPageProps> = ({ result, isAuthenticated }) => {
  const { toggleFavorite, isFavorite } = useFavoriteArtists(); // お気に入りアーティスト管理
  const [integratedRange, setIntegratedRange] = useState<IntegratedVocalRange | null>(null); // 直近N件をまとめた総合的な音域
  const [loadingIntegrated, setLoadingIntegrated] = useState(false);
  const { toastMessage, showToast, hideToast } = useToast();

  /**
   * ── ログイン中のみ実行: 過去の履歴をまとめた「統合音域」を取得 ──
   * 💡 これにより、一回の録音ミスの影響を受けない正確な音域を表示できます。
   */
  useEffect(() => {
    const fetchIntegratedRange = async () => {
      if (!isAuthenticated) return;
      setLoadingIntegrated(true);
      try {
        const data = await getIntegratedVocalRange(20); // 直近20件をベースに計算
        setIntegratedRange(data);
      } catch (e) {
        showToast(toUserMessage(e, "統合音域の取得に失敗しました"));
        setIntegratedRange(null);
      } finally {
        setLoadingIntegrated(false);
      }
    };
    fetchIntegratedRange();
  }, [isAuthenticated, showToast]);

  /**
   * ── ロード中の表示設定 ──
   */
  if (isAuthenticated && loadingIntegrated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-slate-400 p-8">
        <div className="text-4xl mb-4">⏳</div>
        <p className="text-lg font-bold">統合音域を計算中...</p>
      </div>
    );
  }

  /**
   * ── 表示するデータの選択ロジック ──
   * ログイン済みで統合データがある場合はそれを、なければ今回の単発結果(result)を使います。
   */
  const useIntegrated = isAuthenticated && integratedRange;
  const displayData = useIntegrated ? integratedRange : result;

  // データがどこにも存在しない場合のエラー表示
  if (!displayData || hasAnalysisError(displayData)) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-slate-400 p-8">
        <div className="text-6xl mb-4">🎤</div>
        <p className="text-lg font-bold mb-2">分析データがありません</p>
        <p className="text-sm">録音して解析を完了させると、ここに結果が表示されます。</p>
      </div>
    );
  }

  // ── レーダーチャート用データの整形 ──
  const singing = displayData.singing_analysis;
  const radarData = singing ? [
    { label: "音域", value: singing.range_score },
    { label: "安定性", value: singing.stability_score },
    { label: "表現力", value: singing.expression_score },
    { label: "総合", value: singing.overall_score },
  ] : [];

  const songs = displayData.recommended_songs ?? [];
  const artists = displayData.similar_artists ?? [];
  const voiceType = displayData.voice_type ?? {};

  return (
    <div className="flex flex-col items-center w-full min-h-screen bg-transparent p-4 sm:p-8 font-sans text-slate-200">
      <div className="w-full max-w-6xl">

        {/* ── 統合音域バッジ（ログイン時のみ表示） ── */}
        {useIntegrated && (
          <div className="mb-6 flex justify-center">
            <div className="inline-flex bg-slate-900/60 backdrop-blur-md rounded-full px-6 py-3 border border-cyan-500/30">
              <span className="text-sm font-medium text-cyan-400">
                📊 統合音域（直近 {integratedRange!.data_count} 曲から算出）
              </span>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* ── 左カラム: 音域とボイスタイプ ── */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-slate-900/60 backdrop-blur-md rounded-3xl shadow-xl border border-white/10 p-6 sm:p-8">
              <h2 className="text-sm font-bold text-slate-500 uppercase tracking-widest mb-6">Vocal Range Analysis</h2>

              <div className="flex items-baseline gap-4 mb-8">
                <span className="text-4xl sm:text-6xl font-black text-white tracking-tighter">
                  {displayData.overall_min} <span className="text-slate-600 mx-1">~</span> {displayData.overall_max}
                </span>
              </div>

              {/* 地声・裏声の内訳 */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
                <div className="bg-indigo-900/30 p-4 rounded-2xl border border-indigo-500/30">
                  <p className="text-xs font-bold text-indigo-400 mb-1">地声範囲 (Chest)</p>
                  <p className="text-xl font-bold text-slate-100">{displayData.chest_min ?? displayData.overall_min} ~ {displayData.chest_max ?? displayData.overall_max}</p>
                </div>
                {displayData.falsetto_max && (
                  <div className="bg-emerald-900/30 p-4 rounded-2xl border border-emerald-500/30">
                    <p className="text-xs font-bold text-emerald-400 mb-1">裏声最高音 (Falsetto)</p>
                    <p className="text-xl font-bold text-slate-100">{displayData.falsetto_max}</p>
                  </div>
                )}
              </div>

              {/* 声の種類（タイプ）診断 */}
              {voiceType && voiceType.voice_type && (
                <div className="p-5 bg-slate-800/50 rounded-2xl border border-slate-700/50">
                  <p className="text-sm font-bold text-slate-200 mb-1">
                    タイプ: <span className="text-cyan-400">{voiceType.voice_type}</span>
                  </p>
                  <p className="text-xs text-slate-400 leading-relaxed">{voiceType.description}</p>
                </div>
              )}
            </div>

            {/* ── 似ているアーティスト ── */}
            {artists && artists.length > 0 && (
              <div className="bg-slate-900/60 backdrop-blur-md rounded-3xl shadow-xl border border-white/10 p-6">
                <h3 className="text-sm font-bold text-slate-200 mb-4">声質が似ているアーティスト</h3>
                <div className="flex flex-wrap gap-3">
                  {artists.map((artist) => (
                    <div key={artist.id} className="flex items-center gap-3 bg-slate-800/50 pl-4 pr-2 py-2 rounded-full border border-slate-700/50 group transition-all hover:bg-slate-700/50 hover:border-slate-600/50">
                      <span className="text-sm font-bold text-slate-200">{artist.name}</span>
                      <span className="text-[10px] font-bold text-indigo-400">{Math.round(artist.similarity_score)}%</span>
                      <button
                        onClick={() => toggleFavorite(artist.id, artist.name)}
                        className="p-1.5 transition-transform hover:scale-125"
                        aria-label="お気に入り登録"
                      >
                        {isFavorite(artist.id) ? (
                          <StarSolid className="w-5 h-5 text-amber-400" />
                        ) : (
                          <StarOutline className="w-5 h-5 text-slate-500" />
                        )}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* ── 右カラム: スコア指標とおすすめ曲 ── */}
          <div className="space-y-6">
            <div className="bg-slate-900/60 backdrop-blur-md rounded-3xl shadow-xl border border-white/10 p-6 flex flex-col items-center">
              <h3 className="text-sm font-bold text-slate-200 self-start mb-4">歌唱力指標</h3>
              {radarData.length > 0 ? (
                <div className="w-full flex flex-col items-center">
                  <RadarChart data={radarData} />
                  <div className="mt-4 text-center">
                    <div className="text-3xl font-black text-indigo-400">{Math.round(singing?.overall_score ?? 0)}点</div>
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Singing Score</p>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-slate-500 py-10">スコアデータがありません</p>
              )}
            </div>

            <div className="bg-slate-900/60 backdrop-blur-md rounded-3xl shadow-xl border border-white/10 p-6">
              <h3 className="text-sm font-bold text-slate-200 mb-4">あなたへのおすすめ曲</h3>
              <div className="space-y-3">
                {songs.slice(0, 5).map((song, i) => (
                  <div key={song.id} className="flex items-center justify-between group">
                    <div className="min-w-0">
                      <p className="text-sm font-bold text-slate-200 truncate">{song.title}</p>
                      <p className="text-[10px] text-slate-500 truncate">{song.artist}</p>
                    </div>
                    <div className="flex gap-2 flex-shrink-0 ml-2">
                      {/* キーバッジ部品の呼び出し */}
                      {song.recommended_key !== undefined && keyBadge(song.recommended_key, song.fit)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* Toast通知 */}
      {toastMessage && (
        <Toast message={toastMessage} onClose={hideToast} />
      )}
    </div>
  );
};

export default AnalysisResultPage;