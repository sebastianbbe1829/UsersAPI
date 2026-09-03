import base64
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

from UsersAPI.services import extinguisher_recharge_notification_service as service


def _svc():
    return service.ExtinguisherRechargeNotificationService(MagicMock())


def test_build_message():
    message = service.ExtinguisherRechargeNotificationService._build_message(
        "Tenant", date(2026, 9, 3), []
    )
    assert "Tenant" in message
    assert "{TOTAL}" in message
    assert "{VENCIDOS}" in message
    assert "{HOY}" in message


def test_build_excel_attachment_contains_xlsx():
    attachment = _svc()._build_excel_attachment(
        "Tenant",
        date(2026, 9, 3),
        [
            {
                "code": "EXT-01",
                "type_name": "ABC",
                "capacity": 10,
                "location": "Recepción",
                "last_recharge_date": date(2025, 9, 3),
                "next_recharge_date": date(2026, 9, 3),
                "days_overdue": 0,
                "status": "VENCE HOY",
            }
        ],
    )
    assert attachment["name"].endswith(".xlsx")
    assert base64.b64decode(attachment["content"]).startswith(b"PK")


def test_already_sent_true_and_false():
    db = MagicMock()
    svc = service.ExtinguisherRechargeNotificationService(db)
    db.execute.return_value.scalar_one_or_none.return_value = "sent"
    assert svc._already_sent(date(2026, 9, 3), 1, "a@b.com") is True
    db.execute.return_value.scalar_one_or_none.return_value = None
    assert svc._already_sent(date(2026, 9, 3), 1, "a@b.com") is False


def test_mark_pending_commits():
    db = MagicMock()
    svc = service.ExtinguisherRechargeNotificationService(db)
    svc._mark_pending(date(2026, 9, 3), 1, "a@b.com")
    db.execute.assert_called_once()
    db.commit.assert_called_once()


def test_clear_pending_commits():
    db = MagicMock()
    svc = service.ExtinguisherRechargeNotificationService(db)
    svc._clear_pending(date(2026, 9, 3), 1, "a@b.com")
    db.execute.assert_called_once()
    db.commit.assert_called_once()


def test_mark_sent_commits():
    db = MagicMock()
    svc = service.ExtinguisherRechargeNotificationService(db)
    svc._mark_sent(date(2026, 9, 3), 1, "a@b.com")
    db.execute.assert_called_once()
    db.commit.assert_called_once()


def test_get_admin_recipients_normalizes_and_filters(monkeypatch):
    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = [
        " admin@example.com ",
        "",
        None,
        "second@example.com",
    ]
    svc = service.ExtinguisherRechargeNotificationService(db)
    assert svc._get_admin_recipients(1) == ["admin@example.com", "second@example.com"]
    db.execute.assert_called_once()


def test_run_with_no_expired_extinguishers():
    db = MagicMock()
    db.execute.return_value.all.return_value = []
    result = service.ExtinguisherRechargeNotificationService(db).run(date(2026, 9, 3))
    assert result == {
        "date": "2026-09-03",
        "tenants_with_expired_recharges": 0,
        "extinguishers": 0,
        "emails_sent": 0,
        "tenants_without_admin_email": 0,
        "email_errors": 0,
    }


def test_run_skips_tenant_without_admin_email():
    db = MagicMock()
    extinguisher = SimpleNamespace(
        tenant_id=1,
        code="EXT-01",
        capacity=10,
        location="A",
        last_recharge_date=date(2025, 9, 3),
        next_recharge_date=date(2026, 9, 2),
    )
    db.execute.return_value.all.return_value = [
        (extinguisher, "ABC", "Tenant", "tenant")
    ]
    svc = service.ExtinguisherRechargeNotificationService(db)
    svc._get_admin_recipients = MagicMock(return_value=[])
    result = svc.run(date(2026, 9, 3))
    assert result["tenants_with_expired_recharges"] == 1
    assert result["extinguishers"] == 1
    assert result["tenants_without_admin_email"] == 1
    assert result["emails_sent"] == 0


def test_run_sends_email_and_marks_sent(monkeypatch):
    db = MagicMock()
    extinguisher = SimpleNamespace(
        tenant_id=1,
        code="EXT-01",
        capacity=10,
        location="A",
        last_recharge_date=date(2025, 9, 3),
        next_recharge_date=date(2026, 9, 3),
    )
    db.execute.return_value.all.return_value = [
        (extinguisher, "ABC", "Tenant", "tenant")
    ]
    svc = service.ExtinguisherRechargeNotificationService(db)
    svc._get_admin_recipients = MagicMock(return_value=[" admin@example.com "])
    svc._already_sent = MagicMock(return_value=False)
    svc._mark_pending = MagicMock()
    svc._mark_sent = MagicMock()
    svc._build_excel_attachment = MagicMock(return_value={"name": "a.xlsx", "content": "x"})
    monkeypatch.setattr(service, "send_email", MagicMock())

    result = svc.run(date(2026, 9, 3))
    assert result["emails_sent"] == 1
    assert result["email_errors"] == 0
    svc._mark_pending.assert_called_once_with(date(2026, 9, 3), 1, "admin@example.com")
    svc._mark_sent.assert_called_once_with(date(2026, 9, 3), 1, "admin@example.com")
    service.send_email.assert_called_once()


def test_run_does_not_resend_already_sent(monkeypatch):
    db = MagicMock()
    extinguisher = SimpleNamespace(
        tenant_id=1,
        code="EXT-01",
        capacity=10,
        location="A",
        last_recharge_date=date(2025, 9, 3),
        next_recharge_date=date(2026, 9, 3),
    )
    db.execute.return_value.all.return_value = [
        (extinguisher, "ABC", "Tenant", "tenant")
    ]
    svc = service.ExtinguisherRechargeNotificationService(db)
    svc._get_admin_recipients = MagicMock(return_value=["admin@example.com"])
    svc._already_sent = MagicMock(return_value=True)
    svc._build_excel_attachment = MagicMock()
    monkeypatch.setattr(service, "send_email", MagicMock())

    result = svc.run(date(2026, 9, 3))
    assert result["emails_sent"] == 0
    svc._build_excel_attachment.assert_called_once()
    service.send_email.assert_not_called()


def test_run_clears_pending_when_email_fails(monkeypatch):
    db = MagicMock()
    extinguisher = SimpleNamespace(
        tenant_id=1,
        code="EXT-01",
        capacity=10,
        location="A",
        last_recharge_date=date(2025, 9, 3),
        next_recharge_date=date(2026, 9, 3),
    )
    db.execute.return_value.all.return_value = [
        (extinguisher, "ABC", "Tenant", "tenant")
    ]
    svc = service.ExtinguisherRechargeNotificationService(db)
    svc._get_admin_recipients = MagicMock(return_value=["admin@example.com"])
    svc._already_sent = MagicMock(return_value=False)
    svc._mark_pending = MagicMock()
    svc._clear_pending = MagicMock()
    monkeypatch.setattr(service, "send_email", MagicMock(side_effect=RuntimeError("smtp")))

    result = svc.run(date(2026, 9, 3))
    assert result["emails_sent"] == 0
    assert result["email_errors"] == 1
    svc._clear_pending.assert_called_once_with(date(2026, 9, 3), 1, "admin@example.com")
