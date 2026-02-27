import { useCallback } from "react";
import { getArtists, Artist } from "../api";
import { INDEX_KANA, ARTISTS_PER_PAGE, getConsonantRow } from "../constants/songListConstants";

/**
 * 五十音インデックスジャンプ（バイナリサーチ付き）フック
 * @param artists 現在のアーティストリスト
 * @param totalArtists アーティスト総数
 * @param totalPages ページ総数
 * @param setArtistPage ページ設定関数
 * @param notifyError エラー通知関数
 */
export const useIndexJump = (
  artists: Artist[],
  totalArtists: number,
  totalPages: number,
  setArtistPage: (page: number) => void,
  notifyError: (msg: string) => void
) => {
  // 現在ページに該当行が含まれるか
  const isCurrentPageMatchedByRow = useCallback((targetRow: number): boolean => {
    const indexInPage = artists.findIndex((artist) => getConsonantRow(artist.reading || "") >= targetRow);
    return indexInPage !== -1 && getConsonantRow(artists[indexInPage].reading || "") === targetRow;
  }, [artists]);

  // バイナリサーチで該当行の最初のページを探す
  const findFirstPageByConsonantRow = useCallback(async (targetRow: number): Promise<number> => {
    let low = 0;
    let high = Math.max(totalPages - 1, 0);
    let found = 0;

    while (low <= high) {
      const mid = Math.floor((low + high) / 2);
      const offset = mid * ARTISTS_PER_PAGE;
      const { artists: page } = await getArtists(ARTISTS_PER_PAGE, offset);
      if (!page.length) break;

      const firstRow = getConsonantRow(page[0].reading || "");
      const lastRow = getConsonantRow(page[page.length - 1].reading || "");

      if (targetRow < firstRow) {
        high = mid - 1;
        continue;
      }
      if (targetRow > lastRow) {
        low = mid + 1;
        continue;
      }

      found = mid;
      high = mid - 1;
    }

    return found;
  }, [totalPages]);

  // インデックスジャンプ操作
  const handleIndexJump = useCallback(async (char: string) => {
    const targetRow = INDEX_KANA.indexOf(char);
    if (targetRow === -1 || totalArtists === 0) {
      return;
    }

    if (isCurrentPageMatchedByRow(targetRow)) {
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }

    try {
      const found = await findFirstPageByConsonantRow(targetRow);
      setArtistPage(found);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      notifyError("インデックス移動に失敗しました。");
    }
  }, [totalArtists, isCurrentPageMatchedByRow, findFirstPageByConsonantRow, setArtistPage, notifyError]);

  return { handleIndexJump };
};
