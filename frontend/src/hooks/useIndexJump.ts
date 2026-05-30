import { useCallback } from "react";
import { getArtistIndexPage } from "../api/songs";
import { INDEX_KANA, ARTISTS_PER_PAGE } from "../constants/songListConstants";

/**
 * 五十音インデックスジャンプフック
 * @param totalArtists アーティスト総数
 * @param setArtistPage ページ設定関数
 * @param notifyError エラー通知関数
 * @param fetchArtists ページ取得関数
 * @param setPageInput ページ入力欄の更新関数
 */
export const useIndexJump = (
  totalArtists: number,
  setArtistPage: (page: number) => void,
  notifyError: (msg: string) => void,
  fetchArtists: (page: number) => Promise<void>,
  setPageInput: (v: string) => void
) => {
  // インデックスジャンプ操作
  const handleIndexJump = useCallback(async (char: string): Promise<void> => {
    const targetRow = INDEX_KANA.indexOf(char);
    if (targetRow === -1 || totalArtists === 0) return;

    const containerSelector = "#artist-list-panel";

    const scrollTargetRow = (): void => {
      // data-row が同じ要素が複数ある場合、querySelector は先頭（その行の最初のアーティスト）を返す
      const el = document.querySelector(`${containerSelector} [data-row="${targetRow}"]`) as HTMLElement | null;
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

      // React の再描画完了後にスクロール。
      // double rAF で「次フレームの描画完了後」を待つ（固定 setTimeout より信頼性が高い）
      requestAnimationFrame(() => requestAnimationFrame(scrollTargetRow));
    } catch (err) {
      notifyError("インデックス移動に失敗しました。");
    }
  }, [totalArtists, setArtistPage, notifyError, fetchArtists, setPageInput]);

  return { handleIndexJump };
};
