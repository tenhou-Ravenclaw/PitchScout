"""
FastAPI用のPydanticモデル
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional
from datetime import datetime


# ============================================================
# 認証関連
# ============================================================

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="パスワード（8文字以上）")
    display_name: Optional[str] = Field(None, max_length=100)


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordUpdateRequest(BaseModel):
    new_password: str = Field(..., min_length=8)


# ============================================================
# ユーザープロファイル
# ============================================================

class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = None
    dam_account_id: Optional[str] = None


class VocalRangeUpdate(BaseModel):
    vocal_range_min: Optional[str] = Field(None, description="地声最低音（例: mid1C）")
    vocal_range_max: Optional[str] = Field(None, description="地声最高音（例: hiA）")
    falsetto_max: Optional[str] = Field(None, description="裏声最高音（例: hiE）")


# ============================================================
# 分析履歴
# ============================================================

class AnalysisCreate(BaseModel):
    vocal_range_min: Optional[str] = None
    vocal_range_max: Optional[str] = None
    falsetto_max: Optional[str] = None
    source_type: Literal["microphone", "karaoke", "file"] = Field(..., description="音声ソース種別")
    file_name: Optional[str] = None


class AnalysisUpdate(BaseModel):
    file_name: Optional[str] = Field(None, max_length=200)


class AnalysisResponse(BaseModel):
    id: str
    user_id: str
    vocal_range_min: Optional[str]
    vocal_range_max: Optional[str]
    falsetto_max: Optional[str]
    source_type: str
    file_name: Optional[str]
    created_at: datetime


# ============================================================
# お気に入り楽曲
# ============================================================

class FavoriteSongAdd(BaseModel):
    song_id: int


class BatchFavoriteCheckRequest(BaseModel):
    """複数楽曲のお気に入り状態を一括確認するリクエスト。"""
    song_ids: list[int] = Field(
        ...,
        max_length=100,
        description="確認する楽曲 ID のリスト（最大100件）",
    )


class FavoriteSongResponse(BaseModel):
    favorite_id: str
    song_id: int
    title: str
    artist: Optional[str]
    lowest_note: Optional[str]
    highest_note: Optional[str]
    falsetto_note: Optional[str]
    created_at: datetime


# ============================================================
# お気に入りアーティスト
# ============================================================

class FavoriteArtistAdd(BaseModel):
    artist_id: int
    artist_name: str = Field(..., max_length=200, description="アーティスト名（songs.dbから取得）")


class FavoriteArtistResponse(BaseModel):
    id: str
    artist_id: int
    artist_name: str
    created_at: datetime


# ============================================================
# 楽曲・アーティスト
# ============================================================

class SongResponse(BaseModel):
    id: int
    title: str
    artist: Optional[str]
    lowest_note: Optional[str]
    highest_note: Optional[str]
    falsetto_note: Optional[str]
    note: Optional[str]
    source: str


class ArtistResponse(BaseModel):
    id: int
    name: str
    slug: str
    song_count: int