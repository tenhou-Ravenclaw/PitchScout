/**
 * 【api.ts】
 * 役割：サーバー（バックエンド）と通信するための「窓口」です。
 * データの送り方（関数）や、データの形（型定義）をここにまとめています。
 * * 💡 設計図 (FRONTEND_STRUCTURE.md) に基づく改善案：
 * 現在このファイルは「モノリス（巨大な1つの塊）」になっています。
 * 将来的には「共通設定」「録音系」「楽曲系」のようにファイルを分けると管理が楽になります。
 */

import axios from "axios";
import { supabase } from "./supabaseClient";

/** サーバーからの返答を待つ最大時間（10分） */
const TIMEOUT_MS = 600000; 

/** * ── 共通設定 (Axios Client) ──
 * 💡 移動先案: src/lib/axios.ts
 * サーバーの住所（URL）や待ち時間を設定した「通信機」を作成します。
 */
const API = axios.create({
  // 本番環境（Vercel等）なら '/api'、自分のPCでテスト中なら 'http://127.0.0.1:8000' を自動で使い分けます
  baseURL: process.env.REACT_APP_API_URL || (process.env.NODE_ENV === "production" ? "/api" : "http://127.0.0.1:8000"),
  timeout: TIMEOUT_MS,
});

/** * ── 認証の自動化 (Interceptors) ──
 * 通信をする「直前」に、ログイン情報を自動でヘッダーに付け加える仕組みです。
 * これにより、毎回ログイン情報を書かなくても「ログインが必要な機能」が使えます。
 */
API.interceptors.request.use(async (config) => {
  if (supabase) {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (token) {
      // サーバーに対して「私はこのユーザーです」という証明書（トークン）を送ります
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// ── 型定義 (Interfaces) ───────────────────────────────────
// TypeScriptで扱うデータの「形」を決めて、プログラムのミスを防ぎます。
// 💡 移動先案: 各 features/ フォルダ配下の types.ts

/** 歌唱分析の詳細スコア（総合点や安定性など） */
export interface SingingAnalysis {
  overall_score: number;
  range_score: number;
  range_semitones: number;
  stability_score: number;
  expression_score: number;
}

/** 声の種類（テノール、バリトンなど） */
export interface VoiceType {
  voice_type?: string;
  range_class?: string;
  description?: string;
}

/** おすすめされる楽曲のデータ形式 */
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

/** 声質が似ているアーティストの情報 */
export interface SimilarArtist {
  id: number;
  name: string;
  typical_lowest: string;
  typical_highest: string;
  similarity_score: number;
}

/** 一般的な楽曲のデータ形式 */
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

/** お気に入り登録された楽曲 */
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

/** 解析結果の全体をまとめたデータ型 */
export interface AnalysisResult {
  overall_min: string;
  overall_max: string;
  overall_min_hz: number;
  overall_max_hz: number;

  // 地声（チェストボイス）の詳細
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

/** ユーザーの音域（楽曲検索で「歌いやすさ」を判定するために使用） */
export interface UserRange {
  chest_min_hz: number;
  chest_max_hz: number;
  falsetto_max_hz?: number;
}

/** 複数の履歴から計算された「統合音域」データ */
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

// ── API 通信関数 ──────────────────────────────────────────
// ここから下の関数を使って、実際にサーバーからデータを取ってきます。

/** * マイク録音した音声を解析する関数 
 * 💡 移動先案: src/features/karaoke/api/
 */
export const analyzeVoice = async (blob: Blob, noFalsetto: boolean = false): Promise<AnalysisResult> => {
  const formData = new FormData();
  formData.append("file", blob, "recording.webm");
  if (noFalsetto) formData.append("no_falsetto", "true");
  const res = await API.post<AnalysisResult>("/analyze", formData);
  return res.data;
};

/** * アップロードされたカラオケ音源を解析する関数 
 * 💡 移動先案: src/features/karaoke/api/
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

/** 楽曲検索の結果を受け取るための形式 */
export interface SongsResponse {
  songs: Song[];
  total: number;
}

/** * 楽曲の一覧や検索結果を取得する関数 
 * 💡 移動先案: src/features/songs/api/
 */
export const getSongs = async (
  limit: number = 20,
  offset: number = 0,
  query: string = "",
  userRange?: UserRange | null,
): Promise<SongsResponse> => {
  const params: Record<string, any> = { limit, offset };
  if (query) params.q = query;
  // ユーザーの音域がある場合、サーバー側で「推奨キー」を計算してもらうためにデータを送ります
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

/** アーティストの基本データ */
export interface Artist {
  id: number;
  name: string;
  slug: string;
  song_count: number;
  reading: string;
}

/** アーティスト一覧の結果形式 */
export interface ArtistsResponse {
  artists: Artist[];
  total: number;
}

/** * アーティストの一覧を取得する関数（ページネーション対応） 
 * 💡 移動先案: src/features/songs/api/
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

/** * 特定のアーティストが歌っている全楽曲を取得する関数 
 * 💡 移動先案: src/features/songs/api/
 */
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

/** お気に入りアーティストのリストを取得 */
export const getFavoriteArtists = async (): Promise<FavoriteArtist[]> => {
  const res = await API.get<FavoriteArtist[]>("/favorite-artists");
  return res.data;
};

/** アーティストをお気に入りに追加 */
export const addFavoriteArtist = async (artistId: number, artistName: string): Promise<FavoriteArtist> => {
  const res = await API.post<FavoriteArtist>("/favorite-artists", {
    artist_id: artistId,
    artist_name: artistName,
  });
  return res.data;
};

/** アーティストをお気に入りから削除 */
export const removeFavoriteArtist = async (artistId: number): Promise<{ message: string }> => {
  const res = await API.delete<{ message: string }>(`/favorite-artists/${artistId}`);
  return res.data;
};

// ── お気に入り楽曲 API ──
// 💡 移動先案: src/features/songs/api/

/** お気に入り楽曲の一覧を取得（最大100件） */
export const getFavorites = async (limit = 100): Promise<FavoriteSong[]> => {
  const res = await API.get("/favorites", { params: { limit } });
  return res.data;
};

/** 楽曲をお気に入りに追加 */
export const addFavorite = async (songId: number) => {
  const res = await API.post("/favorites", { song_id: songId });
  return res.data;
};

/** 楽曲をお気に入りから削除 */
export const removeFavorite = async (songId: number) => {
  await API.delete(`/favorites/${songId}`);
};

/** 指定した曲がお気に入り済みかどうかをチェック */
export const checkFavorite = async (songId: number): Promise<boolean> => {
  const res = await API.get(`/favorites/check/${songId}`);
  return res.data.is_favorite;
};

/** 1件分の分析履歴レコード */
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

/** * 過去の分析履歴をすべて取得する関数 
 * 💡 移動先案: src/features/songs/api/ (または analysis/api/)
 */
export const getAnalysisHistory = async (limit = 50): Promise<AnalysisHistoryRecord[]> => {
  const res = await API.get<AnalysisHistoryRecord[]>("/analysis/history", { params: { limit } });
  return res.data;
};

/** 特定の履歴を削除 */
export const deleteAnalysisHistory = async (recordId: string): Promise<{ message: string }> => {
  const res = await API.delete(`/analysis/history/${recordId}`);
  return res.data;
};

/** * 直近の解析データを元にした「今のあなたの音域」を取得する関数 
 * 💡 移動先案: src/features/analysis/api/
 */
export const getIntegratedVocalRange = async (limit = 20): Promise<IntegratedVocalRange> => {
  const res = await API.get<IntegratedVocalRange>("/analysis/integrated-range", { params: { limit } });
  return res.data;
};