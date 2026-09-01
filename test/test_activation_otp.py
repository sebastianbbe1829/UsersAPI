from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from UsersAPI.controllers.auth_controller import verify_password
from test.fixtures.activation import create_activation_context


def test_request_activation_otp_sends_code(
    db_session: Session,
    client: TestClient,
    monkeypatch,
):
    user, _, user_tenant, token = create_activation_context(db_session)
    sent = {}

    monkeypatch.setattr(
        "UsersAPI.services.otp_service.send_email",
        lambda **kwargs: sent.update(kwargs),
    )

    response = client.post(f"/users/activate/{user.dni}/{token}/otp")

    assert response.status_code == 200
    assert response.json()["message"] == "Código de verificación enviado correctamente."
    assert response.json()["expires_at"]
    assert sent["recipient"] == user_tenant.email
    assert sent["template"] == "otp"
    assert len(sent["otp_code"]) == 6


def test_validate_activation_otp_activates_user(
    db_session: Session,
    client: TestClient,
    monkeypatch,
):
    user, _, user_tenant, token = create_activation_context(db_session)
    sent = {}

    monkeypatch.setattr(
        "UsersAPI.services.otp_service.send_email",
        lambda **kwargs: sent.update(kwargs),
    )

    request_response = client.post(f"/users/activate/{user.dni}/{token}/otp")
    assert request_response.status_code == 200

    response = client.post(
        f"/users/activate/{user.dni}/{token}/otp/validate",
        json={"code": sent["otp_code"]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "valid": True,
        "message": "Cuenta activada correctamente.",
    }

    db_session.refresh(user_tenant)
    assert user_tenant.status == 1


def test_invalid_activation_otp_does_not_activate_user(
    db_session: Session,
    client: TestClient,
    monkeypatch,
):
    user, _, user_tenant, token = create_activation_context(db_session)

    monkeypatch.setattr(
        "UsersAPI.services.otp_service.send_email",
        lambda **kwargs: None,
    )

    client.post(f"/users/activate/{user.dni}/{token}/otp")

    response = client.post(
        f"/users/activate/{user.dni}/{token}/otp/validate",
        json={"code": "000000"},
    )

    assert response.status_code == 200
    assert response.json()["valid"] is False
    db_session.refresh(user_tenant)
    assert user_tenant.status == 0


def test_activation_otp_cannot_be_reused(
    db_session: Session,
    client: TestClient,
    monkeypatch,
):
    user, _, user_tenant, token = create_activation_context(db_session)
    sent = {}

    monkeypatch.setattr(
        "UsersAPI.services.otp_service.send_email",
        lambda **kwargs: sent.update(kwargs),
    )

    client.post(f"/users/activate/{user.dni}/{token}/otp")

    first = client.post(
        f"/users/activate/{user.dni}/{token}/otp/validate",
        json={"code": sent["otp_code"]},
    )
    assert first.status_code == 200
    assert first.json()["valid"] is True

    # La cuenta ya activa no puede completar nuevamente el flujo.
    second = client.post(
        f"/users/activate/{user.dni}/{token}/otp/validate",
        json={"code": sent["otp_code"]},
    )
    assert second.status_code == 400
    db_session.refresh(user_tenant)
    assert user_tenant.status == 1


def test_activation_rejects_invalid_token(
    db_session: Session,
    client: TestClient,
):
    user, _, _, _ = create_activation_context(db_session)

    response = client.post(
        f"/users/activate/{user.dni}/token-invalido/otp"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Token de activación inválido"


def test_activation_rejects_token_for_another_user(
    db_session: Session,
    client: TestClient,
):
    user, _, _, token = create_activation_context(db_session)
    other_user, _, _, _ = create_activation_context(db_session)

    response = client.post(
        f"/users/activate/{other_user.dni}/{token}/otp"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Token de activación inválido"


def test_activation_rejects_already_active_user(
    db_session: Session,
    client: TestClient,
):
    user, _, user_tenant, token = create_activation_context(
        db_session,
        status=1,
    )

    response = client.post(f"/users/activate/{user.dni}/{token}/otp")

    assert response.status_code == 409
    assert response.json()["detail"] == "El usuario ya se encuentra activo"
    assert user_tenant.status == 1


def test_activation_flow_preserves_password(
    db_session: Session,
    client: TestClient,
    monkeypatch,
):
    user, _, user_tenant, token = create_activation_context(
        db_session,
        password="original-pass",
    )
    sent = {}

    monkeypatch.setattr(
        "UsersAPI.services.otp_service.send_email",
        lambda **kwargs: sent.update(kwargs),
    )

    client.post(f"/users/activate/{user.dni}/{token}/otp")
    response = client.post(
        f"/users/activate/{user.dni}/{token}/otp/validate",
        json={"code": sent["otp_code"]},
    )

    assert response.json()["valid"] is True
    db_session.refresh(user_tenant)
    assert verify_password("original-pass", user_tenant.password) is True
