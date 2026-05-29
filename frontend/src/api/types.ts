
/**
 * API でやり取りするデータ型をまとめたファイル
 */

export interface SingingAnalysis {
  overall_score: number;
  range_score: number;
  range_semitones: number;
  stability_score: number;
  expression_score: number;
}

export interface VoiceType {
  voice_type?: string;
  range_class?: string;
  description?: string;
}

export type KeyFit = "perfect" | "good" | "ok" | "hard" | undefined;

export interface RecommendedSong {
  id: number;
  title: string;
  artist: string;
  lowest_note: string | null;
  highest_note: string | null;
  match_score: number;
  recommended_key?: number;
  fit?: KeyFit;
}

export interface SimilarArtist {
  id: number;
  name: string;
  typical_lowest: string;
  typical_highest: string;
  similarity_score: number;
}

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
  fit?: KeyFit;
}

export interface FavoriteArtist {
  id: string;
  artist_id: number;
  artist_name: string;
  created_at: string;
}

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

export interface AnalysisResult {
  overall_min: string;
  overall_max: string;
  overall_min_hz: number;
  overall_max_hz: number;

  chest_min?: string;
  chest_max?: string;
  chest_min_hz?: number;
  chest_max_hz?: number;
  chest_count?: number;
  chest_ratio?: number;

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

export interface UserRange {
  chest_min_hz: number;
  chest_max_hz: number;
  falsetto_max_hz?: number;
}

export interface SongsResponse {
  songs: Song[];
  total: number;
}

export interface Artist {
  id: number;
  name: string;
  slug: string;
  song_count: number;
  reading: string;
}

export interface ArtistsResponse {
  artists: Artist[];
  total: number;
}

export interface ArtistIndexPageResponse {
  page: number;
}

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

export interface TotalVocalRange extends Partial<AnalysisResult> {
  data_count: number;
  limit: number;
  singing_analysis?: SingingAnalysis;
  voice_type?: VoiceType;
  recommended_songs?: RecommendedSong[];
  similar_artists?: SimilarArtist[];
}

/** 分析タイムラインの1点（1回の分析結果） */
export interface TimelinePoint {
  /** 分析日時 (ISO 8601) */
  date: string;
  /** 地声最低音ラベル（例: "mid1C"） */
  chest_min: string | null;
  /** 地声最高音ラベル（例: "mid2G"） */
  chest_max: string | null;
  /** 裏声最高音ラベル（例: "hiC"） */
  falsetto_max: string | null;
  /** 地声最低音 Hz */
  chest_min_hz: number | null;
  /** 地声最高音 Hz */
  chest_max_hz: number | null;
  /** 裏声最高音 Hz */
  falsetto_max_hz: number | null;
}

/** 安定音域（直近 N 件中 M 回以上出現した音域） */
export interface StableRange {
  /** 安定して出ている地声最低音ラベル */
  chest_min: string | null;
  /** 安定して出ている地声最高音ラベル */
  chest_max: string | null;
  /** 安定して出ている裏声最高音ラベル */
  falsetto_max: string | null;
}

/** GET /analysis/timeline レスポンス */
export interface AnalysisTimeline {
  /** 古い順に並んだ分析タイムラインポイントの配列 */
  timeline: TimelinePoint[];
  /** 安定音域（直近 N 件中 4 回以上出現） */
  stable_range: StableRange;
}
