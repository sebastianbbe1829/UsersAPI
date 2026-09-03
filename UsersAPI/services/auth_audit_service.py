import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..database import set_rls_tenant
from ..models import AuthAuditDB, AuthSessionDB, GlobalUserDB


TENANT_SESSION_KIND = "TENANT"
SUPER_SESSION_KIND = "SUPER"
LOGIN_SUCCESS = "LOGIN_SUCCESS"
LOGOUT = "LOGOUT"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_login_session(
    db: Session,
    token: str,
    payload: dict,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> AuthSessionDB:
    tenant_id = payload.get("tenant_id")
    if tenant_id is None:
        raise ValueError("El token de autenticación no contiene tenant_id")

    set_rls_tenant(db, int(tenant_id))

    session_id = payload.get("session_id") or str(uuid.uuid4())
    session_kind = payload.get("user_type", TENANT_SESSION_KIND)
    user_tenant_id = payload.get("user_tenant_id")
    global_user_id = payload.get("global_user_id")
    occurred_at = _now()

    session = AuthSessionDB(
        id=session_id,
        tenant_id=int(tenant_id),
        user_tenant_id=user_tenant_id,
        global_user_id=global_user_id,
        session_kind=session_kind,
        token_hash=_token_hash(token),
        login_at=occurred_at,
        client_ip=client_ip,
        user_agent=user_agent,
        status="ACTIVE",
    )
    db.add(session)
    db.flush()

    db.add(
        AuthAuditDB(
            id=str(uuid.uuid4()),
            tenant_id=int(tenant_id),
            user_tenant_id=user_tenant_id,
            global_user_id=global_user_id,
            session_id=session_id,
            session_kind=session_kind,
            event_type=LOGIN_SUCCESS,
            actor_identifier=payload.get("email") or payload.get("sub"),
            client_ip=client_ip,
            user_agent=user_agent,
            occurred_at=occurred_at,
        )
    )
    return session


def close_login_session(
    db: Session,
    token: str,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> AuthSessionDB | None:
    from jose import JWTError, jwt

    from ..settings import settings

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"verify_exp": False},
        )
    except JWTError:
        return None

    tenant_id = payload.get("tenant_id")
    if tenant_id is None:
        return None

    set_rls_tenant(db, int(tenant_id))
    session = (
        db.query(AuthSessionDB)
        .filter(AuthSessionDB.token_hash == _token_hash(token))
        .first()
    )

    if session is None or session.status != "ACTIVE":
        return session

    now = _now()
    session.logout_at = now
    session.duration_seconds = max(0, int((now - session.login_at).total_seconds()))
    session.status = "CLOSED"

    db.add(
        AuthAuditDB(
            id=str(uuid.uuid4()),
            tenant_id=session.tenant_id,
            user_tenant_id=session.user_tenant_id,
            global_user_id=session.global_user_id,
            session_id=session.id,
            session_kind=session.session_kind,
            event_type=LOGOUT,
            actor_identifier=payload.get("email") or payload.get("sub"),
            client_ip=client_ip,
            user_agent=user_agent,
            occurred_at=now,
        )
    )

    if session.global_user_id is not None:
        user = db.get(GlobalUserDB, session.global_user_id)
        if user is not None and user.session_id == session.id:
            user.session_id = None

    return session
