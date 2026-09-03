import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ..database import set_rls_tenant
from ..models import AuthAuditDB, AuthSessionDB, GlobalUserDB
from ..services.jwt_service import create_access_token
from ..settings import settings

TENANT_SESSION_KIND = "TENANT"
SUPER_SESSION_KIND = "SUPER"
LOGIN_SUCCESS = "LOGIN_SUCCESS"
LOGOUT = "LOGOUT"
SESSION_REFRESH = "SESSION_REFRESH"
IDLE_TIMEOUT = "IDLE_TIMEOUT"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _decode_token(token: str, verify_exp: bool = True) -> dict:
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"verify_exp": verify_exp},
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido", headers={"WWW-Authenticate": "Bearer"}) from exc


def create_login_session(db: Session, token: str, payload: dict, client_ip: str | None = None, user_agent: str | None = None) -> AuthSessionDB:
    tenant_id = payload.get("tenant_id")
    if tenant_id is None:
        raise ValueError("El token de autenticación no contiene tenant_id")
    set_rls_tenant(db, int(tenant_id))
    session_id = payload.get("session_id") or str(uuid.uuid4())
    session_kind = payload.get("user_type", TENANT_SESSION_KIND)
    user_tenant_id = payload.get("user_tenant_id")
    global_user_id = payload.get("global_user_id")
    occurred_at = _now()
    session = AuthSessionDB(id=session_id, tenant_id=int(tenant_id), user_tenant_id=user_tenant_id, global_user_id=global_user_id, session_kind=session_kind, token_hash=_token_hash(token), login_at=occurred_at, last_activity_at=occurred_at, client_ip=client_ip, user_agent=user_agent, status="ACTIVE")
    db.add(session)
    db.flush()
    db.add(AuthAuditDB(id=str(uuid.uuid4()), tenant_id=int(tenant_id), user_tenant_id=user_tenant_id, global_user_id=global_user_id, session_id=session_id, session_kind=session_kind, event_type=LOGIN_SUCCESS, actor_identifier=payload.get("email") or payload.get("sub"), client_ip=client_ip, user_agent=user_agent, occurred_at=occurred_at))
    return session


def _get_active_session(db: Session, token: str, payload: dict) -> AuthSessionDB:
    tenant_id = payload.get("tenant_id")
    session_id = payload.get("session_id")
    if tenant_id is None or session_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="La sesión ya no es válida", headers={"WWW-Authenticate": "Bearer"})
    set_rls_tenant(db, int(tenant_id))
    session = db.query(AuthSessionDB).filter(AuthSessionDB.id == session_id, AuthSessionDB.tenant_id == int(tenant_id), AuthSessionDB.status == "ACTIVE").first()
    if session is None or session.token_hash != _token_hash(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="La sesión ya no es válida", headers={"WWW-Authenticate": "Bearer"})
    return session


def _close_idle_session(db: Session, session: AuthSessionDB, payload: dict) -> None:
    now = _now()
    session.logout_at = now
    session.duration_seconds = max(0, int((now - session.login_at).total_seconds()))
    session.status = "CLOSED"
    db.add(AuthAuditDB(id=str(uuid.uuid4()), tenant_id=session.tenant_id, user_tenant_id=session.user_tenant_id, global_user_id=session.global_user_id, session_id=session.id, session_kind=session.session_kind, event_type=IDLE_TIMEOUT, actor_identifier=payload.get("email") or payload.get("sub"), occurred_at=now))
    if session.global_user_id is not None:
        user = db.get(GlobalUserDB, session.global_user_id)
        if user is not None and user.session_id == session.id:
            user.session_id = None


def touch_active_session(db: Session, token: str, payload: dict) -> AuthSessionDB:
    session = _get_active_session(db, token, payload)
    now = _now()
    idle_seconds = (now - session.last_activity_at).total_seconds()
    if idle_seconds >= settings.session_idle_timeout_minutes * 60:
        _close_idle_session(db, session, payload)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="La sesión expiró por inactividad", headers={"WWW-Authenticate": "Bearer"})
    session.last_activity_at = now
    return session


def refresh_login_session(db: Session, token: str, client_ip: str | None = None, user_agent: str | None = None) -> dict:
    payload = _decode_token(token, verify_exp=False)
    session = _get_active_session(db, token, payload)
    now = _now()
    if (now - session.last_activity_at).total_seconds() >= settings.session_idle_timeout_minutes * 60:
        _close_idle_session(db, session, payload)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="La sesión expiró por inactividad", headers={"WWW-Authenticate": "Bearer"})
    claims = {key: value for key, value in payload.items() if key not in {"exp", "iat"}}
    new_token = create_access_token(claims)
    session.token_hash = _token_hash(new_token)
    session.last_activity_at = now
    if client_ip:
        session.client_ip = client_ip
    if user_agent:
        session.user_agent = user_agent
    db.add(AuthAuditDB(id=str(uuid.uuid4()), tenant_id=session.tenant_id, user_tenant_id=session.user_tenant_id, global_user_id=session.global_user_id, session_id=session.id, session_kind=session.session_kind, event_type=SESSION_REFRESH, actor_identifier=payload.get("email") or payload.get("sub"), client_ip=client_ip, user_agent=user_agent, occurred_at=now))
    return {"access_token": new_token, "token_type": "bearer", "session_id": session.id}


def close_login_session(db: Session, token: str, client_ip: str | None = None, user_agent: str | None = None) -> AuthSessionDB | None:
    payload = _decode_token(token, verify_exp=False)
    tenant_id = payload.get("tenant_id")
    if tenant_id is None:
        return None
    session = db.query(AuthSessionDB).filter(AuthSessionDB.token_hash == _token_hash(token), AuthSessionDB.tenant_id == int(tenant_id)).first()
    if session is None or session.status != "ACTIVE":
        return session
    set_rls_tenant(db, int(tenant_id))
    now = _now()
    session.logout_at = now
    session.duration_seconds = max(0, int((now - session.login_at).total_seconds()))
    session.status = "CLOSED"
    db.add(AuthAuditDB(id=str(uuid.uuid4()), tenant_id=session.tenant_id, user_tenant_id=session.user_tenant_id, global_user_id=session.global_user_id, session_id=session.id, session_kind=session.session_kind, event_type=LOGOUT, actor_identifier=payload.get("email") or payload.get("sub"), client_ip=client_ip, user_agent=user_agent, occurred_at=now))
    if session.global_user_id is not None:
        user = db.get(GlobalUserDB, session.global_user_id)
        if user is not None and user.session_id == session.id:
            user.session_id = None
    return session
