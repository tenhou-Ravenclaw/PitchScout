import React, { lazy } from "react";
import { RouteObject } from "react-router-dom";
import Layout from "./components/Layout";

// Lazy-loaded pages (direct use)
const RecorderPage = lazy(() => import("./pages/RecorderPage"));
const UploaderPage = lazy(() => import("./pages/UploaderPage"));
const ResultPage = lazy(() => import("./pages/ResultPage"));
const GuidePage = lazy(() => import("./GuidePage"));
const LoginPage = lazy(() => import("./LoginPage"));

// Wrapper components that wire context/hooks to page props
const LandingRoute = lazy(() => import("./routeWrappers/LandingRoute"));
const HomeRoute = lazy(() => import("./routeWrappers/HomeRoute"));
const AnalysisRoute = lazy(() => import("./routeWrappers/AnalysisRoute"));
const SongListRoute = lazy(() => import("./routeWrappers/SongListRoute"));
const FavoritesRoute = lazy(() => import("./routeWrappers/FavoritesRoute"));
const HistoryRoute = lazy(() => import("./routeWrappers/HistoryRoute"));

export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [
      { path: "/", element: <LandingRoute /> },
      { path: "/menu", element: <HomeRoute /> },
      { path: "/record", element: <RecorderPage /> },
      { path: "/karaoke", element: <RecorderPage /> },
      { path: "/upload", element: <UploaderPage /> },
      { path: "/result", element: <ResultPage /> },
      { path: "/analysis", element: <AnalysisRoute /> },
      { path: "/songs", element: <SongListRoute /> },
      { path: "/favorites", element: <FavoritesRoute /> },
      { path: "/history", element: <HistoryRoute /> },
      { path: "/guide", element: <GuidePage /> },
      { path: "/login", element: <LoginPage /> },
    ],
  },
];
