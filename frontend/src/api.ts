/**
 * 【api.ts】
 * 役割：サーバー（バックエンド）と通信するための「依頼書（関数）」と「データの形（型定義）」をまとめたファイルです。
 * ここにある関数を呼び出すことで、録音データの解析や楽曲の検索が行われます。
 */

import axios from "axios";
import { supabase } from "./supabaseClient";

/** 通信のタイムアウト時間を設定（10分間待つ設定） */
const TIMEOUT_MS = 600000; 

/**
 * ── 通信機 (Axios) の初期設定 ──
 * 本番環境（Vercelなど）と開発環境（自分のPC）で、通信相手の住所（URL）を自動で切り替えます。
 */
const API = axios.create({
  baseURL: process.env.REACT_APP_API_URL || (process.env.NODE_ENV === "production" ? "/api" : "http://127.0.0.1:8000"),
  timeout: TIMEOUT_MS,
});

/**
 * ── 認証の自動化 (Interceptors) ──
 * サーバーにリクエストを送る「直前」に、Supabaseからログイン情報を取得し、
 * 「私はログイン済みのユーザーです」という証明（トークン）を自動でヘッダーに付与します。
 */
API.interceptors.request.use(async (config) => {
  if (supabase) {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// ── 型定義 (Interfaces) ───────────────────────────────────
// サーバーとやり取りするデータの「設計図」です。どんな項目が入っているかを定義します。

/** 歌唱分析の詳細（スコアなど） */
export interface SingingAnalysis {
  overall_score: number;
  range_score: number;
  range_semitones: number;
  stability_score: number;
  expression_score: number;
}

/** 声質の種類（バリトン、テノールなど） */
export interface VoiceType {
  voice_type?: string;
  range_class?: string;
  description?: string;
}

/** おすすめ楽曲のデータ */
export interface RecommendedSong {
  id: number;
  title: string;
  artist: string;
  lowest_note: string | null;
  highest_note: string | null;
  match_score: number;
  recommended_key?: number;
  fit?: string;
}

/** 声が似ているアーティストの情報 */
export interface SimilarArtist {
  id: number;
  name: string;
  typical_lowest: string;
  typical_highest: string;
  similarity_score: number;
}

/** 一般的な楽曲データ */
export interface Song {
  id: number;
  artist_id: number;
  title: string;
  artist: string;
  artist_reading?: string;
  artist_slug?: string;
  lowest_note: string | null;
  highest_note: string | null;
  falsetto_note: string | null;
  note: string | null;
  source: string;
  recommended_key?: number;
  fit?: string;
}

/** お気に入り登録されたアーティスト */
export interface FavoriteArtist {
  id: string;
  artist_id: number;
  artist_name: string;
  created_at: string;
}

/** お気に入り楽曲の情報 */
export interface FavoriteSong {
  favorite_id: string;
  song_id: number;
  title: string;
  artist: string | null;
  lowest_note: string | null;
  highest_note: string | null;
  falsetto_note: string | null;
  created_at: string;
}

/**
 * 解析結果の全体像
 * 画面表示に必要な全てのフィールドを網羅したメインのデータ形式です。
 */
export interface AnalysisResult {
  overall_min: string;
  overall_max: string;
  overall_min_hz: number;
  overall_max_hz: number;

  // 地声（チェスト）の詳細
  chest_min?: string;
  chest_max?: string;
  chest_min_hz?: number;
  chest_max_hz?: number;
  chest_count?: number;
  chest_ratio?: number;

  // 裏声（ファルセット）の詳細
  falsetto_min?: string;
  falsetto_max?: string;
  falsetto_min_hz?: number;
  falsetto_max_hz?: number;
  falsetto_count?: number;
  falsetto_ratio?: number;

  singing_analysis?: SingingAnalysis;
  voice_type?: VoiceType;
  recommended_songs?: RecommendedSong[];
  similar_artists?: SimilarArtist[];
  error?: string;
}

/** ユーザーの音域データ（楽曲とのマッチング用） */
export interface UserRange {
  chest_min_hz: number;
  chest_max_hz: number;
  falsetto_max_hz?: number;
}

/** 過去の履歴を合算した「統合音域」のデータ形式 */
export interface IntegratedVocalRange {
  overall_min?: string;
  overall_max?: string;
  overall_min_hz?: number;
  overall_max_hz?: number;
  chest_min?: string;
  chest_max?: string;
  chest_min_hz?: number;
  chest_max_hz?: number;
  falsetto_max?: string;
  falsetto_max_hz?: number;
  chest_ratio?: number;
  falsetto_ratio?: number;
  data_count: number;  
  limit: number;       
  singing_analysis?: SingingAnalysis;
  voice_type?: VoiceType;
  recommended_songs?: RecommendedSong[];
  similar_artists?: SimilarArtist[];
}

// ── API 関数 ──────────────────────────────────────────
// 実際にサーバーにデータを送ったり、受け取ったりする関数群です。

/** * マイクで録音した音声を解析する関数 
 *
 */
export const analyzeVoice = async (blob: Blob, noFalsetto: boolean = false): Promise<AnalysisResult> => {
  const formData = new FormData();
  formData.append("file", blob, "recording.webm");
  if (noFalsetto) formData.append("no_falsetto", "true");
  const res = await API.post<AnalysisResult>("/analyze", formData);
  return res.data;
};

/** * アップロードした音源（カラオケなど）を解析する関数 
 *
 */
export const analyzeKaraoke = async (
  file: File | Blob,
  filename: string,
  noFalsetto: boolean = false,
): Promise<AnalysisResult> => {
  const formData = new FormData();
  formData.append("file", file, filename);
  if (noFalsetto) formData.append("no_falsetto", "true");
  const res = await API.post<AnalysisResult>("/analyze-karaoke", formData);
  return res.data;
};

/** 楽曲検索の返答形式 */
export interface SongsResponse {
  songs: Song[];
  total: number;
}

/** * 楽曲の一覧や検索結果を取得する関数 
 *
 */
export const getSongs = async (
  limit: number = 20,
  offset: number = 0,
  query: string = "",
  userRange?: UserRange | null,
): Promise<SongsResponse> => {
  const params: Record<string, any> = { limit, offset };
  if (query) params.q = query;
  if (userRange) {
    params.chest_min_hz = userRange.chest_min_hz;
    params.chest_max_hz = userRange.chest_max_hz;
    if (userRange.falsetto_max_hz) {
      params.falsetto_max_hz = userRange.falsetto_max_hz;
    }
  }
  const res = await API.get<SongsResponse>("/songs", { params });
  return res.data;
};

/** アーティストの基本情報 */
export interface Artist {
  id: number;
  name: string;
  slug: string;
  song_count: number;
  reading: string;
}

/** アーティスト一覧の返答形式 */
export interface ArtistsResponse {
  artists: Artist[];
  total: number;
}

/** * アーティスト一覧をページごとに取得する関数 
 *
 */
export const getArtists = async (
  limit: number = 10,
  offset: number = 0,
  query: string = "",
): Promise<ArtistsResponse> => {
  const params: Record<string, any> = { limit, offset };
  if (query) params.q = query;
  const res = await API.get<ArtistsResponse>("/artists", { params });
  return res.data;
};

/** 特定のアーティストに紐づく楽曲を全て取得する関数 */
export const getArtistSongs = async (
  artistId: number,
  userRange?: UserRange | null,
): Promise<Song[]> => {
  const params: Record<string, any> = {};
  if (userRange) {
    params.chest_min_hz = userRange.chest_min_hz;
    params.chest_max_hz = userRange.chest_max_hz;
    if (userRange.falsetto_max_hz) {
      params.falsetto_max_hz = userRange.falsetto_max_hz;
    }
  }
  const res = await API.get<Song[]>(`/artists/${artistId}/songs`, { params });
  return res.data;
};

/** 自分がお気に入りに登録したアーティスト一覧を取得する関数 */
export const getFavoriteArtists = async (): Promise<FavoriteArtist[]> => {
  const res = await API.get<FavoriteArtist[]>("/favorite-artists");
  return res.data;
};

/** アーティストをお気に入りに追加する関数 */
export const addFavoriteArtist = async (artistId: number, artistName: string): Promise<FavoriteArtist> => {
  const res = await API.post<FavoriteArtist>("/favorite-artists", {
    artist_id: artistId,
    artist_name: artistName,
  });
  return res.data;
};

/** アーティストをお気に入りから削除する関数 */
export const removeFavoriteArtist = async (artistId: number): Promise<{ message: string }> => {
  const res = await API.delete<{ message: string }>(`/favorite-artists/${artistId}`);
  return res.data;
};

// ── お気に入り楽曲 API ─────────────────────────────────

/** お気に入り楽曲の一覧を取得する関数 */
export const getFavorites = async (limit = 100): Promise<FavoriteSong[]> => {
  const res = await API.get("/favorites", { params: { limit } });
  return res.data;
};

/** 楽曲をお気に入りに追加する関数 */
export const addFavorite = async (songId: number) => {
  const res = await API.post("/favorites", { song_id: songId });
  return res.data;
};

/** 楽曲をお気に入りから削除する関数 */
export const removeFavorite = async (songId: number) => {
  await API.delete(`/favorites/${songId}`);
};

/** 指定した曲がお気に入り登録済みか確認する関数 */
export const checkFavorite = async (songId: number): Promise<boolean> => {
  const res = await API.get(`/favorites/check/${songId}`);
  return res.data.is_favorite;
};

/** 解析履歴の1件分のデータ形式 */
export interface AnalysisHistoryRecord {
  id: string;
  user_id: string;
  vocal_range_min: string | null;
  vocal_range_max: string | null;
  falsetto_max: string | null;
  source_type: string;
  file_name: string | null;
  created_at: string;
  result_json?: AnalysisResult | null;
}

/** 過去の全ての解析履歴を取得する関数 */
export const getAnalysisHistory = async (limit = 50): Promise<AnalysisHistoryRecord[]> => {
  const res = await API.get<AnalysisHistoryRecord[]>("/analysis/history", { params: { limit } });
  return res.data;
};

/** 特定の解析履歴を削除する関数 */
export const deleteAnalysisHistory = async (recordId: string): Promise<{ message: string }> => {
  const res = await API.delete(`/analysis/history/${recordId}`);
  return res.data;
};

/** * 直近の履歴を元に「統合された音域」を取得する関数 
 *
 */
export const getIntegratedVocalRange = async (limit = 20): Promise<IntegratedVocalRange> => {
  const res = await API.get<IntegratedVocalRange>("/analysis/integrated-range", { params: { limit } });
  return res.data;
};