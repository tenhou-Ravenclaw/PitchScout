/**
 * API でやり取りするデータ型をまとめたファイル
 */

export interface SingingAnalysis {
  /** 総合スコア */
  overall_score: number;
  /** 音域評価スコア */
  range_score: number;
  /** 音域幅（半音数） */
  range_semitones: number;
  /** 安定性スコア */
  stability_score: number;
  /** 表現力スコア */
  expression_score: number;
}

/** 声質分類情報です。 */
export interface VoiceType {
  /** 声質タイプ名 */
  voice_type?: string;
  /** 音域クラス */
  range_class?: string;
  /** 説明文 */
  description?: string;
}

/** 推薦楽曲の要約情報です。 */
export interface RecommendedSong {
  /** 楽曲ID */
  id: number;
  /** 楽曲名 */
  title: string;
  /** アーティスト名 */
  artist: string;
  /** 最低音 */
  lowest_note: string | null;
  /** 最高音 */
  highest_note: string | null;
  /** マッチングスコア */
  match_score: number;
  /** 推奨キー変更量 */
  recommended_key?: number;
  /** 適合度ラベル */
  fit?: string;
}

/** 類似アーティスト情報です。 */
export interface SimilarArtist {
  /** アーティストID */
  id: number;
  /** アーティスト名 */
  name: string;
  /** 代表的な最低音 */
  typical_lowest: string;
  /** 代表的な最高音 */
  typical_highest: string;
  /** 類似度スコア */
  similarity_score: number;
}

/** 楽曲データの基本情報です。 */
export interface Song {
  /** 楽曲ID */
  id: number;
  /** アーティストID */
  artist_id: number;
  /** 楽曲名 */
  title: string;
  /** アーティスト名 */
  artist: string;
  /** アーティスト読み */
  artist_reading?: string;
  /** アーティストslug */
  artist_slug?: string;
  /** 最低音 */
  lowest_note: string | null;
  /** 最高音 */
  highest_note: string | null;
  /** 裏声最高音 */
  falsetto_note: string | null;
  /** 補足メモ */
  note: string | null;
  /** データ出典 */
  source: string;
  /** 推奨キー変更量 */
  recommended_key?: number;
  /** 適合度ラベル */
  fit?: string;
}

/** お気に入りアーティストレコードです。 */
export interface FavoriteArtist {
  /** お気に入りレコードID */
  id: string;
  /** アーティストID */
  artist_id: number;
  /** アーティスト名 */
  artist_name: string;
  /** 登録日時 */
  created_at: string;
}

/** お気に入り楽曲レコードです。 */
export interface FavoriteSong {
  /** お気に入りレコードID */
  favorite_id: string;
  /** 楽曲ID */
  song_id: number;
  /** 楽曲名 */
  title: string;
  /** アーティスト名 */
  artist: string | null;
  /** 最低音 */
  lowest_note: string | null;
  /** 最高音 */
  highest_note: string | null;
  /** 裏声最高音 */
  falsetto_note: string | null;
  /** 登録日時 */
  created_at: string;
}

/** 1回分の声域分析結果です。 */
export interface AnalysisResult {
  /** 全体最低音（音名） */
  overall_min: string;
  /** 全体最高音（音名） */
  overall_max: string;
  /** 全体最低音（Hz） */
  overall_min_hz: number;
  /** 全体最高音（Hz） */
  overall_max_hz: number;

  /** 地声最低音（音名） */
  chest_min?: string;
  /** 地声最高音（音名） */
  chest_max?: string;
  /** 地声最低音（Hz） */
  chest_min_hz?: number;
  /** 地声最高音（Hz） */
  chest_max_hz?: number;
  /** 地声検出点数 */
  chest_count?: number;
  /** 地声割合 */
  chest_ratio?: number;

  /** 裏声最低音（音名） */
  falsetto_min?: string;
  /** 裏声最高音（音名） */
  falsetto_max?: string;
  /** 裏声最低音（Hz） */
  falsetto_min_hz?: number;
  /** 裏声最高音（Hz） */
  falsetto_max_hz?: number;
  /** 裏声検出点数 */
  falsetto_count?: number;
  /** 裏声割合 */
  falsetto_ratio?: number;

  /** 歌唱分析スコア */
  singing_analysis?: SingingAnalysis;
  /** 声質分類 */
  voice_type?: VoiceType;
  /** 推薦楽曲 */
  recommended_songs?: RecommendedSong[];
  /** 類似アーティスト */
  similar_artists?: SimilarArtist[];
  /** エラーメッセージ */
  error?: string;
}

/** ユーザー音域（Hz）です。 */
export interface UserRange {
  /** 地声最低Hz */
  chest_min_hz: number;
  /** 地声最高Hz */
  chest_max_hz: number;
  /** 裏声最高Hz */
  falsetto_max_hz?: number;
}

/** 楽曲一覧APIレスポンスです。 */
export interface SongsResponse {
  /** 楽曲配列 */
  songs: Song[];
  /** 総件数 */
  total: number;
}

/** アーティスト情報です。 */
export interface Artist {
  /** アーティストID */
  id: number;
  /** 名前 */
  name: string;
  /** URL向けslug */
  slug: string;
  /** 楽曲数 */
  song_count: number;
  /** 読み仮名 */
  reading: string;
}

/** アーティスト一覧APIレスポンスです。 */
export interface ArtistsResponse {
  /** アーティスト配列 */
  artists: Artist[];
  /** 総件数 */
  total: number;
}

/** 分析履歴レコードです。 */
export interface AnalysisHistoryRecord {
  /** 履歴ID */
  id: string;
  /** ユーザーID */
  user_id: string;
  /** 地声最低音 */
  vocal_range_min: string | null;
  /** 地声最高音 */
  vocal_range_max: string | null;
  /** 裏声最高音 */
  falsetto_max: string | null;
  /** 音源種別 */
  source_type: string;
  /** 元ファイル名 */
  file_name: string | null;
  /** 作成日時 */
  created_at: string;
  /** 詳細結果JSON */
  result_json?: AnalysisResult | null;
}

/** 複数履歴を統合した声域分析結果です。 */
export interface IntegratedVocalRange {
  /** 全体最低音（音名） */
  overall_min?: string;
  /** 全体最高音（音名） */
  overall_max?: string;
  /** 全体最低音（Hz） */
  overall_min_hz?: number;
  /** 全体最高音（Hz） */
  overall_max_hz?: number;
  /** 地声最低音（音名） */
  chest_min?: string;
  /** 地声最高音（音名） */
  chest_max?: string;
  /** 地声最低音（Hz） */
  chest_min_hz?: number;
  /** 地声最高音（Hz） */
  chest_max_hz?: number;
  /** 裏声最高音（音名） */
  falsetto_max?: string;
  /** 裏声最高音（Hz） */
  falsetto_max_hz?: number;
  /** 地声割合 */
  chest_ratio?: number;
  /** 裏声割合 */
  falsetto_ratio?: number;
  /** 統合件数 */
  data_count: number;
  /** 利用した履歴上限 */
  limit: number;
  /** 歌唱分析スコア */
  singing_analysis?: SingingAnalysis;
  /** 声質分類 */
  voice_type?: VoiceType;
  /** 推薦楽曲 */
  recommended_songs?: RecommendedSong[];
  /** 類似アーティスト */
  similar_artists?: SimilarArtist[];
}
