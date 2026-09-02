import logging

from UsersAPI.logging_config import SensitiveDataFilter


def test_sensitive_data_filter_redacts_authentication_data():
    record = logging.LogRecord(
        name="UsersAPI",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=(
            "Login SUPER exitoso email=%s tenant_id=%s "
            "session_id=%s client_host=%s token=%s"
        ),
        args=(
            "super@example.com",
            42,
            "session-123",
            "192.168.1.10",
            "jwt-secret-value",
        ),
        exc_info=None,
    )

    assert SensitiveDataFilter().filter(record) is True

    assert "super@example.com" not in record.msg
    assert "42" not in record.msg
    assert "session-123" not in record.msg
    assert "192.168.1.10" not in record.msg
    assert "jwt-secret-value" not in record.msg
    assert "[EMAIL_REDACTED]" in record.msg
    assert "tenant_id=[REDACTED]" in record.msg
    assert "session_id=[REDACTED]" in record.msg
    assert "client_host=[REDACTED]" in record.msg
    assert "token=[REDACTED]" in record.msg


def test_sensitive_data_filter_redacts_mfa_and_password_fields():
    record = logging.LogRecord(
        name="UsersAPI",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="password=PlainPassword123 otp=123456 secret=super-secret",
        args=(),
        exc_info=None,
    )

    assert SensitiveDataFilter().filter(record) is True

    assert "PlainPassword123" not in record.msg
    assert "123456" not in record.msg
    assert "super-secret" not in record.msg
    assert record.msg == "password=[REDACTED] otp=[REDACTED] secret=[REDACTED]"
