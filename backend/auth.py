"""
Supabase認証のヘルパー関数
"""
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from db.users import supabase
from dotenv import load_dotenv

load_dotenv()

security = HTTPBearer()


def _ensure_auth_available() -> None:
    """Supabase認証機能の利用可否を確認する。"""
    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="認証機能は現在利用できません",
        )


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    HTTPヘッダーからJWTトークンを取得し、ユーザー情報を返す
    
    使い方:
        @app.get("/protected")
        def protected_route(user: dict = Depends(get_current_user)):
            return {"user_id": user["id"]}
    """
    _ensure_auth_available()
    token = credentials.credentials
    
    try:
        # Supabaseでトークンを検証（JWT署名検証はSupabase SDKが実施）
        user = supabase.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なトークンです"
            )
        return user.user.model_dump()
    except HTTPException:
        # すでに適切な HTTPException が raise されている場合はそのまま再送出
        raise
    except Exception as e:
        print(f"[ERROR] 認証トークン検証失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証に失敗しました"
        )


def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[Dict[str, Any]]:
    """
    オプショナルな認証（ログインしていなくてもアクセス可能）
    ログイン済みの場合はユーザー情報を返す
    """
    if not credentials or supabase is None:
        return None
    
    try:
        user = supabase.auth.get_user(credentials.credentials)
        return user.user.model_dump() if (user and user.user) else None
    except Exception:
        return None


# ============================================================
# 認証関連の関数
# ============================================================

def sign_up_with_email(email: str, password: str, display_name: Optional[str] = None) -> Dict[str, Any]:
    """
    メールアドレスとパスワードでユーザー登録
    """
    _ensure_auth_available()
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
        print(f"[ERROR] サインアップ失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="サインアップに失敗しました"
        )


def sign_in_with_email(email: str, password: str) -> Dict[str, Any]:
    """
    メールアドレスとパスワードでログイン
    """
    _ensure_auth_available()
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
        print(f"[ERROR] ログイン失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ログインに失敗しました"
        )


def sign_out() -> bool:
    """
    ログアウト
    """
    _ensure_auth_available()
    try:
        supabase.auth.sign_out()
        return True
    except Exception as e:
        print(f"[ERROR] ログアウト失敗: {e}")
        return False


def refresh_session(refresh_token: str) -> Dict[str, Any]:
    """
    リフレッシュトークンを使ってセッションを更新
    """
    _ensure_auth_available()
    try:
        response = supabase.auth.refresh_session(refresh_token)
        return {
            "user": response.user.model_dump() if response.user else None,
            "session": response.session.model_dump() if response.session else None
        }
    except Exception as e:
        print(f"[ERROR] セッション更新失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="セッション更新に失敗しました"
        )


def request_password_reset(email: str) -> bool:
    """
    パスワードリセットメールを送信
    """
    _ensure_auth_available()
    try:
        supabase.auth.reset_password_for_email(email)
        return True
    except Exception as e:
        print(f"[ERROR] パスワードリセットメール送信失敗: {e}")
        return False


def update_password(user_id: str, new_password: str) -> bool:
    """
    パスワードを更新
    """
    _ensure_auth_available()
    try:
        supabase.auth.admin.update_user_by_id(user_id, {
            "password": new_password,
        })
        return True
    except Exception as e:
        print(f"[ERROR] パスワード更新失敗: {e}")
        return False
