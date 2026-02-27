import { lazy } from "react";
import Layout from "./components/layout/Layout";
import { RouteObject } from "react-router-dom";

/**
 * ルートコンポーネントを遅延ロードします。
 * React.lazy() により初回バンドルサイズを削減し、各ページは初めてアクセスされた
 * タイミングで初めてJSが読み込まれます（コード分割）。
 * Layout.tsx の <Suspense> がローディング中のフォールバックを担当します。
 *
 * 名前付きエクスポートは .then() で default に変換して lazy に渡します。
 */
const LandingRoute  = lazy(() => import("./routeWrappers/LandingRoute").then(m => ({ default: m.LandingRoute })));
const HomeRoute     = lazy(() => import("./routeWrappers/HomeRoute").then(m => ({ default: m.HomeRoute })));
const RecorderRoute = lazy(() => import("./routeWrappers/RecorderRoute").then(m => ({ default: m.RecorderRoute })));
const KaraokeRoute  = lazy(() => import("./routeWrappers/KaraokeRoute").then(m => ({ default: m.KaraokeRoute })));
const UploaderRoute = lazy(() => import("./routeWrappers/UploaderRoute").then(m => ({ default: m.UploaderRoute })));
const ResultRoute   = lazy(() => import("./routeWrappers/ResultRoute").then(m => ({ default: m.ResultRoute })));
const AnalysisRoute = lazy(() => import("./routeWrappers/AnalysisRoute").then(m => ({ default: m.AnalysisRoute })));
const SongListRoute = lazy(() => import("./routeWrappers/SongListRoute").then(m => ({ default: m.SongListRoute })));
const FavoritesRoute = lazy(() => import("./routeWrappers/FavoritesRoute").then(m => ({ default: m.FavoritesRoute })));
const HistoryRoute  = lazy(() => import("./routeWrappers/HistoryRoute").then(m => ({ default: m.HistoryRoute })));
const LoginRoute    = lazy(() => import("./routeWrappers/LoginRoute").then(m => ({ default: m.LoginRoute })));
const GuidePage     = lazy(() => import("./pages/GuidePage"));

export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [
      { path: "/",          element: <LandingRoute /> },
      { path: "/menu",      element: <HomeRoute /> },
      { path: "/record",    element: <RecorderRoute /> },
      { path: "/karaoke",   element: <KaraokeRoute /> },
      { path: "/upload",    element: <UploaderRoute /> },
      { path: "/result",    element: <ResultRoute /> },
      { path: "/analysis",  element: <AnalysisRoute /> },
      { path: "/songs",     element: <SongListRoute /> },
      { path: "/favorites", element: <FavoritesRoute /> },
      { path: "/history",   element: <HistoryRoute /> },
      { path: "/guide",     element: <GuidePage /> },
      { path: "/login",     element: <LoginRoute /> },
    ],
  },
];
