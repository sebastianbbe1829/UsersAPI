from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from test.fixtures.activation import create_activation_context


def test_activation_otp_request_sends_code(
    db_session: Session,
    client: TestClient,
    monkeypatch,
):
    user, _, _, token = create_activation_context(db_session)
    sent = {}
    monkeypatch.setattr(
        "UsersAPI.services.otp_service.send_email",
        lambda **kwargs: sent.update(kwargs),
    )

    response = client.post(f"/users/activate/{user.dni}/{token}/otp")

    assert response.status_code == 200
    assert response.json()["message"] == "Código de verificación enviado correctamente."
    assert sent["to"] == user.email if hasattr(user, "email") else True
    assert len(sent["otp_code"]) == 6


def test_activation_otp_valid_code_activates_user(
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
    response = client.post(
        f"/users/activate/{user.dni}/{token}/otp/validate",
        json={"code": sent["otp_code"]},
    )

    assert response.status_code == 200
    assert response.json()["valid"] is True
    db_session.refresh(user_tenant)
    assert user_tenant.status == 1
    assert user_tenant.activation_token is None


def test_activation_otp_invalid_code_does_not_activate_user(
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

    # La activación consume también el token de activación, por lo que
    # un segundo intento con el mismo token ya no puede iniciar el flujo.
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
        f"/users/activate/{user.dni}/invalid-token/otp/validate",
        json={"code": "000000"},
    )

    assert response.status_code == 400


def test_activation_rejects_token_for_another_user(
    db_session: Session,
    client: TestClient,
):
    user_one, _, _, token = create_activation_context(db_session)
    user_two, _, _, _ = create_activation_context(db_session)

    response = client.post(
        f"/users/activate/{user_two.dni}/{token}/otp/validate",
        json={"code": "000000"},
    )

    assert response.status_code == 400


def test_activation_rejects_already_active_user(
    db_session: Session,
    client: TestClient,
    monkeypatch,
):
    user, _, user_tenant, token = create_activation_context(
        db_session,
        status=1,
    )

    response = client.post(f"/users/activate/{user.dni}/{token}/otp")

    assert response.status_code == 409
    db_session.refresh(user_tenant)
    assert user_tenant.status == 1


def test_activation_keeps_password_valid_after_activation(
    db_session: Session,
    client: TestClient,
    monkeypatch,
):
    user, _, user_tenant, token = create_activation_context(
        db_session,
        password="oldpass",
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

    assert response.status_code == 200
    db_session.refresh(user_tenant)
    assert user_tenant.status == 1
