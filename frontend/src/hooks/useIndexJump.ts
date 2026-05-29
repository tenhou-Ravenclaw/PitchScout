import { useCallback } from "react";
import { getArtistIndexPage } from "../api/songs";
import { INDEX_KANA, ARTISTS_PER_PAGE } from "../constants/songListConstants";

/**
 * 五十音インデックスジャンプ（バイナリサーチ付き）フック
 * @param artists 現在のアーティストリスト
 * @param totalArtists アーティスト総数
 * @param totalPages ページ総数
 * @param setArtistPage ページ設定関数
 * @param notifyError エラー通知関数
 */
export const useIndexJump = (
  totalArtists: number,
  setArtistPage: (page: number) => void,
  notifyError: (msg: string) => void,
  fetchArtists: (page: number) => Promise<void>,
  setPageInput: (v: string) => void
) => {
  // インデックスジャンプ操作
  const handleIndexJump = useCallback(async (char: string) => {
    const targetRow = INDEX_KANA.indexOf(char);
    if (targetRow === -1 || totalArtists === 0) return;

    const containerSelector = "#artist-list-panel";

    const scrollTargetRow = (): void => {
      const el = document.querySelector(`${containerSelector} [data-row=\"${targetRow}\"]`) as HTMLElement | null;
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
      window.scrollTo({ top: 0, behavior: "smooth" });
    };

    try {
      const { page } = await getArtistIndexPage(char, ARTISTS_PER_PAGE);

      setArtistPage(page);
      setPageInput((page + 1).toString());

      await fetchArtists(page);

      setTimeout(() => {
        scrollTargetRow();
      }, 100);
    } catch (err) {
      notifyError("インデックス移動に失敗しました。");
    }
  }, [totalArtists, setArtistPage, notifyError, fetchArtists, setPageInput]);

  return { handleIndexJump };
};
