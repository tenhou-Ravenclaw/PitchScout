-- ============================================================
-- Supabaseスキーマ更新（ダッシュボードのSQL Editorで実行）
-- 既存テーブルに対する差分マイグレーション
-- ============================================================

-- artists に reading カラム追加（ふりがな検索用）
ALTER TABLE artists ADD COLUMN IF NOT EXISTS reading TEXT;

-- songs の UNIQUE 制約をマージ済み向けに変更
-- （旧: artist_id + title + source → 新: artist_id + title）
ALTER TABLE songs DROP CONSTRAINT IF EXISTS songs_artist_id_title_source_key;
ALTER TABLE songs ADD CONSTRAINT songs_artist_id_title_key UNIQUE(artist_id, title);

-- analysis_history に result_json カラム追加（分析結果の詳細保存用）
ALTER TABLE analysis_history ADD COLUMN IF NOT EXISTS result_json JSONB;

-- favorite_artists に artist_name カラム追加（表示用）
ALTER TABLE favorite_artists ADD COLUMN IF NOT EXISTS artist_name TEXT;
