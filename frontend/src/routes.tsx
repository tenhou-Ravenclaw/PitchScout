
import Layout from "./components/layout/Layout";
import { Navigate, RouteObject } from "react-router-dom";
import GuidePage from "./pages/GuidePage";
import { LandingRoute } from "./routeWrappers/LandingRoute";
import { RecordRoute } from "./routeWrappers/RecordRoute";
import { RecorderRoute } from "./routeWrappers/RecorderRoute";
import { KaraokeRoute } from "./routeWrappers/KaraokeRoute";
import { UploaderRoute } from "./routeWrappers/UploaderRoute";
import { ResultRoute } from "./routeWrappers/ResultRoute";
import { AnalysisRoute } from "./routeWrappers/AnalysisRoute";
import { SongListRoute } from "./routeWrappers/SongListRoute";
import { FavoritesRoute } from "./routeWrappers/FavoritesRoute";
import { HistoryRoute } from "./routeWrappers/HistoryRoute";
import { LoginRoute } from "./routeWrappers/LoginRoute";

export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [
      { path: "/", element: <LandingRoute /> },
      { path: "/record", element: <RecordRoute /> },
      { path: "/record/normal", element: <RecorderRoute /> },
      { path: "/record/karaoke", element: <KaraokeRoute /> },
      { path: "/record/upload", element: <UploaderRoute /> },
      { path: "/karaoke", element: <Navigate to="/record/karaoke" replace /> },
      { path: "/upload", element: <Navigate to="/record/upload" replace /> },
      { path: "/result", element: <ResultRoute /> },
      { path: "/analysis", element: <AnalysisRoute /> },
      { path: "/songs", element: <SongListRoute /> },
      { path: "/favorites", element: <FavoritesRoute /> },
      { path: "/history", element: <HistoryRoute /> },
      { path: "/guide", element: <GuidePage /> },
      { path: "/login", element: <LoginRoute /> },
    ],
  },
];
