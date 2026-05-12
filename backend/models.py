"""
models.py — FastAPI 用の Pydantic リクエスト/レスポンスモデル

全エンドポイントの入出力を型安全に定義する。
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Literal
from datetime import datetime


# ============================================================
# 認証関連
# ============================================================

class SignUpRequest(BaseModel):
    """ユーザー新規登録リクエスト。"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="パスワード（8文字以上）")
    display_name: str | None = Field(None, max_length=100)


class SignInRequest(BaseModel):
    """メール+パスワードによるログインリクエスト。"""
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """セッション更新リクエスト。"""
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """パスワードリセットメール送信リクエスト。"""
    email: EmailStr


class PasswordUpdateRequest(BaseModel):
    """パスワード変更リクエスト（認証済みユーザー向け）。"""
    new_password: str = Field(..., min_length=8)


# ============================================================
# ユーザープロファイル
# ============================================================

class UserProfileUpdate(BaseModel):
    """ユーザープロファイル更新リクエスト（部分更新可）。"""
    display_name: str | None = Field(None, max_length=100)
    avatar_url: str | None = None
    dam_account_id: str | None = None


class VocalRangeUpdate(BaseModel):
    """ユーザーの声域情報を手動更新するリクエスト。"""
    vocal_range_min: str | None = Field(None, description="地声最低音（例: mid1C）")
    vocal_range_max: str | None = Field(None, description="地声最高音（例: hiA）")
    falsetto_max: str | None = Field(None, description="裏声最高音（例: hiE）")


# ============================================================
# 分析履歴
# ============================================================

class AnalysisCreate(BaseModel):
    """分析結果の履歴保存リクエスト。"""
    vocal_range_min: str | None = None
    vocal_range_max: str | None = None
    falsetto_max: str | None = None
    source_type: Literal["microphone", "karaoke", "file"] = Field(..., description="音声ソース種別")
    file_name: str | None = None


class AnalysisUpdate(BaseModel):
    """分析履歴レコードの更新リクエスト（ファイル名の変更等）。"""
    file_name: str | None = Field(None, max_length=200)


class AnalysisResponse(BaseModel):
    """分析履歴レコードのレスポンス。"""
    id: str
    user_id: str
    vocal_range_min: str | None
    vocal_range_max: str | None
    falsetto_max: str | None
    source_type: str
    file_name: str | None
    created_at: datetime


# ============================================================
# お気に入り楽曲
# ============================================================

class FavoriteSongAdd(BaseModel):
    """お気に入り楽曲追加リクエスト。"""
    song_id: int


class BatchFavoriteCheckRequest(BaseModel):
    """複数楽曲のお気に入り状態を一括確認するリクエスト。"""
    song_ids: list[int] = Field(
        ...,
        max_length=100,
        description="確認する楽曲 ID のリスト（最大100件）",
    )


class FavoriteSongResponse(BaseModel):
    """お気に入り楽曲のレスポンス（楽曲情報を結合済み）。"""
    favorite_id: str
    song_id: int
    title: str
    artist: str | None
    lowest_note: str | None
    highest_note: str | None
    falsetto_note: str | None
    created_at: datetime


# ============================================================
# お気に入りアーティスト
# ============================================================

class FavoriteArtistAdd(BaseModel):
    """お気に入りアーティスト追加リクエスト。"""
    artist_id: int
    artist_name: str = Field(..., max_length=200, description="アーティスト名（songs.dbから取得）")


class FavoriteArtistResponse(BaseModel):
    """お気に入りアーティストのレスポンス。"""
    id: str
    artist_id: int
    artist_name: str
    created_at: datetime


# ============================================================
# 楽曲・アーティスト
# ============================================================

class SongResponse(BaseModel):
    """楽曲情報レスポンス（SQLite songs テーブルの公開フィールド）。"""
    id: int
    title: str
    artist: str | None
    lowest_note: str | None
    highest_note: str | None
    falsetto_note: str | None
    note: str | None
    source: str


class ArtistResponse(BaseModel):
    """アーティスト情報レスポンス。"""
    id: int
    name: str
    slug: str
    song_count: int