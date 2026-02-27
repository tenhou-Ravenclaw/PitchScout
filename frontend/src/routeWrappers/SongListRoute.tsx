import React, { useCallback, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAppContext } from "../contexts/AppContext";
import SongListPage from "../pages/SongListPage";

/**
 * SongListRoute
 *
 * 検索クエリの受け渡しに URL パラメータ（?q=...）を使用する。
 * コンテキストの更新タイミングに依存しないため、他ページからの遷移でも
 * マウント直後に正しいクエリで検索結果が表示される。
 *
 * - 他ページのヘッダー検索 → Layout が `/songs?q=...` へ遷移
 *   → urlQuery が確実に非空 → SongListPage の initialQuery が正しくセットされる
 * - /songs ページ上でのヘッダー検索 → URL は変わらず context 更新のみ
 *   → urlQuery = null → context の searchQuery を fallback として使用
 *   → useSongListData の useEffect が initialQuery 変化を検知して検索実行
 */
export const SongListRoute: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { searchQuery, setSearchQuery, userRange } = useAppContext();

  // URLパラメータを優先（他ページからの遷移時にタイミング問題なく参照できるため）
  const urlQuery = searchParams.get("q");
  const effectiveQuery = urlQuery !== null ? urlQuery : searchQuery;

  // アンマウント時（他タブへ移動時）にコンテキストの検索クエリをクリアする。
  // setSearchParams は呼ばない（呼ぶと navigate が発火して他タブへの遷移が妨害される）。
  useEffect(() => {
    return () => {
      setSearchQuery("");
    };
  }, [setSearchQuery]);

  /**
   * ページ内検索バー・クリアボタンからの変更時に呼ばれる。
   * コンテキストとURLパラメータの両方を更新して一貫性を保つ。
   */
  const handleSearchChange = useCallback((q: string) => {
    setSearchQuery(q);
    setSearchParams(q ? { q } : {}, { replace: true });
  }, [setSearchQuery, setSearchParams]);

  return (
    <SongListPage
      searchQuery={effectiveQuery}
      userRange={userRange}
      onLoginClick={() => navigate("/login")}
      onSearchChange={handleSearchChange}
    />
  );
};
