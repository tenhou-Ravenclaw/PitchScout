/**
 * 【KaraokeUploader.tsx】
 * 役割：手持ちのカラオケ音源ファイル（MP3/WAV等）をアップロードして解析するための部品です。
 * 特徴：ドラッグ＆ドロップ対応、ファイル形式チェック、解析中の進捗表示機能を備えています。
 */

import React, { useState, useRef } from "react";
// APIから解析関数と型をインポート
import { analyzeKaraoke, AnalysisResult, toUserMessage } from "../../api";
import { CloudArrowUpIcon, DocumentArrowUpIcon } from "@heroicons/react/24/solid";
// 解析の状態（進捗やラベル）を管理するためのフック
import { useAnalysis } from '../../contexts/AnalysisContext';
import ErrorBanner from "../ui/ErrorBanner";

interface Props {
  onResult: (data: AnalysisResult) => void; // 解析完了時に実行される関数
}

const KaraokeUploader: React.FC<Props> = ({ onResult }) => {
  // ── 共有状態 (Context) ──
  const {
    isAnalyzing: loading, setIsAnalyzing: setLoading,
    progress, setProgress,
    stepLabel, setStepLabel,
    startAnalysisTimer, stopAnalysisTimer
  } = useAnalysis();

  // ── ローカル状態 (State) ──
  const [error, setError] = useState("");              // エラーメッセージ
  const [fileName, setFileName] = useState<string | null>(null); // 選択されたファイル名
  const [isHovered, setIsHovered] = useState(false);    // マウスホバー状態
  const [isDragging, setIsDragging] = useState(false);  // ファイルドラッグ中状態
  const [noFalsetto, setNoFalsetto] = useState(false);  // 裏声除外オプション

  // ファイル入力要素への参照
  const fileInputRef = useRef<HTMLInputElement>(null);

  /**
   * ── ファイル処理のメインロジック ──
   * 形式チェック、タイマー開始、API送信、結果受取までを行います。
   */
  const processFile = async (file: File) => {
    // 対応フォーマットの定義
    const supportedExts = [".wav", ".mp3", ".m4a", ".aac", ".mp4", ".ogg", ".flac", ".wma", ".webm"];
    const ext = file.name.toLowerCase().slice(file.name.lastIndexOf("."));
    const isAudio =
      file.type.startsWith("audio/") ||
      file.type.startsWith("video/") ||
      supportedExts.includes(ext);

    // 形式が合わない場合はエラーを表示して終了
    if (!isAudio) {
      setError(
        "対応していないファイル形式です。音声ファイル（MP3, M4A, AAC, WAV, FLAC等）をアップロードしてください。"
      );
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    setError("");
    setFileName(file.name);

    // 進捗表示用の疑似タイマーを開始
    startAnalysisTimer('upload');

    try {
      // サーバーへファイルを送信して解析を依頼
      const data = await analyzeKaraoke(file, file.name, noFalsetto);

      stopAnalysisTimer(); // タイマー停止
      setProgress(100);    // プログレスバーを100%に
      setStepLabel("完了！");

      if (data.error) {
        setError(data.error);
      } else {
        onResult(data); // 成功したら親コンポーネントへ結果を渡す
      }
    } catch (err: unknown) {
      // 通信エラーやタイムアウトの処理
      stopAnalysisTimer();
      setError(toUserMessage(err, "解析に失敗しました。もう一度お試しください。"));
    } finally {
      // 少し待ってから解析中表示をリセットします
      setTimeout(() => {
        setLoading(false);
        setProgress(0);
        setStepLabel("");
      }, 500);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  /** ── イベントハンドラー ── */
  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  const handleDragOver = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    if (!loading) setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    const related = e.relatedTarget as Node | null;
    if (related && e.currentTarget.contains(related)) return;
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (loading) return;
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  };

  return (
    <div className="flex flex-col items-center gap-8 w-full max-w-2xl mx-auto font-sans relative z-10 p-4 sm:p-8">

      {/* ヘッダー部分 */}
      <div className="text-center w-full">
        <h2 className="text-3xl sm:text-4xl font-black italic text-fuchsia-400 mb-4 drop-shadow-[0_0_10px_rgba(232,121,249,0.8)] tracking-wide">
          🎤 UPLOAD KARAOKE
        </h2>
        <p className="text-sm sm:text-base text-fuchsia-200 font-bold tracking-wide drop-shadow-md">
          歌入りの音源をアップロードして解析を開始します
        </p>
        <p className="text-xs text-fuchsia-400 mt-2 tracking-widest uppercase">
          [ SUPPORTED: MP3, M4A, AAC, WAV, FLAC ]
        </p>
      </div>

      {/* 裏声なしオプション */}
      <label className="flex items-center gap-2 text-sm text-fuchsia-200 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={noFalsetto}
          onChange={(e) => setNoFalsetto(e.target.checked)}
          disabled={loading}
          className="w-4 h-4 rounded border-fuchsia-500/50 bg-fuchsia-950/50 text-fuchsia-400 focus:ring-fuchsia-400"
        />
        裏声を使わない（地声のみで判定）
      </label>

      {/* サイバーパンク風ドロップゾーン */}
      <div className="w-full relative group perspective-[1000px] mt-2">
        <label
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onMouseEnter={() => !loading && setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          className={`relative w-full aspect-video sm:aspect-[21/9] flex flex-col items-center justify-center p-8 transition-all duration-300 block overflow-hidden ${
            loading ? "bg-fuchsia-950/60 cursor-not-allowed cursor-wait" : "bg-gradient-to-br from-fuchsia-950/40 via-fuchsia-900/30 to-fuchsia-950/40 hover:bg-fuchsia-900/40 cursor-pointer"
          }`}
          style={{
            clipPath: 'polygon(30px 0, 100% 0, 100% calc(100% - 30px), calc(100% - 30px) 100%, 0 100%, 0 30px)',
            boxShadow: isDragging || isHovered ? '0 0 30px rgba(232,121,249,0.4)' : '0 0 15px rgba(0,0,0,0.5)'
          }}
        >
          {/* ネオンの縁取り装飾 */}
          <div className={`absolute inset-0 border-2 transition-all duration-300 pointer-events-none z-10 ${isDragging || isHovered ? 'border-fuchsia-400 shadow-[inset_0_0_20px_rgba(232,121,249,0.6)] animate-pulse' : 'border-fuchsia-500/50'
            }`}
            style={{ clipPath: 'polygon(30px 0, 100% 0, 100% calc(100% - 30px), calc(100% - 30px) 100%, 0 100%, 0 30px)' }}></div>

          {/* デジタルグリッド背景 */}
          <div className="absolute inset-0 z-0 opacity-10 pointer-events-none"
            style={{
              backgroundImage: 'linear-gradient(rgba(232, 121, 249, 0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(232, 121, 249, 0.5) 1px, transparent 1px)',
              backgroundSize: '20px 20px'
            }}>
          </div>

          {/* スキャンラインエフェクト */}
          <div className={`absolute inset-0 z-0 pointer-events-none transition-opacity duration-500 ${isDragging || (isHovered && !loading) ? 'opacity-100' : 'opacity-0'}`}>
            <div className="w-full h-full bg-[linear-gradient(to_bottom,transparent_0%,rgba(232,121,249,0.2)_50%,transparent_100%)] bg-[length:100%_4px] animate-scan"></div>
          </div>

          {/* 背面の透かし文字 */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full text-center z-0 pointer-events-none">
            <span className="text-4xl sm:text-6xl md:text-7xl font-black italic text-fuchsia-400 opacity-5 sm:opacity-[0.03] tracking-widest whitespace-nowrap">
              DROP FILE HERE
            </span>
          </div>

          {/* メインコンテンツ（アイコン・ファイル名） */}
          <div className="relative z-20 flex flex-col items-center justify-center text-center transform transition-transform duration-300 group-hover:scale-105">
            {fileName && !loading ? (
              <div className="flex flex-col items-center gap-3">
                <DocumentArrowUpIcon className="w-16 h-16 text-fuchsia-400 drop-shadow-[0_0_8px_rgba(232,121,249,0.8)]" />
                <p className="text-lg font-bold text-fuchsia-100 bg-fuchsia-950/50 px-4 py-2 rounded-lg border border-fuchsia-500/30">
                  {fileName}
                </p>
                <p className="text-xs text-fuchsia-400 font-bold italic mt-2 animate-pulse">CLICK OR DROP AGAIN TO CHANGE</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-4">
                <CloudArrowUpIcon
                  className={`w-16 h-16 sm:w-20 sm:h-20 transition-all duration-300 ${loading ? "text-slate-500" : "text-fuchsia-400 drop-shadow-[0_0_15px_rgba(232,121,249,0.8)]"
                    } ${isDragging ? "scale-110" : ""}`}
                />
                <div className="space-y-1">
                  <p className="text-lg sm:text-xl font-bold italic text-fuchsia-100 tracking-wide">
                    {isDragging ? (
                      <span className="text-fuchsia-300 drop-shadow-[0_0_5px_rgba(232,121,249,0.8)] animate-pulse">RELEASE TO TRANSFER</span>
                    ) : (
                      <span>CLICK OR DROP FILE</span>
                    )}
                  </p>
                  <p className="text-xs text-fuchsia-300/60 font-medium tracking-widest">
                    MAX SIZE: 50MB
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* 実際のファイル選択ボタン（隠し要素） */}
          <input
            ref={fileInputRef}
            type="file"
            accept="audio/*,.mp3,.m4a,.aac,.wav,.flac,.ogg,.wma,.mp4"
            onChange={handleUpload}
            disabled={loading}
            className="hidden"
          />
        </label>

        {/* 装飾用の角アクセント */}
        <div className="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 border-fuchsia-400 z-20 opacity-50 pointer-events-none shadow-[0_0_5px_rgba(232,121,249,1)]"></div>
        <div className="absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 border-fuchsia-400 z-20 opacity-50 pointer-events-none shadow-[0_0_5px_rgba(232,121,249,1)]"></div>
      </div>

      {/* 解析中のプログレスバー */}
      {loading && (
        <div className="w-full max-w-lg mt-4 bg-slate-900/80 backdrop-blur-md p-6 rounded-2xl border border-fuchsia-500/30 shadow-[0_0_20px_rgba(232,121,249,0.2)]">
          <div className="w-full h-3 bg-slate-800 rounded-full overflow-hidden mb-4 shadow-inner border border-slate-700">
            <div
              className={`h-full rounded-full transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(232,121,249,0.8)] ${progress >= 100 ? "bg-cyan-400" : "bg-fuchsia-500"
                }`}
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-center text-sm font-bold italic text-fuchsia-300 tracking-wider animate-pulse drop-shadow-[0_0_5px_rgba(232,121,249,0.5)]">
            {stepLabel}
          </p>
        </div>
      )}

      {/* エラー表示エリア */}
      {error && (
        <ErrorBanner message={error} className="max-w-lg" />
      )}

    </div>
  );
};

export default KaraokeUploader;