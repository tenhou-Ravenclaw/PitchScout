"""
Supabase認証のヘルパー関数
"""
import os
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from database_supabase import supabase
from dotenv import load_dotenv

load_dotenv()

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    HTTPヘッダーからJWTトークンを取得し、ユーザー情報を返す
    
    使い方:
        @app.get("/protected")
        def protected_route(user: dict = Depends(get_current_user)):
            return {"user_id": user["id"]}
    """
    token = credentials.credentials
    
    try:
        # Supabaseでトークンを検証
        user = supabase.auth.get_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なトークンです"
            )
        return user.user.model_dump()
    except HTTPException:
        # すでに適切な HTTPException が raise されている場合はそのまま再送出
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"認証エラー: {str(e)}"
        )


def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[Dict[str, Any]]:
    """
    オプショナルな認証（ログインしていなくてもアクセス可能）
    ログイン済みの場合はユーザー情報を返す
    """
    if not credentials:
        return None
    
    try:
        user = supabase.auth.get_user(credentials.credentials)
        return user.user.model_dump() if user else None
    except Exception:
        return None


# ============================================================
# 認証関連の関数
# ============================================================

def sign_up_with_email(email: str, password: str, display_name: Optional[str] = None) -> Dict[str, Any]:
    """
    メールアドレスとパスワードでユーザー登録
    """
    try:
        user_data = {}
        if display_name:
            user_data["display_name"] = display_name
        
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": user_data
            }
        })
        
        return {
            "user": response.user.model_dump() if response.user else None,
            "session": response.session.model_dump() if response.session else None
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"サインアップエラー: {str(e)}"
        )


def sign_in_with_email(email: str, password: str) -> Dict[str, Any]:
    """
    メールアドレスとパスワードでログイン
    """
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        return {
            "user": response.user.model_dump() if response.user else None,
            "session": response.session.model_dump() if response.session else None
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"ログインエラー: {str(e)}"
        )


def sign_out(token: str) -> bool:
    """
    ログアウト
    """
    try:
        supabase.auth.sign_out()
        return True
    except Exception:
        return False


def refresh_session(refresh_token: str) -> Dict[str, Any]:
    """
    リフレッシュトークンを使ってセッションを更新
    """
    try:
        response = supabase.auth.refresh_session(refresh_token)
        return {
            "user": response.user.model_dump() if response.user else None,
            "session": response.session.model_dump() if response.session else None
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"トークン更新エラー: {str(e)}"
        )


def request_password_reset(email: str) -> bool:
    """
    パスワードリセットメールを送信
    """
    try:
        supabase.auth.reset_password_for_email(email)
        return True
    except Exception:
        return False


def update_password(token: str, new_password: str) -> bool:
    """
    パスワードを更新
    """
    try:
        supabase.auth.update_user({
            "password": new_password
        })
        return True
    except Exception:
        return False
