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
  notifyError: (msg: string) => void,
  fetchArtists: (page: number) => Promise<void>,
  artistPage: number,
  setPageInput: (v: string) => void
) => {
  // 現在ページに該当行が含まれるか
  const isCurrentPageMatchedByRow = useCallback((targetRow: number): boolean => {
    const indexInPage = artists.findIndex((artist) => getConsonantRow(artist.reading || "") >= targetRow);
    return indexInPage !== -1 && getConsonantRow(artists[indexInPage].reading || "") === targetRow;
  }, [artists]);

  // バイナリサーチで該当行の最初のページを探す
  const findFirstPageByConsonantRow = useCallback(async (targetRow: number): Promise<number> => {
    // 線形探索で最初に該当行が出現するページを返す（堅牢性優先）
    const maxPages = Math.max(totalPages, 0);
    for (let p = 0; p < maxPages; p++) {
      const offset = p * ARTISTS_PER_PAGE;
      const { artists: page } = await getArtists(ARTISTS_PER_PAGE, offset);
      if (!page || page.length === 0) continue;
      // ページ内に targetRow を持つ要素があるか
      for (const a of page) {
        if (getConsonantRow(a.reading || "") === targetRow) {
          return p;
        }
      }
    }
    // 見つからなければ先頭に戻す
    return 0;
  }, [totalPages]);

  // インデックスジャンプ操作
  const handleIndexJump = useCallback(async (char: string) => {
    const targetRow = INDEX_KANA.indexOf(char);
    if (targetRow === -1 || totalArtists === 0) return;

    const containerSelector = "#artist-list-panel";

    try {
      let found = await findFirstPageByConsonantRow(targetRow);

      // binary search で見つかったページの直前に該当行が含まれていないか確認し、
      // より早いページが該当する場合は詰める（オフバイワン対策）
      while (found > 0) {
        const prevOffset = (found - 1) * ARTISTS_PER_PAGE;
        const { artists: prevPage } = await getArtists(ARTISTS_PER_PAGE, prevOffset);
        if (!prevPage || prevPage.length === 0) break;
        const prevLastRow = getConsonantRow(prevPage[prevPage.length - 1].reading || "");
        if (prevLastRow >= targetRow) {
          found = found - 1;
          continue;
        }
        break;
      }

      // 目的: 全アーティストの中での先頭ページへ移動する
      setArtistPage(found);
      // 表示用の入力（1-index）を更新
      try {
        setPageInput((found + 1).toString());
      } catch (_) {}

      // fetchArtists を呼び出してサーバー側の総数/ページ情報を更新する
      try {
        await fetchArtists(found).catch(() => {});
      } finally {
        // ページ切替後に描画される要素を探して先頭に揃える
        setTimeout(() => {
          const el = document.querySelector(`${containerSelector} [data-row=\"${targetRow}\"]`) as HTMLElement | null;
          if (el) {
            el.scrollIntoView({ behavior: "smooth", block: "start" });
          } else {
            window.scrollTo({ top: 0, behavior: "smooth" });
          }
        }, 150);
      }
    } catch (err) {
      notifyError("インデックス移動に失敗しました。");
    }
  }, [totalArtists, isCurrentPageMatchedByRow, findFirstPageByConsonantRow, setArtistPage, notifyError]);

  return { handleIndexJump };
};
