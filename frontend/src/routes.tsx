/**
 * 【routes.tsx】
 * 役割：アプリ内の「URL」と「表示する画面」を紐付ける、いわばアプリの「地図」です。
 * 特徴：lazy（遅延読み込み）を使うことで、必要な時だけファイルを読み込み、初期起動を軽くしています。
 */

import React, { lazy } from "react";
import { RouteObject } from "react-router-dom";
// 共通の枠組み（ヘッダーやナビなど）を読み込みます
import Layout from "./components/Layout";

/** ── 各画面（ページ）の読み込み ──
 * lazy を使うことで、そのページを開く瞬間まで読み込みを後回しにします。
 */
const RecorderPage = lazy(() => import("./pages/RecorderPage"));
const UploaderPage = lazy(() => import("./pages/UploaderPage"));
const ResultPage = lazy(() => import("./pages/ResultPage"));
const GuidePage = lazy(() => import("./GuidePage"));
const LoginPage = lazy(() => import("./LoginPage"));

/** ── 中継役（RouteWrappers）の読み込み ──
 * ページ本体にデータ（Contextなど）を渡すためのラッパーコンポーネントです。
 */
const LandingRoute = lazy(() => import("./routeWrappers/LandingRoute"));
const HomeRoute = lazy(() => import("./routeWrappers/HomeRoute"));
const AnalysisRoute = lazy(() => import("./routeWrappers/AnalysisRoute"));
const SongListRoute = lazy(() => import("./routeWrappers/SongListRoute"));
const FavoritesRoute = lazy(() => import("./routeWrappers/FavoritesRoute"));
const HistoryRoute = lazy(() => import("./routeWrappers/HistoryRoute"));

/**
 * ── ルーティング設定の本体 ──
 * path: ブラウザのURL
 * element: その時に表示するプログラム
 */
export const routes: RouteObject[] = [
  {
    // 全ての画面で共通の Layout（枠組み）を適用します
    element: <Layout />,
    children: [
      { path: "/", element: <LandingRoute /> },        // トップ画面
      { path: "/menu", element: <HomeRoute /> },       // メニュー
      { path: "/record", element: <RecorderPage /> },   // マイク録音
      { path: "/karaoke", element: <RecorderPage /> },  // カラオケ録音
      { path: "/upload", element: <UploaderPage /> },   // ファイルアップ
      { path: "/result", element: <ResultPage /> },     // 簡易結果
      { path: "/analysis", element: <AnalysisRoute /> }, // 詳細解析結果
      { path: "/songs", element: <SongListRoute /> },    // 楽曲・アーティスト一覧
      { path: "/favorites", element: <FavoritesRoute /> },// お気に入り
      { path: "/history", element: <HistoryRoute /> },   // 履歴
      { path: "/guide", element: <GuidePage /> },       // ガイド
      { path: "/login", element: <LoginPage /> },       // ログイン
    ],
  },
];