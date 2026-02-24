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
  fit?: string;
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
