import React, { useState, useRef, useEffect, useCallback } from "react";
import { analyzeVoice, analyzeKaraoke, AnalysisResult } from "../api";
import { MicrophoneIcon, StopIcon } from "@heroicons/react/24/solid";
import "./Recorder.css";
import { useAnalysis } from '../contexts/AnalysisContext';

interface Props {
  onResult: (data: AnalysisResult) => void;
  initialUseDemucs?: boolean;
}

const Recorder: React.FC<Props> = ({ onResult, initialUseDemucs = false }) => {
  const [recording, setRecording] = useState(false);
  const {
    isAnalyzing: loading, setIsAnalyzing: setLoading,
    progress, setProgress,
    stepLabel, setStepLabel,
    startAnalysisTimer, stopAnalysisTimer
  } = useAnalysis();

  const [noFalsetto, setNoFalsetto] = useState(false);

  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  // Visualizer refs
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const dataArrayRef = useRef<Uint8Array | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const animationIdRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const gradientRef = useRef<CanvasGradient | null>(null);

  // クリーンアップ処理
  useEffect(() => {
    return () => {
      if (animationIdRef.current) {
        cancelAnimationFrame(animationIdRef.current);
      }
      if (mediaRecorder.current && mediaRecorder.current.state !== "inactive") {
        mediaRecorder.current.stop();
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
      if (sourceRef.current) {
        sourceRef.current.disconnect();
        sourceRef.current = null;
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }
    };
  }, []);

  // ビジュアライザー描画関数
  const drawVisualizer = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !analyserRef.current || !dataArrayRef.current) {
      return;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const WIDTH = canvas.width;
    const HEIGHT = canvas.height;

    analyserRef.current.getByteFrequencyData(dataArrayRef.current as any);

    ctx.clearRect(0, 0, WIDTH, HEIGHT);

    if (!gradientRef.current) {
      const gradient = ctx.createLinearGradient(0, HEIGHT, 0, 0);
      gradient.addColorStop(0, "#38bdf8");
      gradient.addColorStop(1, "#a78bfa");
      gradientRef.current = gradient;
    }
    ctx.fillStyle = gradientRef.current;

    const totalBins = dataArrayRef.current.length;
    const maxBinIndex = Math.floor(totalBins * 0.4);
    const barCount = 80;
    const barWidth = (WIDTH / barCount) * 0.8;
    const gap = (WIDTH / barCount) * 0.2;
    let x = 0;

    for (let i = 0; i < barCount; i++) {
      const percent = i / barCount;
      const indexMapping = Math.pow(percent, 2.0);
      const rawIndex = Math.floor(indexMapping * maxBinIndex);
      const valueIndex = Math.min(rawIndex, totalBins - 1);
      const v = dataArrayRef.current[valueIndex];
      const barHeight = Math.max((v / 255) * HEIGHT * 0.95, 5);
      ctx.fillRect(x, HEIGHT - barHeight, barWidth, barHeight);
      x += barWidth + gap;
    }

    animationIdRef.current = requestAnimationFrame(drawVisualizer);
  }, []);

  // 録音開始
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      mediaRecorder.current = new MediaRecorder(stream);
      chunks.current = [];

      mediaRecorder.current.ondataavailable = (e) => {
        chunks.current.push(e.data);
      };

      mediaRecorder.current.onstop = async () => {
        if (animationIdRef.current) cancelAnimationFrame(animationIdRef.current);
        const blob = new Blob(chunks.current, { type: "audio/webm" });

        if (initialUseDemucs) {
          startAnalysisTimer('karaoke_record');
        } else {
          startAnalysisTimer('mic_record');
        }

        try {
          const data = initialUseDemucs
            ? await analyzeKaraoke(blob, "recording.webm", noFalsetto)
            : await analyzeVoice(blob, noFalsetto);

          stopAnalysisTimer();
          setProgress(100);
          setStepLabel("完了！");
          onResult(data);
        } catch (err: unknown) {
          stopAnalysisTimer();
          const axiosErr = err as { code?: string; message?: string; response?: { data?: { error?: string } } };
          let errorMsg: string;
          if (
            axiosErr?.message?.includes("timeout")
          ) {
            errorMsg =
              "⏱️ 処理時間が10分を超えたため、タイムアウトしました。録音が長すぎるか、サーバーの負荷が高い可能性があります。もう一度お試しください。";
          } else if (axiosErr?.code === "ECONNABORTED" || axiosErr?.message?.includes("Network Error")) {
            errorMsg =
              "ネットワークエラーが発生しました。サーバーに接続できないか、通信が途中で切断された可能性があります。もう一度お試しください。";
          } else {
            errorMsg =
              axiosErr?.response?.data?.error ||
              axiosErr?.message ||
              "解析に失敗しました。もう一度お試しください。";
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

      if (!audioContextRef.current) {
        audioContextRef.current = new (
          window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext!
        )();
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

      setTimeout(() => {
        if (!animationIdRef.current) {
          drawVisualizer();
        }
      }, 100);
    } catch (e) {
      console.error("録音開始エラー:", e);
      alert("マイクの使用が許可されていないか、エラーが発生しました。");
    }
  };

  const stopRecording = () => {
    if (mediaRecorder.current && mediaRecorder.current.state !== "inactive") {
      mediaRecorder.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (sourceRef.current) {
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }
    setRecording(false);
    if (animationIdRef.current) {
      cancelAnimationFrame(animationIdRef.current);
      animationIdRef.current = null;
    }
  };

  return (
    <div className="flex flex-col items-center w-full gap-4 font-sans">
      {/* 裏声なしオプション */}
      <label className="flex items-center gap-3 text-sm cursor-pointer select-none group transition-all duration-300 text-cyan-400 [text-shadow:0_0_8px_rgba(34,211,238,0.6)] hover:text-cyan-300 hover:[text-shadow:0_0_15px_rgba(34,211,238,1)] z-10 relative">
        <div className="relative flex items-center justify-center">
          <input
            type="checkbox"
            checked={noFalsetto}
            onChange={(e) => setNoFalsetto(e.target.checked)}
            disabled={recording || loading}
            className="peer appearance-none w-5 h-5 border-2 border-cyan-400 rounded-sm bg-slate-900/50 outline-none cursor-pointer transition-all duration-300 shadow-[0_0_10px_rgba(34,211,238,0.6)] group-hover:shadow-[0_0_20px_rgba(34,211,238,1)] group-hover:border-cyan-300 checked:bg-cyan-400 checked:border-cyan-400 checked:shadow-[0_0_20px_rgba(34,211,238,1)] disabled:opacity-50 disabled:cursor-not-allowed focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 focus-visible:outline-none"
          />
          <svg
            className="absolute w-3.5 h-3.5 text-slate-900 pointer-events-none opacity-0 peer-checked:opacity-100 transition-all duration-300 scale-50 peer-checked:scale-100"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={4}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <span className="font-semibold tracking-wide">裏声を使わない（地声のみで判定）</span>
      </label>

      <div className="relative w-full max-w-4xl h-[500px] bg-slate-900/80 backdrop-blur-xl border border-slate-700/50 rounded-3xl overflow-hidden shadow-[0_0_50px_rgba(0,0,0,0.5)] flex flex-col items-center justify-center group">
        {/* Visualizer Canvas during recording */}
        {recording && (
          <div className="absolute inset-0 w-full h-full z-10">
            <canvas
              ref={canvasRef}
              width={800}
              height={500}
              className="absolute inset-0 w-full h-full drop-shadow-[0_0_10px_rgba(56,189,248,0.8)]"
            />
          </div>
        )}

        {/* Ambient background glow (idle) */}
        {!loading && (
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-cyan-500/20 rounded-full blur-[80px] pointer-events-none"></div>
        )}
        {!recording && !loading && (
          <div className="absolute inset-0 flex items-center justify-center text-cyan-400/10 text-6xl sm:text-8xl md:text-[10rem] font-black italic tracking-widest select-none pointer-events-none drop-shadow-[0_0_15px_rgba(34,211,238,0.3)] z-0 mix-blend-screen">
            READY
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="absolute inset-0 bg-slate-900/90 backdrop-blur-md z-20 flex flex-col items-center justify-center p-8">
            <div className="w-24 h-24 border-t-4 border-b-4 border-cyan-400 rounded-full animate-spin mb-8 shadow-[0_0_15px_rgba(34,211,238,0.5)]"></div>
            <div className="w-full max-w-md h-2 bg-slate-800 rounded-full overflow-hidden mb-4 shadow-inner border border-slate-700">
              <div
                className={`h-full transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(34,211,238,0.8)] ${progress >= 100 ? "bg-emerald-400" : "bg-cyan-400"
                  }`}
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-cyan-300 font-bold italic tracking-wide animate-pulse drop-shadow-[0_0_5px_rgba(34,211,238,0.8)]">{stepLabel}</p>
          </div>
        )}

        {/* Recording Controls */}
        {!loading && (
          <div className="absolute inset-0 z-20 flex items-center justify-center pointer-events-none">
            {!recording ? (
              // --- Idle State Button ---
              <button
                onClick={startRecording}
                className="pointer-events-auto relative w-28 h-28 bg-slate-800 hover:bg-slate-700 flex flex-col items-center justify-center rounded-full transition-all duration-300 transform hover:scale-110 shadow-[0_0_30px_rgba(34,211,238,0.3)] hover:shadow-[0_0_50px_rgba(34,211,238,0.6)] border-2 border-cyan-500/50 hover:border-cyan-400 group z-10"
              >
                <MicrophoneIcon className="w-12 h-12 text-slate-300 group-hover:text-cyan-300 transition-colors drop-shadow-[0_0_8px_rgba(34,211,238,0)] group-hover:drop-shadow-[0_0_8px_rgba(34,211,238,0.8)]" />
                <span className="text-xs mt-1 font-black italic text-cyan-400 tracking-wider">START</span>
              </button>
            ) : (
              // --- Recording State Button ---
              <div className="relative flex items-center justify-center group pointer-events-auto recorder-fade-in">
                {/* 15s Progress Ring SVG */}
                <svg className="absolute w-[180px] h-[180px] -rotate-90 pointer-events-none drop-shadow-[0_0_10px_rgba(232,121,249,0.8)]">
                  <circle
                    cx="90"
                    cy="90"
                    r="84"
                    fill="none"
                    className="stroke-slate-800"
                    strokeWidth="6"
                  />
                  <circle
                    cx="90"
                    cy="90"
                    r="84"
                    fill="none"
                    className="stroke-fuchsia-400 transition-all duration-100 ease-linear recorder-ring-circle"
                    strokeWidth="6"
                    strokeDasharray="132 396"
                    strokeDashoffset="0"
                  />
                </svg>

                <button
                  onClick={stopRecording}
                  className="w-24 h-24 bg-fuchsia-600 hover:bg-fuchsia-500 rounded-full flex items-center justify-center transition-all transform hover:scale-105 border-4 border-fuchsia-300 relative z-10 recorder-stop-btn"
                  aria-label="録音を停止"
                >
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