"""
認証エンドポイント (/auth/*)
"""
from fastapi import APIRouter, Depends, HTTPException
from auth import (
    get_current_user,
    sign_up_with_email, sign_in_with_email, sign_out,
    refresh_session, request_password_reset, update_password,
)
from models import (
    SignUpRequest, SignInRequest, RefreshTokenRequest,
    PasswordResetRequest, PasswordUpdateRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup")
def signup(data: SignUpRequest) -> dict:
    """メールアドレスでユーザー登録"""
    return sign_up_with_email(data.email, data.password, data.display_name)


@router.post("/signin")
def signin(data: SignInRequest) -> dict:
    """メールアドレスでログイン"""
    return sign_in_with_email(data.email, data.password)


@router.post("/signout")
def signout_endpoint(user: dict = Depends(get_current_user)) -> dict:
    """ログアウト"""
    success = sign_out(str(user.get("__access_token", "")))
    if not success:
        raise HTTPException(status_code=400, detail="ログアウトに失敗しました")
    return {"message": "ログアウトしました"}


@router.post("/refresh")
def refresh(data: RefreshTokenRequest) -> dict:
    """セッションをリフレッシュ"""
    return refresh_session(data.refresh_token)


@router.post("/reset-password")
def reset_password(data: PasswordResetRequest) -> dict:
    """パスワードリセットメールを送信"""
    success = request_password_reset(data.email)
    if success:
        return {"message": "パスワードリセットメールを送信しました"}
    raise HTTPException(status_code=400, detail="メール送信に失敗しました")


@router.post("/update-password")
def update_password_endpoint(
    data: PasswordUpdateRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    """パスワードを更新（要ログイン）"""
    success = update_password(str(user.get("__access_token", "")), data.new_password)
    if success:
        return {"message": "パスワードを更新しました"}
    raise HTTPException(status_code=400, detail="パスワード更新に失敗しました")
