
import Layout from "./components/layout/Layout";
import { RouteObject } from "react-router-dom";
import GuidePage from "./pages/GuidePage";
import { LandingRoute } from "./routeWrappers/LandingRoute";
import { HomeRoute } from "./routeWrappers/HomeRoute";
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
      { path: "/menu", element: <HomeRoute /> },
      { path: "/record", element: <RecorderRoute /> },
      { path: "/karaoke", element: <KaraokeRoute /> },
      { path: "/upload", element: <UploaderRoute /> },
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
