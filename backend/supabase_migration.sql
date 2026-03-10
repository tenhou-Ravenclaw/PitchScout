-- ============================================================
-- Supabase用データベース設計
-- 実行方法: Supabaseダッシュボードの「SQL Editor」で実行
-- ============================================================

-- ============================================================
-- 1. ユーザープロファイルテーブル
--    Supabase Authのユーザーと1:1で紐付け
-- ============================================================
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT,
    avatar_url TEXT,
    
    -- DAM連携用（将来実装）
    dam_account_id TEXT,
    
    -- 最新の声域データ（プロファイルに表示用）
    current_vocal_range_min TEXT,  -- 例: "mid1C"
    current_vocal_range_max TEXT,  -- 例: "hiA"
    current_falsetto_max TEXT,     -- 例: "hiE"
    
    -- メタデータ
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS (Row Level Security) を有効化
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- プロファイル用ポリシー（重複エラーを防ぐためドロップしてから作成）
DO $$ BEGIN
    DROP POLICY IF EXISTS "Users can view own profile" ON user_profiles;
    DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
END $$;

-- 自分のプロファイルは自分だけが読み書き可能
CREATE POLICY "Users can view own profile" 
    ON user_profiles FOR SELECT 
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" 
    ON user_profiles FOR UPDATE 
    USING (auth.uid() = id);

-- サインアップ時に自動的にプロファイルを作成するトリガー
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (id, email, display_name)
    VALUES (NEW.id, NEW.email, COALESCE(NEW.raw_user_meta_data->>'display_name', NULL));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================
-- 2. 分析履歴テーブル
--    声域の変化を時系列で追跡 / JSON結果の保存に対応
-- ============================================================
CREATE TABLE IF NOT EXISTS analysis_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    
    -- 測定結果
    vocal_range_min TEXT,
    vocal_range_max TEXT,
    falsetto_max TEXT,
    result_json JSONB, -- 分析結果の詳細データ保存用
    
    -- 測定メタデータ
    source_type TEXT NOT NULL CHECK (source_type IN ('microphone', 'karaoke', 'file')),
    file_name TEXT,
    
    -- タイムスタンプ
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE analysis_history ADD COLUMN IF NOT EXISTS result_json JSONB;

-- インデックス
CREATE INDEX IF NOT EXISTS idx_analysis_user_date ON analysis_history(user_id, created_at DESC);

-- RLS
ALTER TABLE analysis_history ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    DROP POLICY IF EXISTS "Users can view own analysis history" ON analysis_history;
    DROP POLICY IF EXISTS "Users can insert own analysis" ON analysis_history;
END $$;

CREATE POLICY "Users can view own analysis history" 
    ON analysis_history FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own analysis" 
    ON analysis_history FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

-- ============================================================
-- 3. 楽曲テーブル（artists, songs）
-- ============================================================

-- アーティストテーブル
CREATE TABLE IF NOT EXISTS artists (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    song_count INTEGER DEFAULT 0,
    reading TEXT  -- ふりがな検索用
);

-- 楽曲テーブル
CREATE TABLE IF NOT EXISTS songs (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    artist_id INTEGER NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
    lowest_note TEXT,
    highest_note TEXT,
    falsetto_note TEXT,
    note TEXT,
    source TEXT DEFAULT 'voice-key.news',
    
    -- 重複防止（マージ済みデータはソースに関係なくアーティスト+タイトルで一意）
    UNIQUE(artist_id, title)
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_songs_title ON songs(title);
CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(artist_id);

-- RLS（楽曲データは全員が閲覧可能）
ALTER TABLE artists ENABLE ROW LEVEL SECURITY;
ALTER TABLE songs ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    DROP POLICY IF EXISTS "Anyone can view artists" ON artists;
    DROP POLICY IF EXISTS "Anyone can view songs" ON songs;
END $$;

CREATE POLICY "Anyone can view artists" 
    ON artists FOR SELECT 
    USING (true);

CREATE POLICY "Anyone can view songs" 
    ON songs FOR SELECT 
    USING (true);

-- ============================================================
-- 4. お気に入り楽曲テーブル
-- ============================================================
CREATE TABLE IF NOT EXISTS favorite_songs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    song_id INTEGER NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 同じ曲を重複してお気に入り登録できないように
    UNIQUE(user_id, song_id)
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorite_songs(user_id, created_at DESC);

-- RLS
ALTER TABLE favorite_songs ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    DROP POLICY IF EXISTS "Users can view own favorites" ON favorite_songs;
    DROP POLICY IF EXISTS "Users can manage own favorites" ON favorite_songs;
END $$;

CREATE POLICY "Users can view own favorites" 
    ON favorite_songs FOR SELECT 
    USING (auth.uid() = user_id);

-- INSERT/UPDATEができるように WITH CHECK を追加
CREATE POLICY "Users can manage own favorites" 
    ON favorite_songs FOR ALL 
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ============================================================
-- 5. お気に入りアーティストテーブル
-- ============================================================
CREATE TABLE IF NOT EXISTS favorite_artists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    artist_id INTEGER NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
    artist_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 同じアーティストを重複してお気に入り登録できないように
    UNIQUE(user_id, artist_id)
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_favorite_artists_user ON favorite_artists(user_id, created_at DESC);

-- RLS
ALTER TABLE favorite_artists ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    DROP POLICY IF EXISTS "Users can manage own favorite artists" ON favorite_artists;
END $$;

CREATE POLICY "Users can manage own favorite artists" 
    ON favorite_artists FOR ALL 
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ============================================================
-- 6. updated_atの自動更新トリガー
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 7. 既存テーブルへのカラム追加・制約変更（冪等）
--    CREATE TABLE IF NOT EXISTS では既存テーブルに新カラムが追加されないため、
--    ALTER TABLE で明示的に追加する。
-- ============================================================

-- artists.reading: ふりがな検索用カラム（Supabase移行時に追加）
ALTER TABLE artists ADD COLUMN IF NOT EXISTS reading TEXT;

-- favorite_artists.artist_name: 表示用アーティスト名
ALTER TABLE favorite_artists ADD COLUMN IF NOT EXISTS artist_name TEXT;

-- songs の UNIQUE 制約を (artist_id, title, source) → (artist_id, title) に変更
-- マージ済みデータではソースに関係なくアーティスト+タイトルで一意
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'songs_artist_id_title_source_key') THEN
        ALTER TABLE songs DROP CONSTRAINT songs_artist_id_title_source_key;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'songs_artist_id_title_key') THEN
        ALTER TABLE songs ADD CONSTRAINT songs_artist_id_title_key UNIQUE (artist_id, title);
    END IF;
END $$;
