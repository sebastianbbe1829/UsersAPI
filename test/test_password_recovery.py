from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from UsersAPI.controllers.auth_controller import verify_password
from UsersAPI.models.otp import OTPCodeDB
from test.fixtures.multitenant import create_user_context


PASSWORD_RECOVERY_PURPOSE = "password_recovery"


def test_request_password_recovery_sends_otp_for_existing_user_tenant(
    db_session: Session,
    client: TestClient,
    monkeypatch,
):
    user, tenant, user_tenant, _ = create_user_context(db_session)
    sent = {}

    monkeypatch.setattr(
        "UsersAPI.services.otp_service.send_email",
        lambda **kwargs: sent.update(kwargs),
    )

    response = client.post(
        f"/auth/password-recovery/{tenant.slug}/request",
        json={"email": user_tenant.email},
    )

    assert response.status_code == 200
    assert response.json()["message"] == (
        "Si el correo pertenece a un usuario activo, "
        "recibirás un código para recuperar tu contraseña."
    )
    assert response.json()["expires_at"]
    assert sent["recipient"] == user_tenant.email
    assert sent["template"] == "otp"
    assert len(sent["otp_code"]) == 6


def test_request_password_recovery_does_not_reveal_unknown_email(
    db_session: Session,
    client: TestClient,
):
    _, tenant, _, _ = create_user_context(db_session)
    unknown_email = "not-registered@example.com"

    response = client.post(
        f"/auth/password-recovery/{tenant.slug}/request",
        json={"email": unknown_email},
    )

    assert response.status_code == 200
    assert response.json()["message"] == (
        "Si el correo pertenece a un usuario activo, "
        "recibirás un código para recuperar tu contraseña."
    )
    assert response.json()["expires_at"] is not None
    assert (
        db_session.query(OTPCodeDB)
        .filter(
            OTPCodeDB.destination == unknown_email,
            OTPCodeDB.purpose == PASSWORD_RECOVERY_PURPOSE,
        )
        .count()
        == 0
    )


def test_password_recovery_reset_changes_password(
    db_session: Session,
    client: TestClient,
    monkeypatch,
):
    user, tenant, user_tenant, _ = create_user_context(
        db_session,
        password="oldpass",
    )
    sent = {}

    monkeypatch.setattr(
        "UsersAPI.services.otp_service.send_email",
        lambda **kwargs: sent.update(kwargs),
    )

    request_response = client.post(
        f"/auth/password-recovery/{tenant.slug}/request",
        json={"email": user_tenant.email},
    )
    assert request_response.status_code == 200

    response = client.post(
        f"/auth/password-recovery/{tenant.slug}/reset",
        json={
            "email": user_tenant.email,
            "code": sent["otp_code"],
            "new_password": "new-password",
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Contraseña actualizada correctamente."

    db_session.refresh(user_tenant)
    assert verify_password("new-password", user_tenant.password) is True
    assert verify_password("oldpass", user_tenant.password) is False


def test_password_recovery_rejects_invalid_otp_without_changing_password(
    db_session: Session,
    client: TestClient,
    monkeypatch,
):
    _, tenant, user_tenant, _ = create_user_context(
        db_session,
        password="oldpass",
    )

    monkeypatch.setattr(
        "UsersAPI.services.otp_service.send_email",
        lambda **kwargs: None,
    )

    client.post(
        f"/auth/password-recovery/{tenant.slug}/request",
        json={"email": user_tenant.email},
    )

    response = client.post(
        f"/auth/password-recovery/{tenant.slug}/reset",
        json={
            "email": user_tenant.email,
            "code": "000000",
            "new_password": "new-password",
        },
    )

    assert response.status_code == 400
    db_session.refresh(user_tenant)
    assert verify_password("oldpass", user_tenant.password) is True


def test_password_recovery_cannot_reuse_otp(
    db_session: Session,
    client: TestClient,
    monkeypatch,
):
    _, tenant, user_tenant, _ = create_user_context(db_session)
    sent = {}

    monkeypatch.setattr(
        "UsersAPI.services.otp_service.send_email",
        lambda **kwargs: sent.update(kwargs),
    )

    client.post(
        f"/auth/password-recovery/{tenant.slug}/request",
        json={"email": user_tenant.email},
    )

    first = client.post(
        f"/auth/password-recovery/{tenant.slug}/reset",
        json={
            "email": user_tenant.email,
            "code": sent["otp_code"],
            "new_password": "new-password",
        },
    )
    assert first.status_code == 200

    second = client.post(
        f"/auth/password-recovery/{tenant.slug}/reset",
        json={
            "email": user_tenant.email,
            "code": sent["otp_code"],
            "new_password": "another-password",
        },
    )

    assert second.status_code == 400


def test_password_recovery_rejects_invalid_tenant(
    client: TestClient,
):
    response = client.post(
        "/auth/password-recovery/tenant-inexistente/request",
        json={"email": "user@example.com"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Tenant inválido"


def test_password_recovery_is_isolated_by_tenant(
    db_session: Session,
    client: TestClient,
    monkeypatch,
):
    _, _, user_tenant_a, _ = create_user_context(db_session)
    _, tenant_b, _, _ = create_user_context(db_session)

    monkeypatch.setattr(
        "UsersAPI.services.otp_service.send_email",
        lambda **kwargs: None,
    )

    response = client.post(
        f"/auth/password-recovery/{tenant_b.slug}/request",
        json={"email": user_tenant_a.email},
    )

    assert response.status_code == 200
    assert response.json()["expires_at"] is not None
    assert (
        db_session.query(OTPCodeDB)
        .filter(
            OTPCodeDB.destination == user_tenant_a.email,
            OTPCodeDB.purpose == PASSWORD_RECOVERY_PURPOSE,
        )
        .count()
        == 0
    )
