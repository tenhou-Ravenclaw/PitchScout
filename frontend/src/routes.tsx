import React, { lazy } from "react";
import { RouteObject } from "react-router-dom";
import { useNavigate } from "react-router-dom";
import Layout from "./components/Layout";
import { useAppContext } from "./contexts/AppContext";
import { AnalysisResult, AnalysisHistoryRecord } from "./api";

// Lazy-loaded pages
const RecorderPage = lazy(() => import("./pages/RecorderPage"));
const UploaderPage = lazy(() => import("./pages/UploaderPage"));
const ResultPage = lazy(() => import("./pages/ResultPage"));
const GuidePage = lazy(() => import("./pages/GuidePage"));
const LoginPage = lazy(() => import("./pages/LoginPage"));
const Landing = lazy(() => import("./pages/Landing"));
const Home = lazy(() => import("./pages/Home"));
const AnalysisResultPage = lazy(() => import("./pages/AnalysisResultPage"));
const SongListPage = lazy(() => import("./pages/SongListPage"));
const FavoritesPage = lazy(() => import("./pages/FavoritesPage"));
const HistoryPage = lazy(() => import("./pages/HistoryPage"));

// ── Inline route wrappers ──

/** Landing ページリッパー */
const LandingRoute: React.FC = () => {
  const navigate = useNavigate();
  return (
    <Landing
      onRecordClick={() => navigate("/menu")}
      onHistoryClick={() => navigate("/history")}
    />
  );
};

/** Home メニューリッパー */
const HomeRoute: React.FC = () => {
  const navigate = useNavigate();
  return (
    <Home
      onNormalClick={() => navigate("/record")}
      onKaraokeClick={() => navigate("/karaoke")}
      onUploadClick={() => navigate("/upload")}
      onHistoryClick={() => navigate("/history")}
    />
  );
};

/** AnalysisResultPage リッパー */
const AnalysisRoute: React.FC = () => {
  const { result } = useAppContext();
  return (
    <div className="min-h-screen bg-transparent">
      <AnalysisResultPage result={result} />
    </div>
  );
};

/** SongListPage リッパー */
const SongListRoute: React.FC = () => {
  const navigate = useNavigate();
  const { searchQuery, setSearchQuery, userRange } = useAppContext();
  return (
    <SongListPage
      searchQuery={searchQuery}
      userRange={userRange}
      onLoginClick={() => navigate("/login")}
      onSearchChange={setSearchQuery}
    />
  );
};

/** FavoritesPage リッパー */
const FavoritesRoute: React.FC = () => {
  const navigate = useNavigate();
  const { userRange } = useAppContext();
  return (
    <FavoritesPage
      userRange={userRange}
      onLoginClick={() => navigate("/login")}
    />
  );
};

/** HistoryPage リッパー */
const HistoryRoute: React.FC = () => {
  const navigate = useNavigate();
  const { setResult, setIsFromHistory } = useAppContext();

  const handleSelectRecord = (record: AnalysisHistoryRecord) => {
    if (record.result_json) {
      setResult(record.result_json);
    } else {
      const mockResult: AnalysisResult = {
        overall_min: record.vocal_range_min || "-",
        overall_max: record.vocal_range_max || "-",
        overall_min_hz: 0,
        overall_max_hz: 0,
        chest_min: record.vocal_range_min || undefined,
        chest_max: record.vocal_range_max || undefined,
        falsetto_max: record.falsetto_max || undefined,
      };
      setResult(mockResult);
    }
    setIsFromHistory(true);
    navigate("/result");
  };

  return (
    <HistoryPage
      onLoginClick={() => navigate("/login")}
      onSelectRecord={handleSelectRecord}
    />
  );
};

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
