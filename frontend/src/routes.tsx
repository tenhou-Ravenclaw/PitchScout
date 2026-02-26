import React, { lazy, useCallback } from "react";
import { RouteObject } from "react-router-dom";
import { useNavigate } from "react-router-dom";
import Layout from "./components/layout/Layout";
import { useAppContext } from "./contexts/AppContext";
import { useAuth } from "./contexts/AuthContext";
import { useAnalysis } from "./contexts/AnalysisContext";
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

/**
 * 解析完了時の共通処理を提供するカスタムフック。
 * 目的: ルートラッパー内の重複ロジックを削減する。
 */
const useAnalysisCompletion = () => {
  const navigate = useNavigate();
  const { setResult, setIsFromHistory } = useAppContext();

  const handleComplete = useCallback(
    (data: AnalysisResult) => {
      setResult(data);
      setIsFromHistory(false);
      navigate("/result");
    },
    [navigate, setIsFromHistory, setResult]
  );

  const goMenu = useCallback(() => {
    navigate("/menu");
  }, [navigate]);

  return { handleComplete, goMenu };
};

/**
 * 指定パスへ遷移するコールバックを返します。
 * 目的: routes ラッパー内の `() => navigate("...")` 重複を削減する。
 */
const useNavigateTo = (path: string): (() => void) => {
  const navigate = useNavigate();

  return useCallback(() => {
    navigate(path);
  }, [navigate, path]);
};

/** Landing ページラッパー */
const LandingRoute: React.FC = () => {
  const goMenu = useNavigateTo("/menu");
  const goHistory = useNavigateTo("/history");

  return (
    <Landing
      onRecordClick={goMenu}
      onHistoryClick={goHistory}
    />
  );
};

/** Home メニューラッパー */
const HomeRoute: React.FC = () => {
  const goRecord = useNavigateTo("/record");
  const goKaraoke = useNavigateTo("/karaoke");
  const goUpload = useNavigateTo("/upload");
  const goHistory = useNavigateTo("/history");
  const { isAnalyzing } = useAnalysis();

  return (
    <Home
      onNormalClick={goRecord}
      onKaraokeClick={goKaraoke}
      onUploadClick={goUpload}
      onHistoryClick={goHistory}
      isAnalyzing={isAnalyzing}
    />
  );
};

/** AnalysisResultPage ラッパー */
const AnalysisRoute: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const { result } = useAppContext();
  return (
    <div className="min-h-screen bg-transparent">
      <AnalysisResultPage result={result} isAuthenticated={isAuthenticated} />
    </div>
  );
};

/** SongListPage ラッパー */
const SongListRoute: React.FC = () => {
  const goLogin = useNavigateTo("/login");
  const { searchQuery, setSearchQuery, userRange } = useAppContext();

  return (
    <SongListPage
      searchQuery={searchQuery}
      userRange={userRange}
      onLoginClick={goLogin}
      onSearchChange={setSearchQuery}
    />
  );
};

/** FavoritesPage ラッパー */
const FavoritesRoute: React.FC = () => {
  const goLogin = useNavigateTo("/login");
  const { isAuthenticated } = useAuth();

  return (
    <FavoritesPage
      isAuthenticated={isAuthenticated}
      onLoginClick={goLogin}
    />
  );
};

/** HistoryPage ラッパー */
const HistoryRoute: React.FC = () => {
  const navigate = useNavigate();
  const goLogin = useNavigateTo("/login");
  const { isAuthenticated } = useAuth();
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
      isAuthenticated={isAuthenticated}
      onLoginClick={goLogin}
      onSelectRecord={handleSelectRecord}
    />
  );
};

/** RecorderPage ラッパー（マイク録音） */
const RecorderRoute: React.FC = () => {
  const { handleComplete, goMenu } = useAnalysisCompletion();
  return (
    <RecorderPage
      isKaraokeMode={false}
      onBack={goMenu}
      onComplete={handleComplete}
    />
  );
};

/** RecorderPage ラッパー（カラオケ録音） */
const KaraokeRoute: React.FC = () => {
  const { handleComplete, goMenu } = useAnalysisCompletion();
  return (
    <RecorderPage
      isKaraokeMode={true}
      onBack={goMenu}
      onComplete={handleComplete}
    />
  );
};

/** UploaderPage ラッパー */
const UploaderRoute: React.FC = () => {
  const { handleComplete, goMenu } = useAnalysisCompletion();
  return (
    <UploaderPage
      onBack={goMenu}
      onComplete={handleComplete}
    />
  );
};

/** ResultPage ラッパー */
const ResultRoute: React.FC = () => {
  const navigate = useNavigate();
  const { result, isFromHistory } = useAppContext();
  return (
    <ResultPage
      result={result}
      isFromHistory={isFromHistory}
      onBack={() => navigate(isFromHistory ? "/history" : "/menu")}
    />
  );
};

/** LoginPage ラッパー */
const LoginRoute: React.FC = () => {
  const { loginWithGoogle } = useAuth();
  return <LoginPage onLogin={loginWithGoogle} />;
};

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
