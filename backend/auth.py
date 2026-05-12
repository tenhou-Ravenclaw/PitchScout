"""
auth.py — Supabase 認証ヘルパー

FastAPI の Depends で使う認証関数と、メール/パスワード認証のラッパーを提供する。
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from db.users import supabase
from dotenv import load_dotenv

load_dotenv()

security = HTTPBearer()


def _ensure_auth_available() -> None:
    """
    Supabase 認証機能の利用可否を確認する。

    Raises:
        HTTPException(503): Supabase が未設定の場合。
    """
    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="認証機能は現在利用できません",
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, object]:
    """
    HTTP ヘッダーから JWT トークンを取得し、ユーザー情報を返す。

    FastAPI の Depends で保護エンドポイントに使用する。

    Args:
        credentials: HTTPBearer が抽出した認証情報。

    Returns:
        Supabase ユーザーオブジェクトの辞書表現。

    Raises:
        HTTPException(401): トークンが無効、またはユーザーが存在しない場合。
        HTTPException(503): Supabase が未設定の場合。
    """
    _ensure_auth_available()
    token = credentials.credentials

    try:
        # Supabase でトークンを検証（JWT 署名検証は Supabase SDK が実施）
        user = supabase.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なトークンです",
            )
        return user.user.model_dump()
    except HTTPException:
        # すでに適切な HTTPException が raise されている場合はそのまま再送出
        raise
    except Exception as e:
        print(f"[ERROR] 認証トークン検証失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証に失敗しました",
        )


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> dict[str, object] | None:
    """
    オプショナルな認証（ログインしていなくてもアクセス可能）。

    ログイン済みの場合はユーザー情報を返し、未ログインなら None を返す。
    認証エラー時はログ出力した上で None を返す（エンドポイントは継続動作する）。

    Args:
        credentials: HTTPBearer(auto_error=False) が抽出した認証情報。未認証なら None。

    Returns:
        ユーザー情報の辞書。未認証・認証失敗時は None。
    """
    if not credentials or supabase is None:
        return None

    try:
        user = supabase.auth.get_user(credentials.credentials)
        return user.user.model_dump() if (user and user.user) else None
    except Exception as e:
        print(f"[WARN] オプショナル認証失敗（エンドポイントは継続）: {e}")
        return None


# ============================================================
# 認証関連の関数
# ============================================================


def sign_up_with_email(
    email: str,
    password: str,
    display_name: str | None = None,
) -> dict[str, object]:
    """
    メールアドレスとパスワードでユーザー登録する。

    Args:
        email: メールアドレス。
        password: パスワード（8文字以上）。
        display_name: 表示名（任意）。

    Returns:
        user と session を含む辞書。

    Raises:
        HTTPException(400): Supabase でのサインアップに失敗した場合。
        HTTPException(503): Supabase が未設定の場合。
    """
    _ensure_auth_available()
    try:
        user_data = {}
        if display_name:
            user_data["display_name"] = display_name

        response = supabase.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {"data": user_data},
            }
        )

        return {
            "user": response.user.model_dump() if response.user else None,
            "session": response.session.model_dump() if response.session else None,
        }
    except Exception as e:
        print(f"[ERROR] サインアップ失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="サインアップに失敗しました",
        )


def sign_in_with_email(email: str, password: str) -> dict[str, object]:
    """
    メールアドレスとパスワードでログインする。

    Args:
        email: メールアドレス。
        password: パスワード。

    Returns:
        user と session を含む辞書。

    Raises:
        HTTPException(401): ログインに失敗した場合。
        HTTPException(503): Supabase が未設定の場合。
    """
    _ensure_auth_available()
    try:
        response = supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )

        return {
            "user": response.user.model_dump() if response.user else None,
            "session": response.session.model_dump() if response.session else None,
        }
    except Exception as e:
        print(f"[ERROR] ログイン失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ログインに失敗しました",
        )


def sign_out() -> bool:
    """
    ログアウトする。

    Returns:
        成功した場合 True、失敗した場合 False。

    Raises:
        HTTPException(503): Supabase が未設定の場合。
    """
    _ensure_auth_available()
    try:
        supabase.auth.sign_out()
        return True
    except Exception as e:
        print(f"[ERROR] ログアウト失敗: {e}")
        return False


def refresh_session(refresh_token: str) -> dict[str, object]:
    """
    リフレッシュトークンでセッションを更新する。

    Args:
        refresh_token: Supabase が発行したリフレッシュトークン。

    Returns:
        user と session を含む辞書。

    Raises:
        HTTPException(401): セッション更新に失敗した場合。
        HTTPException(503): Supabase が未設定の場合。
    """
    _ensure_auth_available()
    try:
        response = supabase.auth.refresh_session(refresh_token)
        return {
            "user": response.user.model_dump() if response.user else None,
            "session": response.session.model_dump() if response.session else None,
        }
    except Exception as e:
        print(f"[ERROR] セッション更新失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="セッション更新に失敗しました",
        )


def request_password_reset(email: str) -> bool:
    """
    パスワードリセットメールを送信する。

    Args:
        email: リセット対象のメールアドレス。

    Returns:
        送信成功なら True、失敗なら False。

    Raises:
        HTTPException(503): Supabase が未設定の場合。
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
    パスワードを更新する。

    Args:
        user_id: 更新対象の Supabase ユーザー ID。
        new_password: 新しいパスワード。

    Returns:
        更新成功なら True、失敗なら False。

    Raises:
        HTTPException(503): Supabase が未設定の場合。
    """
    _ensure_auth_available()
    try:
        supabase.auth.admin.update_user_by_id(
            user_id,
            {"password": new_password},
        )
        return True
    except Exception as e:
        print(f"[ERROR] パスワード更新失敗: {e}")
        return False
