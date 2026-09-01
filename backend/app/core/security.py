from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings

bearer = HTTPBearer(auto_error=False)


def create_token(subject: str) -> str:
    s = get_settings()
    payload = {
        "sub": subject,
        "exp": datetime.now(UTC) + timedelta(minutes=s.jwt_expire_minutes),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "缺少憑證")
    s = get_settings()
    try:
        payload = jwt.decode(cred.credentials, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "憑證無效或已過期") from exc
    return payload["sub"]
