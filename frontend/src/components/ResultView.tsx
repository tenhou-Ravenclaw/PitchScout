import React from "react";
import { AnalysisResult } from "../api";

interface Props {
  result: AnalysisResult;
}

/* ───── helpers ───── */
const fmtHz = (hz: number) => `${Math.round(hz)} Hz`;
const fmtNote = (label: string | undefined) => label || "—";

/* ───── score → color ───── */
const scoreColor = (score: number) => {
  if (score >= 80) return "text-emerald-500";
  if (score >= 60) return "text-sky-500";
  if (score >= 40) return "text-amber-500";
  return "text-rose-400";
};
const scoreBg = (score: number) => {
  if (score >= 80) return "bg-emerald-500";
  if (score >= 60) return "bg-sky-500";
  if (score >= 40) return "bg-amber-500";
  return "bg-rose-400";
};
const scoreRank = (score: number) => {
  if (score >= 90) return "S";
  if (score >= 80) return "A";
  if (score >= 65) return "B";
  if (score >= 50) return "C";
  return "D";
};

/* ════════════════════════════════════════════════
   Main Component
   ════════════════════════════════════════════════ */
const ResultView: React.FC<Props> = ({ result }) => {
  if (result.error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-4">
        <div className="w-16 h-16 rounded-full bg-rose-900/30 flex items-center justify-center mb-4 border border-rose-500/30">
          <svg className="w-8 h-8 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        <p className="text-slate-400 text-center max-w-md">{result.error}</p>
      </div>
    );
  }

  const hasChest = result.chest_min != null;
  const hasFalsetto = result.falsetto_min != null;
  const analysis = result.singing_analysis;
  const songs = result.recommended_songs ?? [];
  const artists = result.similar_artists ?? [];
  const voiceType = result.voice_type ?? {};

  return (
    <div className="space-y-6">

      {/* ──── 1. Voice Type Badge + Overall Range ──── */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-500 via-blue-500 to-sky-400 p-6 text-white">
        <div className="absolute -top-10 -right-10 w-40 h-40 rounded-full bg-white/10" />
        <div className="absolute -bottom-6 -left-6 w-28 h-28 rounded-full bg-white/5" />

        <div className="relative z-10">
          {voiceType.voice_type && (
            <div className="inline-block bg-white/20 backdrop-blur-sm rounded-full px-3 py-1 text-xs font-semibold tracking-wide mb-3">
              {voiceType.range_class} ・ {voiceType.voice_type}
            </div>
          )}

          <h2 className="text-sm font-medium text-white/70 mb-1">あなたの音域</h2>
          <div className="flex items-baseline gap-3 flex-wrap">
            <span className="text-3xl sm:text-4xl font-extrabold tracking-tight">
              {fmtNote(result.overall_min)}
            </span>
            <span className="text-xl text-white/50">〜</span>
            <span className="text-3xl sm:text-4xl font-extrabold tracking-tight">
              {fmtNote(result.overall_max)}
            </span>
          </div>
          <p className="text-xs text-white/50 mt-1">
            {fmtHz(result.overall_min_hz)} 〜 {fmtHz(result.overall_max_hz)}
          </p>

          {voiceType.description && (
            <p className="text-sm text-white/80 mt-4 leading-relaxed max-w-lg">
              {voiceType.description}
            </p>
          )}
        </div>
      </div>

      {/* ──── 2. Chest / Falsetto Ratio Bar ──── */}
      {result.chest_ratio !== undefined && (
        <div className="bg-slate-900/60 backdrop-blur-md rounded-xl p-5 shadow-xl border border-white/10">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">声区バランス</h3>
          <div className="w-full h-3 bg-slate-800 rounded-full overflow-hidden flex border border-white/5">
            <div
              className="h-full bg-indigo-500 transition-all duration-700 opacity-90"
              style={{ width: `${result.chest_ratio}%` }}
            />
            <div
              className="h-full bg-emerald-400 transition-all duration-700 opacity-90"
              style={{ width: `${result.falsetto_ratio}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-slate-400 mt-2">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 bg-indigo-500 rounded-full inline-block" />
              地声 {result.chest_ratio}%
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 bg-emerald-400 rounded-full inline-block" />
              裏声 {result.falsetto_ratio}%
            </span>
          </div>
        </div>
      )}

      {/* ──── 3. Range Detail Cards ──── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {hasChest && (
          <div className="bg-slate-900/60 backdrop-blur-md rounded-xl p-5 shadow-xl border border-white/10">
            <div className="flex items-center gap-2 mb-3">
              <span className="w-2.5 h-2.5 bg-indigo-500 rounded-full shadow-[0_0_5px_rgba(99,102,241,0.8)]" />
              <h3 className="text-sm font-bold text-slate-200">地声</h3>
              <span className="text-xs text-slate-500 ml-auto">{result.chest_count}フレーム</span>
            </div>
            <div className="space-y-1.5">
              <div className="flex justify-between items-baseline">
                <span className="text-xs text-slate-400">最低音</span>
                <span className="font-bold text-slate-300">
                  {fmtNote(result.chest_min)}{" "}
                  <span className="text-xs text-slate-500 font-normal">
                    {result.chest_min_hz !== undefined && fmtHz(result.chest_min_hz)}
                  </span>
                </span>
              </div>
              <div className="flex justify-between items-baseline">
                <span className="text-xs text-slate-400">最高音</span>
                <span className="font-bold text-slate-300">
                  {fmtNote(result.chest_max)}{" "}
                  <span className="text-xs text-slate-500 font-normal">
                    {result.chest_max_hz !== undefined && fmtHz(result.chest_max_hz)}
                  </span>
                </span>
              </div>
            </div>
          </div>
        )}
        {hasFalsetto && (
          <div className="bg-slate-900/60 backdrop-blur-md rounded-xl p-5 shadow-xl border border-white/10">
            <div className="flex items-center gap-2 mb-3">
              <span className="w-2.5 h-2.5 bg-emerald-400 rounded-full shadow-[0_0_5px_rgba(52,211,153,0.8)]" />
              <h3 className="text-sm font-bold text-slate-200">裏声</h3>
              <span className="text-xs text-slate-500 ml-auto">{result.falsetto_count}フレーム</span>
            </div>
            <div className="space-y-1.5">
              <div className="flex justify-between items-baseline">
                <span className="text-xs text-slate-400">最低音</span>
                <span className="font-bold text-slate-300">
                  {fmtNote(result.falsetto_min)}{" "}
                  <span className="text-xs text-slate-500 font-normal">
                    {result.falsetto_min_hz !== undefined && fmtHz(result.falsetto_min_hz)}
                  </span>
                </span>
              </div>
              <div className="flex justify-between items-baseline">
                <span className="text-xs text-slate-400">最高音</span>
                <span className="font-bold text-slate-300">
                  {fmtNote(result.falsetto_max)}{" "}
                  <span className="text-xs text-slate-500 font-normal">
                    {result.falsetto_max_hz !== undefined && fmtHz(result.falsetto_max_hz)}
                  </span>
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ──── 4. Singing Analysis Scores ──── */}
      {analysis && (
        <div className="bg-slate-900/60 backdrop-blur-md rounded-xl p-5 shadow-xl border border-white/10">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-200">歌唱力スコア</h3>
            <div className="flex items-center gap-1.5">
              <span className={`text-2xl font-black ${scoreColor(analysis.overall_score)} drop-shadow-sm`}>
                {scoreRank(analysis.overall_score)}
              </span>
              <span className="text-xs text-slate-500">ランク</span>
            </div>
          </div>

          <div className="space-y-3">
            {[
              { label: "総合", value: analysis.overall_score },
              {
                label: `音域の広さ (${analysis.range_semitones}半音)`,
                value: analysis.range_score,
              },
              { label: "ピッチ安定性", value: analysis.stability_score },
              { label: "表現力", value: analysis.expression_score },
            ].map(({ label, value }) => (
              <div key={label}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400 font-medium">{label}</span>
                  <span className={`font-bold ${scoreColor(value)}`}>
                    {Math.round(value)}
                  </span>
                </div>
                <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden border border-white/5">
                  <div
                    className={`h-full rounded-full transition-all duration-1000 ${scoreBg(value)}`}
                    style={{ width: `${value}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ──── 5. Similar Artists ──── */}
      {artists.length > 0 && (
        <div className="bg-slate-900/60 backdrop-blur-md rounded-xl p-5 shadow-xl border border-white/10">
          <h3 className="text-sm font-bold text-slate-200 mb-3">声が似ているアーティスト</h3>
          <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1">
            {artists.map((a, i) => (
              <div
                key={a.id}
                className="flex-shrink-0 w-28 flex flex-col items-center text-center"
              >
                <div
                  className={`w-14 h-14 rounded-full flex items-center justify-center text-white font-bold text-lg shadow-md ring-2 ring-white/10 ${
                    i === 0
                      ? "bg-gradient-to-br from-amber-400 to-orange-500"
                      : i === 1
                      ? "bg-gradient-to-br from-slate-500 to-slate-600"
                      : "bg-gradient-to-br from-blue-500 to-indigo-600"
                  }`}
                >
                  {a.name.charAt(0)}
                </div>
                <span className="text-xs font-bold text-slate-300 mt-2 leading-tight line-clamp-2">
                  {a.name}
                </span>
                <span className="text-[10px] text-slate-500 mt-0.5">
                  {a.typical_lowest}〜{a.typical_highest}
                </span>
                <span className="text-[10px] text-indigo-400 font-semibold drop-shadow-sm">
                  {a.similarity_score}%一致
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ──── 6. Recommended Songs ──── */}
      {songs.length > 0 && (
        <div className="bg-slate-900/60 backdrop-blur-md rounded-xl p-5 shadow-xl border border-white/10">
          <h3 className="text-sm font-bold text-slate-200 mb-1">おすすめの曲</h3>
          <p className="text-xs text-slate-500 mb-4">あなたの音域に合った楽曲</p>

          <div className="space-y-1">
            {songs.map((song, i) => {
              const matchColor =
                song.match_score >= 95 ? "bg-emerald-900/50 text-emerald-400 border border-emerald-500/30" :
                  song.match_score >= 80 ? "bg-sky-900/50 text-sky-400 border border-sky-500/30" :
                    song.match_score >= 60 ? "bg-amber-900/50 text-amber-400 border border-amber-500/30" :
                      "bg-slate-800 text-slate-400 border border-slate-700";

              return (
                <div
                  key={song.id}
                  className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-white/5 transition-colors group"
                >
                  <span className="w-6 text-center text-sm font-bold text-slate-500 group-hover:text-cyan-400 transition-colors">
                    {i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-bold text-slate-200 truncate">
                      {song.title}
                    </div>
                    <div className="text-xs text-slate-500 truncate">
                      {song.artist}
                    </div>
                  </div>
                  <div className="hidden sm:block text-xs text-slate-500 whitespace-nowrap">
                    {song.lowest_note}〜{song.highest_note}
                  </div>
                  {song.recommended_key !== undefined && (
                    <span
                      className={`text-[11px] font-bold px-2 py-0.5 rounded-full whitespace-nowrap border ${
                        song.fit === "perfect"
                          ? "bg-emerald-900/30 text-emerald-400 border-emerald-500/30"
                          : song.fit === "good"
                          ? "bg-sky-900/30 text-sky-400 border-sky-500/30"
                          : song.fit === "ok"
                          ? "bg-amber-900/30 text-amber-400 border-amber-500/30"
                          : "bg-slate-800 text-slate-500 border-slate-700"
                      }`}
                    >
                      {song.recommended_key === 0
                        ? "±0"
                        : song.recommended_key > 0
                        ? `+${song.recommended_key}`
                        : `${song.recommended_key}`}
                    </span>
                  )}
                  <span
                    className={`text-[11px] font-bold px-2 py-0.5 rounded-full whitespace-nowrap ${matchColor}`}
                  >
                    {Math.round(song.match_score)}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {!hasChest && !hasFalsetto && (
        <div className="text-center py-8 text-slate-500">
          <p>声の種類を判定できませんでした。</p>
          <p className="text-sm">もう少し長く録音してみてください。</p>
        </div>
      )}
    </div>
  );
};

export default React.memo(ResultView);
