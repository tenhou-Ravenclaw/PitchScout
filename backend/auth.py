"""
auth.py — Supabase 認証ヘルパー

FastAPI の Depends で使う認証関数と、メール/パスワード認証のラッパーを提供する。
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx

from db.users import SUPABASE_KEY, SUPABASE_URL, supabase
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


def _auth_rest_headers(access_token: str) -> dict[str, str]:
    """
    Supabase Auth REST API 用ヘッダーを作る。

    admin API ではなく、ユーザー本人の Bearer token で操作するために使う。
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        _ensure_auth_available()
    return {
        "apikey": SUPABASE_KEY or "",
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def _auth_public_headers() -> dict[str, str]:
    """Supabase Auth REST API の公開エンドポイント用ヘッダーを作る。"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        _ensure_auth_available()
    return {
        "apikey": SUPABASE_KEY or "",
        "Content-Type": "application/json",
    }


def _auth_url(path: str) -> str:
    """Supabase Auth REST API の URL を組み立てる。"""
    if not SUPABASE_URL:
        _ensure_auth_available()
    base_url = (SUPABASE_URL or "").rstrip().rstrip("/")
    return f"{base_url}/auth/v1/{path.lstrip('/')}"


def _format_auth_response(data: dict[str, object]) -> dict[str, object]:
    """
    Supabase Auth REST レスポンスを既存 API 形式へ整形する。

    既存のフロントエンド互換のため、user と session をトップレベルに分けて返す。
    """
    user = data.get("user")
    if user is None and ("id" in data or "email" in data) and "access_token" not in data:
        user = data
    session_keys = {
        "access_token",
        "refresh_token",
        "token_type",
        "expires_in",
        "expires_at",
        "provider_token",
        "provider_refresh_token",
    }
    session = {key: data[key] for key in session_keys if key in data}
    if session and user is not None:
        session["user"] = user
    return {"user": user, "session": session or None}


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
        # Supabase Auth REST API でトークンを検証する。
        # 共有 Supabase client の auth session を汚さないよう、SDK の sign-in state は使わない。
        response = httpx.get(
            _auth_url("user"),
            headers=_auth_rest_headers(token),
            timeout=10.0,
        )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なトークンです",
            )
        user_data = response.json()
        # 後続の本人操作（password update / signout）で Bearer token を明示的に使う。
        # レスポンスとして返す用途ではない内部フィールド。
        user_data["__access_token"] = token
        return user_data
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
        response = httpx.get(
            _auth_url("user"),
            headers=_auth_rest_headers(credentials.credentials),
            timeout=10.0,
        )
        return response.json() if response.status_code < 400 else None
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

        response = httpx.post(
            _auth_url("signup"),
            headers=_auth_public_headers(),
            json={"email": email, "password": password, "data": user_data},
            timeout=10.0,
        )
        response.raise_for_status()
        return _format_auth_response(response.json())
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
        response = httpx.post(
            _auth_url("token"),
            headers=_auth_public_headers(),
            params={"grant_type": "password"},
            json={"email": email, "password": password},
            timeout=10.0,
        )
        response.raise_for_status()
        return _format_auth_response(response.json())
    except Exception as e:
        print(f"[ERROR] ログイン失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ログインに失敗しました",
        )


def sign_out(access_token: str) -> bool:
    """
    ログアウトする。

    Args:
        access_token: ログアウト対象ユーザーの Bearer token。

    Returns:
        成功した場合 True、失敗した場合 False。

    Raises:
        HTTPException(503): Supabase が未設定の場合。
    """
    _ensure_auth_available()
    try:
        response = httpx.post(
            _auth_url("logout"),
            headers=_auth_rest_headers(access_token),
            params={"scope": "global"},
            timeout=10.0,
        )
        response.raise_for_status()
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
        response = httpx.post(
            _auth_url("token"),
            headers=_auth_public_headers(),
            params={"grant_type": "refresh_token"},
            json={"refresh_token": refresh_token},
            timeout=10.0,
        )
        response.raise_for_status()
        return _format_auth_response(response.json())
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
        response = httpx.post(
            _auth_url("recover"),
            headers=_auth_public_headers(),
            json={"email": email},
            timeout=10.0,
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"[ERROR] パスワードリセットメール送信失敗: {e}")
        return False


def update_password(access_token: str, new_password: str) -> bool:
    """
    パスワードを更新する。

    Args:
        access_token: 更新対象ユーザー本人の Bearer token。
        new_password: 新しいパスワード。

    Returns:
        更新成功なら True、失敗なら False。

    Raises:
        HTTPException(503): Supabase が未設定の場合。
    """
    _ensure_auth_available()
    try:
        response = httpx.put(
            _auth_url("user"),
            headers=_auth_rest_headers(access_token),
            json={"password": new_password},
            timeout=10.0,
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"[ERROR] パスワード更新失敗: {e}")
        return False
