/**
 * 【Recorder.tsx】
 * 役割：ブラウザからマイクを使って録音し、声をリアルタイムで波形表示し、解析サーバーへ送信します。
 * 非常に高度な「音声処理」と「ビジュアライザー（視覚化）」が詰まったファイルです。
 * * 💡 設計図（FRONTEND_STRUCTURE.md）に基づく移動案：
 * 1. 移動先: src/features/karaoke/components/Recorder.tsx
 */

import React, { useState, useRef, useEffect, useCallback } from "react";
// 通信用の関数と、録音ページ用のスタイルを読み込み
import { analyzeVoice, analyzeKaraoke, AnalysisResult } from "../api";
import { MicrophoneIcon, StopIcon } from "@heroicons/react/24/solid";
import "./Recorder.css";
// 解析の状態（進捗など）を管理するコンテキストを使用
import { useAnalysis } from '../contexts/AnalysisContext';

interface Props {
  onResult: (data: AnalysisResult) => void; // 解析が終わった時に呼ばれる関数
  initialUseDemucs?: boolean;                // カラオケ録音モード（BGM除去）かどうか
}

const Recorder: React.FC<Props> = ({ onResult, initialUseDemucs = false }) => {
  // ── 状態管理 (State) ──
  const [recording, setRecording] = useState(false); // 録音中かどうか
  // 分析コンテキストから必要な情報をもらってくる
  const {
    isAnalyzing: loading, setIsAnalyzing: setLoading,
    progress, setProgress,
    stepLabel, setStepLabel,
    startAnalysisTimer, stopAnalysisTimer
  } = useAnalysis();

  const [noFalsetto, setNoFalsetto] = useState(false); // 「裏声なし」設定

  // ── 参照 (Refs) ──
  // 【ポイント】useRef は「画面の書き換え（再描画）」を発生させずに値を保持したい時に使います。
  // 音声処理のように、1秒間に何十回も値が変わるものは ref で管理します。
  const mediaRecorder = useRef<MediaRecorder | null>(null); // ブラウザの録音機
  const chunks = useRef<Blob[]>([]);                        // 録音データの断片

  // ビジュアライザー（波形表示）用の参照
  const canvasRef = useRef<HTMLCanvasElement>(null);         // 描画するキャンバス
  const audioContextRef = useRef<AudioContext | null>(null); // 音声処理の土台
  const analyserRef = useRef<AnalyserNode | null>(null);     // 周波数分析器
  const dataArrayRef = useRef<Uint8Array | null>(null);      // 周波数データの入れ物
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const animationIdRef = useRef<number | null>(null);        // アニメーションの停止用ID
  const streamRef = useRef<MediaStream | null>(null);        // マイクからの音声ストリーム
  const gradientRef = useRef<CanvasGradient | null>(null);   // 波形の色付け（グラデーション）

  /**
   * ── クリーンアップ処理 ──
   * コンポーネントが消える時に、マイクを止めたりメモリを解放したりします。
   */
  useEffect(() => {
    return () => {
      if (animationIdRef.current) cancelAnimationFrame(animationIdRef.current);
      if (mediaRecorder.current && mediaRecorder.current.state !== "inactive") mediaRecorder.current.stop();
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
      if (sourceRef.current) { sourceRef.current.disconnect(); sourceRef.current = null; }
      if (audioContextRef.current) { audioContextRef.current.close(); audioContextRef.current = null; }
    };
  }, []);

  /**
   * ── ビジュアライザー描画関数 ──
   * 音声データを元に、リアルタイムでキャンバスに棒グラフ（波形）を描きます。
   */
  const drawVisualizer = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !analyserRef.current || !dataArrayRef.current) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const WIDTH = canvas.width;
    const HEIGHT = canvas.height;

    // 現在の音の周波数データを取得
    analyserRef.current.getByteFrequencyData(dataArrayRef.current as any);

    // 一度キャンバスをクリア
    ctx.clearRect(0, 0, WIDTH, HEIGHT);

    // グラデーションの設定（青〜紫）
    if (!gradientRef.current) {
      const gradient = ctx.createLinearGradient(0, HEIGHT, 0, 0);
      gradient.addColorStop(0, "#38bdf8");
      gradient.addColorStop(1, "#a78bfa");
      gradientRef.current = gradient;
    }
    ctx.fillStyle = gradientRef.current;

    // データの描画（棒グラフ）
    const totalBins = dataArrayRef.current.length;
    const maxBinIndex = Math.floor(totalBins * 0.4); // 高音域すぎるところはカット
    const barCount = 80;
    const barWidth = (WIDTH / barCount) * 0.8;
    const gap = (WIDTH / barCount) * 0.2;
    let x = 0;

    for (let i = 0; i < barCount; i++) {
      const percent = i / barCount;
      const indexMapping = Math.pow(percent, 2.0); // 低音側を強調
      const rawIndex = Math.floor(indexMapping * maxBinIndex);
      const valueIndex = Math.min(rawIndex, totalBins - 1);
      const v = dataArrayRef.current[valueIndex];
      const barHeight = Math.max((v / 255) * HEIGHT * 0.95, 5);
      ctx.fillRect(x, HEIGHT - barHeight, barWidth, barHeight);
      x += barWidth + gap;
    }

    // 次のフレームを描画予約（ループ）
    animationIdRef.current = requestAnimationFrame(drawVisualizer);
  }, []);

  /**
   * ── 録音開始 ──
   * マイクの使用許可を取り、データの収集を始めます。
   */
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      mediaRecorder.current = new MediaRecorder(stream);
      chunks.current = [];

      // 音声データが溜まるたびに配列に追加
      mediaRecorder.current.ondataavailable = (e) => {
        chunks.current.push(e.data);
      };

      // 録音が止まった時の処理（サーバーへ送信）
      mediaRecorder.current.onstop = async () => {
        if (animationIdRef.current) cancelAnimationFrame(animationIdRef.current);
        const blob = new Blob(chunks.current, { type: "audio/webm" });

        // 解析タイマーの開始
        if (initialUseDemucs) {
          startAnalysisTimer('karaoke_record');
        } else {
          startAnalysisTimer('mic_record');
        }

        try {
          // サーバーに送信して解析結果を待つ
          const data = initialUseDemucs
            ? await analyzeKaraoke(blob, "recording.webm", noFalsetto)
            : await analyzeVoice(blob, noFalsetto);

          stopAnalysisTimer();
          setProgress(100);
          setStepLabel("完了！");
          onResult(data);
        } catch (err: unknown) {
          // エラー時のメッセージ処理
          stopAnalysisTimer();
          const axiosErr = err as { code?: string; message?: string; response?: { data?: { error?: string } } };
          let errorMsg: string;
          if (axiosErr?.message?.includes("timeout")) {
            errorMsg = "⏱️ 処理時間が10分を超えたため、タイムアウトしました。もう一度お試しください。";
          } else if (axiosErr?.code === "ECONNABORTED" || axiosErr?.message?.includes("Network Error")) {
            errorMsg = "ネットワークエラーが発生しました。サーバーに接続できない可能性があります。";
          } else {
            errorMsg = axiosErr?.response?.data?.error || axiosErr?.message || "解析に失敗しました。";
          }
          onResult({ error: errorMsg } as AnalysisResult);
        } finally {
          setTimeout(() => {
            setLoading(false);
            setProgress(0);
            setStepLabel("");
          }, 500);
        }
      };

      // 音声分析の準備
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
      }

      const audioCtx = audioContextRef.current;
      analyserRef.current = audioCtx.createAnalyser();
      analyserRef.current.fftSize = 1024;

      if (sourceRef.current) sourceRef.current.disconnect();
      sourceRef.current = audioCtx.createMediaStreamSource(stream);
      sourceRef.current.connect(analyserRef.current);
      dataArrayRef.current = new Uint8Array(analyserRef.current.frequencyBinCount);

      mediaRecorder.current.start();
      setRecording(true);

      // 少し遅れてビジュアライザーを開始
      setTimeout(() => {
        if (!animationIdRef.current) drawVisualizer();
      }, 100);
    } catch (e) {
      console.error("録音開始エラー:", e);
      alert("マイクの使用が許可されていないか、エラーが発生しました。");
    }
  };

  /**
   * ── 録音停止 ──
   */
  const stopRecording = () => {
    if (mediaRecorder.current && mediaRecorder.current.state !== "inactive") mediaRecorder.current.stop();
    if (streamRef.current) { streamRef.current.getTracks().forEach((track) => track.stop()); streamRef.current = null; }
    if (sourceRef.current) { sourceRef.current.disconnect(); sourceRef.current = null; }
    setRecording(false);
    if (animationIdRef.current) { cancelAnimationFrame(animationIdRef.current); animationIdRef.current = null; }
  };

  return (
    <div className="flex flex-col items-center w-full gap-4 font-sans">
      {/* ── オプション設定 ── */}
      <label className="flex items-center gap-3 text-sm cursor-pointer select-none group transition-all duration-300 text-cyan-400 [text-shadow:0_0_8px_rgba(34,211,238,0.6)] hover:text-cyan-300 z-10 relative">
        <div className="relative flex items-center justify-center">
          <input
            type="checkbox"
            checked={noFalsetto}
            onChange={(e) => setNoFalsetto(e.target.checked)}
            disabled={recording || loading}
            className="peer appearance-none w-5 h-5 border-2 border-cyan-400 rounded-sm bg-slate-900/50 outline-none cursor-pointer transition-all duration-300 shadow-[0_0_10px_rgba(34,211,238,0.6)] checked:bg-cyan-400"
          />
          <svg className="absolute w-3.5 h-3.5 text-slate-900 pointer-events-none opacity-0 peer-checked:opacity-100 transition-all duration-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={4}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <span className="font-semibold tracking-wide">裏声を使わない（地声のみで判定）</span>
      </label>

      {/* ── 録音・波形表示メインエリア ── */}
      <div className="relative w-full max-w-4xl h-[500px] bg-slate-900/80 backdrop-blur-xl border border-slate-700/50 rounded-3xl overflow-hidden shadow-[0_0_50px_rgba(0,0,0,0.5)] flex flex-col items-center justify-center group">
        
        {/* 録音中の波形キャンバス */}
        {recording && (
          <div className="absolute inset-0 w-full h-full z-10">
            <canvas ref={canvasRef} width={800} height={500} className="absolute inset-0 w-full h-full drop-shadow-[0_0_10px_rgba(56,189,248,0.8)]" />
          </div>
        )}

        {/* 待機中の装飾 */}
        {!recording && !loading && (
          <div className="absolute inset-0 flex items-center justify-center text-cyan-400/10 text-6xl sm:text-8xl md:text-[10rem] font-black italic tracking-widest select-none pointer-events-none z-0 mix-blend-screen">
            READY
          </div>
        )}

        {/* 解析中（ローディング）の表示 */}
        {loading && (
          <div className="absolute inset-0 bg-slate-900/90 backdrop-blur-md z-20 flex flex-col items-center justify-center p-8">
            <div className="w-24 h-24 border-t-4 border-b-4 border-cyan-400 rounded-full animate-spin mb-8 shadow-[0_0_15px_rgba(34,211,238,0.5)]"></div>
            {/* 進捗バー */}
            <div className="w-full max-w-md h-2 bg-slate-800 rounded-full overflow-hidden mb-4 shadow-inner border border-slate-700">
              <div
                className={`h-full transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(34,211,238,0.8)] ${progress >= 100 ? "bg-emerald-400" : "bg-cyan-400"}`}
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-cyan-300 font-bold italic tracking-wide animate-pulse drop-shadow-[0_0_5px_rgba(34,211,238,0.8)]">{stepLabel}</p>
          </div>
        )}

        {/* 録音コントロールボタン */}
        {!loading && (
          <div className="absolute inset-0 z-20 flex items-center justify-center pointer-events-none">
            {!recording ? (
              <button
                onClick={startRecording}
                className="pointer-events-auto relative w-28 h-28 bg-slate-800 hover:bg-slate-700 flex flex-col items-center justify-center rounded-full transition-all duration-300 transform hover:scale-110 shadow-[0_0_30px_rgba(34,211,238,0.3)] border-2 border-cyan-500/50 z-10 group"
              >
                <MicrophoneIcon className="w-12 h-12 text-slate-300 group-hover:text-cyan-300 transition-colors" />
                <span className="text-xs mt-1 font-black italic text-cyan-400 tracking-wider">START</span>
              </button>
            ) : (
              <div className="relative flex items-center justify-center group pointer-events-auto recorder-fade-in">
                {/* 15秒で一周するプログレスリング（SVG） */}
                <svg className="absolute w-[180px] h-[180px] -rotate-90 pointer-events-none drop-shadow-[0_0_10px_rgba(232,121,249,0.8)]">
                  <circle cx="90" cy="90" r="84" fill="none" className="stroke-slate-800" strokeWidth="6" />
                  <circle cx="90" cy="90" r="84" fill="none" className="stroke-fuchsia-400 transition-all duration-100 ease-linear recorder-ring-circle" strokeWidth="6" strokeDasharray="132 396" strokeDashoffset="0" />
                </svg>
                <button onClick={stopRecording} className="w-24 h-24 bg-fuchsia-600 hover:bg-fuchsia-500 rounded-full flex items-center justify-center transition-all transform hover:scale-105 border-4 border-fuchsia-300 relative z-10 recorder-stop-btn">
                  <StopIcon className="w-12 h-12 text-white drop-shadow-[0_0_5px_rgba(255,255,255,0.8)]" />
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Recorder;