from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from UsersAPI.models import GlobalUserDB
from UsersAPI.schemas.global_user import GlobalSuperCreate, GlobalSuperUpdate
from UsersAPI.services import global_user_service


@pytest.fixture
def actor():
    return SimpleNamespace(email="actor@example.com", is_superuser=True)


def _create_data(**overrides):
    data = {
        "dni": "90000010",
        "name": "Nuevo SUPER",
        "phone": "3000000010",
        "email": "new@example.com",
        "password": "StrongPassword123!",
    }
    data.update(overrides)
    return GlobalSuperCreate(**data)


def test_list_global_supers_returns_only_query_results():
    db = MagicMock()
    query = db.query.return_value
    query.filter.return_value = query
    query.order_by.return_value = query
    expected = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    query.all.return_value = expected

    result = global_user_service.list_global_supers(db)

    assert result == expected
    db.query.assert_called_once_with(GlobalUserDB)


def test_get_global_super_raises_when_not_found():
    db = MagicMock()
    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        global_user_service.get_global_super(99, db)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Usuario SUPER no encontrado."


def test_create_global_super_requires_super_actor():
    db = MagicMock()
    datos = _create_data()

    with patch.object(
        global_user_service,
        "require_super_user",
        side_effect=HTTPException(status_code=403, detail="Solo SUPER."),
    ):
        with pytest.raises(HTTPException) as exc_info:
            global_user_service.create_global_super(datos, "123456", db, actor=None)

    assert exc_info.value.status_code == 403
    db.add.assert_not_called()


def test_create_global_super_requires_valid_fresh_mfa(actor):
    db = MagicMock()
    datos = _create_data()

    with patch.object(global_user_service, "require_super_user", return_value=actor), patch.object(
        global_user_service,
        "verify_super_mfa_otp",
        side_effect=HTTPException(status_code=401, detail="MFA inválido."),
    ):
        with pytest.raises(HTTPException) as exc_info:
            global_user_service.create_global_super(datos, "000000", db, actor)

    assert exc_info.value.status_code == 401
    db.add.assert_not_called()


def test_create_global_super_creates_enrolled_user_and_returns_provisioning_uri(actor):
    db = MagicMock()
    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None

    def flush_assigns_id():
        db.add.call_args.args[0].id = 1

    db.flush.side_effect = flush_assigns_id
    datos = _create_data(dni="90000011", email=" New@Example.COM ")

    with patch.object(global_user_service, "require_super_user", return_value=actor), patch.object(
        global_user_service, "verify_super_mfa_otp"
    ) as verify_otp, patch.object(
        global_user_service, "get_password_hash", return_value="hashed-password"
    ), patch.object(
        global_user_service, "_encrypt_mfa_secret", side_effect=lambda secret: f"enc:{secret}"
    ), patch.object(global_user_service, "send_email") as send_email_mock:
        response = global_user_service.create_global_super(datos, "123456", db, actor)

    verify_otp.assert_called_once_with(actor, "123456")
    send_email_mock.assert_called_once()
    email_kwargs = send_email_mock.call_args.kwargs
    assert email_kwargs["recipient"] == "new@example.com"
    assert email_kwargs["template"] == "super_invitation"
    assert email_kwargs["tenant_name"] == "UsersAPI"
    assert email_kwargs["qr_html"].startswith("<table")
    assert email_kwargs["attachments"]
    assert email_kwargs["attachments"][0]["name"] == "mfa_qr.png"
    assert response.id == 1
    assert response.email == "new@example.com"
    assert response.dni == "90000011"
    assert response.name == "Nuevo SUPER"
    assert response.phone == "3000000010"
    assert response.is_superuser is True
    assert response.is_active is True
    assert response.mfa_enabled is True
    assert response.mfa_verified_at is None
    assert response.provisioning_uri.startswith("otpauth://totp/")
    assert response.email_sent is True
    created = db.add.call_args.args[0]
    assert created.email == "new@example.com"
    assert created.dni == "90000011"
    assert created.password_hash == "hashed-password"
    assert created.mfa_secret_encrypted.startswith("enc:")
    assert created.mfa_verified_at is None


def test_create_global_super_rejects_duplicate_email(actor):
    db = MagicMock()
    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = SimpleNamespace(email="new@example.com")
    datos = _create_data()

    with patch.object(global_user_service, "require_super_user", return_value=actor), patch.object(
        global_user_service, "verify_super_mfa_otp"
    ):
        with pytest.raises(HTTPException) as exc_info:
            global_user_service.create_global_super(datos, "123456", db, actor)

    assert exc_info.value.status_code == 409
    db.add.assert_not_called()


def test_update_global_super_requires_fresh_mfa(actor):
    db = MagicMock()
    datos = GlobalSuperUpdate(name="Changed")

    with patch.object(global_user_service, "require_super_user", return_value=actor), patch.object(
        global_user_service,
        "verify_super_mfa_otp",
        side_effect=HTTPException(status_code=401, detail="MFA inválido."),
    ):
        with pytest.raises(HTTPException) as exc_info:
            global_user_service.update_global_super(1, datos, "000000", db, actor)

    assert exc_info.value.status_code == 401
    db.add.assert_not_called()


def test_update_global_super_rejects_empty_update(actor):
    db = MagicMock()
    target = SimpleNamespace(id=1, email="target@example.com", is_active=True, is_superuser=True)
    datos = GlobalSuperUpdate()

    with patch.object(global_user_service, "require_super_user", return_value=actor), patch.object(
        global_user_service, "verify_super_mfa_otp"
    ), patch.object(global_user_service, "get_global_super", return_value=target):
        with pytest.raises(HTTPException) as exc_info:
            global_user_service.update_global_super(1, datos, "123456", db, actor)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Debe indicar al menos un campo para actualizar."


def test_update_global_super_cannot_deactivate_last_active_super(actor):
    db = MagicMock()
    target = SimpleNamespace(
        id=1,
        email="target@example.com",
        is_active=True,
        is_superuser=True,
        session_id="session-id",
    )
    query = db.query.return_value
    query.filter.return_value = query
    query.count.return_value = 1
    datos = GlobalSuperUpdate(is_active=False)

    with patch.object(global_user_service, "require_super_user", return_value=actor), patch.object(
        global_user_service, "verify_super_mfa_otp"
    ), patch.object(global_user_service, "get_global_super", return_value=target):
        with pytest.raises(HTTPException) as exc_info:
            global_user_service.update_global_super(1, datos, "123456", db, actor)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "No es posible desactivar el último usuario SUPER activo."
    assert target.is_active is True


def test_update_global_super_deactivation_clears_session(actor):
    db = MagicMock()
    target = SimpleNamespace(
        id=2,
        email="target@example.com",
        is_active=True,
        is_superuser=True,
        session_id="session-id",
        updated_at=None,
        updated_by=None,
    )
    query = db.query.return_value
    query.filter.return_value = query
    query.count.return_value = 2
    datos = GlobalSuperUpdate(is_active=False)

    with patch.object(global_user_service, "require_super_user", return_value=actor), patch.object(
        global_user_service, "verify_super_mfa_otp"
    ), patch.object(global_user_service, "get_global_super", return_value=target):
        result = global_user_service.update_global_super(2, datos, "123456", db, actor)

    assert result is target
    assert target.is_active is False
    assert target.session_id is None
    assert target.updated_by == actor.email
    db.add.assert_called_once_with(target)
