/**
 * 【routes.tsx】
 * 役割：アプリの「地図」です。「どのURL（パス）にアクセスした時に、どの画面を表示するか」を一括で定義します。
 * 💡 設計図（FRONTEND_STRUCTURE.md）に基づく移動案：
 * 1. 移動先: src/app/routes.tsx
 * 2. 理由：ルーティングの設定はアプリ全体の基盤に関わるため、appフォルダにまとめます。
 */

import React, { lazy } from "react";
import { RouteObject } from "react-router-dom";
// 全画面共通の枠組み（ヘッダーやナビゲーション）
import Layout from "./components/Layout";

/**
 * ── ページコンポーネントの読み込み ──
 * lazy を使用することで、その画面が必要になったタイミングで初めてファイルを読み込みます。
 * これにより、アプリ起動時の読み込み時間を短縮できます（Lazy Loading）。
 */
const RecorderPage = lazy(() => import("./pages/RecorderPage"));
const UploaderPage = lazy(() => import("./pages/UploaderPage"));
const ResultPage = lazy(() => import("./pages/ResultPage"));
const GuidePage = lazy(() => import("./GuidePage"));
const LoginPage = lazy(() => import("./LoginPage"));

/**
 * ── ルートラッパー（Wire用） ──
 * コンテキスト（Context）やフック（Hooks）を各ページに橋渡しする役割のコンポーネントです。
 */
const LandingRoute = lazy(() => import("./routeWrappers/LandingRoute"));
const HomeRoute = lazy(() => import("./routeWrappers/HomeRoute"));
const AnalysisRoute = lazy(() => import("./routeWrappers/AnalysisRoute"));
const SongListRoute = lazy(() => import("./routeWrappers/SongListRoute"));
const FavoritesRoute = lazy(() => import("./routeWrappers/FavoritesRoute"));
const HistoryRoute = lazy(() => import("./routeWrappers/HistoryRoute"));

/**
 * ── ルート定義の本体 ──
 */
export const routes: RouteObject[] = [
  {
    // 全てのページに適用される共通レイアウト
    element: <Layout />,
    children: [
      // 各パス（URL）と表示するコンポーネントの対応付け
      { path: "/", element: <LandingRoute /> },            // トップ画面
      { path: "/menu", element: <HomeRoute /> },           // メニュー画面
      { path: "/record", element: <RecorderPage /> },      // 通常録音
      { path: "/karaoke", element: <RecorderPage /> },     // カラオケ録音
      { path: "/upload", element: <UploaderPage /> },      // アップロード
      { path: "/result", element: <ResultPage /> },        // 結果表示（簡易）
      { path: "/analysis", element: <AnalysisRoute /> },   // 解析結果詳細
      { path: "/songs", element: <SongListRoute /> },      // 楽曲一覧・検索
      { path: "/favorites", element: <FavoritesRoute /> }, // お気に入り
      { path: "/history", element: <HistoryRoute /> },     // 履歴
      { path: "/guide", element: <GuidePage /> },          // 使い方ガイド
      { path: "/login", element: <LoginPage /> },          // ログイン
    ],
  },
];