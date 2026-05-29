import { useState, useEffect, useCallback, useRef } from "react";
import { listApi, ListType } from "../api/listApi";
import type { FavoriteSong, FavoriteArtist, AnalysisHistoryRecord } from "../api/types";
import { toUserMessage } from "../api/error";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "./useToast";

/**
 * useItemList - お気に入り・履歴などのリスト管理を共通化するカスタムフック
 *
 * favoriteSong / favoriteArtist / analysisHistory の3種別に対して、
 * オプティミスティック更新・ロールバック・連打防止・認証チェックを一元提供します。
 * useFavoriteSongs / useFavoriteArtists はこのフックの薄いラッパーです。
 *
 * @param type - リスト種別
 * @param onLoginRequired - 未ログイン時のコールバック（favoriteSong のみ有効）
 */

/** リスト操作の結果型 */
type ItemListResult<T extends number[] | string[]> = {
  /** リストIDリスト */
  ids: T;
  /** 初回ロード中フラグ */
  loading: boolean;
  /** 追加・削除トグル関数（オプティミスティック更新あり） */
  toggle: T extends number[]
    ? (id: number, name?: string) => Promise<void>
    : (id: string) => Promise<void>;
  /** IDが含まれているか判定 */
  isIncluded: T extends number[] ? (id: number) => boolean : (id: string) => boolean;
  /** 指定IDが処理中か判定（連打防止用） */
  isToggling: T extends number[] ? (id: number) => boolean : (id: string) => boolean;
};

export function useItemList(
  type: "favoriteSong",
  onLoginRequired?: () => void
): ItemListResult<number[]>;
export function useItemList(
  type: "favoriteArtist"
): ItemListResult<number[]>;
export function useItemList(
  type: "analysisHistory"
): ItemListResult<string[]>;
export function useItemList(
  type: ListType,
  onLoginRequired?: () => void
): ItemListResult<number[]> | ItemListResult<string[]> {
  const [ids, setIds] = useState<number[] | string[]>([]);
  const [togglingIds, setTogglingIds] = useState<Set<number | string>>(new Set());
  const [loading, setLoading] = useState(false);
  const { isAuthenticated } = useAuth();
  const { showToast } = useToast();

  // 最新の ids を常に参照するための Ref（stale closure 対策）
  const idsRef = useRef(ids);
  useEffect(() => {
    idsRef.current = ids;
  }, [ids]);

  /**
   * 初回マウント時・認証状態変化時にIDリストをサーバーと同期します。
   * 楽曲・アーティストお気に入りは未ログイン時に空リセットします。
   */
  useEffect(() => {
    if ((type === "favoriteSong" || type === "favoriteArtist") && !isAuthenticated) {
      setIds([]);
      return;
    }
    setLoading(true);
    listApi[type].get()
      .then((items) => {
        if (type === "favoriteSong") {
          setIds((items as FavoriteSong[]).map((item) => item.song_id));
        } else if (type === "favoriteArtist") {
          setIds((items as FavoriteArtist[]).map((item) => item.artist_id));
        } else if (type === "analysisHistory") {
          setIds((items as AnalysisHistoryRecord[]).map((item) => item.id));
        }
      })
      .catch((err) => {
        showToast(toUserMessage(err, "リスト取得に失敗しました"));
      })
      .finally(() => setLoading(false));
  }, [type, isAuthenticated, showToast]);

  /**
   * コレクションのアイテムを追加・削除します。
   * - サーバー通信前に画面を即座に更新するオプティミスティック更新を採用。
   * - API失敗時は元の状態に自動ロールバックします。
   * - 処理中フラグで連打を防止します。
   */
  const toggle = useCallback(
    async (id: number | string, name?: string) => {
      // 認証チェック
      if (type === "favoriteSong" && !isAuthenticated) {
        onLoginRequired?.();
        return;
      }
      if (type === "favoriteArtist" && !isAuthenticated) {
        showToast("ログインするとお気に入り機能を利用できます。");
        return;
      }

      // 現在の状態を Ref から取得（最新の状態を反映）
      // number[] | string[] の共通型 (number | string)[] にキャストして includes を呼ぶ
      const wasIncluded = (idsRef.current as (number | string)[]).includes(id);

      // オプティミスティック更新
      if (type === "favoriteSong" || type === "favoriteArtist") {
        const numId = id as number;
        setIds((prev) => {
          return wasIncluded
            ? (prev as number[]).filter((i) => i !== numId)
            : [...(prev as number[]), numId];
        });
      }

      // 処理中フラグ ON（連打防止）
      setTogglingIds((prev) => new Set(prev).add(id));

      try {
        if (type === "favoriteSong") {
          const songId = id as number;
          if (wasIncluded) {
            await listApi.favoriteSong.remove(songId);
          } else {
            await listApi.favoriteSong.add(songId);
          }
        } else if (type === "favoriteArtist") {
          const artistId = id as number;
          if (wasIncluded) {
            await listApi.favoriteArtist.remove(artistId);
          } else {
            await listApi.favoriteArtist.add(artistId, name ?? "");
          }
        } else if (type === "analysisHistory") {
          // 履歴は削除のみ（追加は録音フローで行う）
          await listApi.analysisHistory.remove(id as string);
          setIds((prev) => (prev as string[]).filter((i) => i !== id));
        }
      } catch (err) {
        showToast(toUserMessage(err, "リスト操作に失敗しました"));
        // ロールバック（曲・アーティストのみ）
        if (type === "favoriteSong" || type === "favoriteArtist") {
          const numId = id as number;
          setIds((prev) =>
            wasIncluded
              ? [...(prev as number[]), numId]
              : (prev as number[]).filter((i) => i !== numId)
          );
        }
      } finally {
        // 処理中フラグ OFF
        setTogglingIds((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
      }
    },
    [type, isAuthenticated, onLoginRequired, showToast]
  );

  /** IDがコレクションに含まれているか判定します。 */
  const isIncluded = useCallback(
    (id: number | string) => {
      if (type === "favoriteSong" || type === "favoriteArtist") {
        return (ids as number[]).includes(id as number);
      }
      return (ids as string[]).includes(id as string);
    },
    [type, ids]
  );

  /** 指定IDが現在処理中（API通信中）か判定します。 */
  const isToggling = useCallback(
    (id: number | string) => togglingIds.has(id),
    [togglingIds]
  );

  if (type === "favoriteSong" || type === "favoriteArtist") {
    return {
      ids: ids as number[],
      loading,
      toggle: toggle as (id: number, name?: string) => Promise<void>,
      isIncluded: isIncluded as (id: number) => boolean,
      isToggling: isToggling as (id: number) => boolean,
    };
  }
  return {
    ids: ids as string[],
    loading,
    toggle: toggle as (id: string) => Promise<void>,
    isIncluded: isIncluded as (id: string) => boolean,
    isToggling: isToggling as (id: string) => boolean,
  };
}
