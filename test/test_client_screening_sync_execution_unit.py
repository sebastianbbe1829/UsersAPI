from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from UsersAPI.domains.clients.routes.screening_routes import (
    _accepted,
    list_sync_executions_route,
    manual_sync_screening_lists_route,
    sync_screening_lists_route,
)
from UsersAPI.domains.clients.services.screening_sync_service import (
    create_sync_execution,
    list_sync_executions,
    run_sync_execution,
)


def _execution(status="PENDING"):
    return SimpleNamespace(
        id=uuid4(),
        status=status,
        trigger_type="MANUAL",
        triggered_by=7,
        triggered_by_email="admin@example.com",
        created_at=None,
        started_at=None,
        finished_at=None,
        duration_ms=None,
        total_sources=None,
        successful_sources=None,
        failed_sources=None,
        result=None,
        error_message=None,
    )


def test_create_sync_execution_reuses_active_execution():
    db = MagicMock()
    active = _execution("RUNNING")
    db.query.return_value.filter.return_value.first.return_value = active

    result = create_sync_execution(db, "CRONJOB")

    assert result is active
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_create_sync_execution_persists_new_execution():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    created = create_sync_execution(db, "MANUAL", 7, "admin@example.com")

    assert created.status == "PENDING"
    assert created.trigger_type == "MANUAL"
    assert created.triggered_by == 7
    assert created.triggered_by_email == "admin@example.com"
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(created)


def test_list_sync_executions_returns_latest_rows():
    db = MagicMock()
    rows = [_execution("SUCCESS"), _execution("ERROR")]
    db.query.return_value.order_by.return_value.limit.return_value.all.return_value = rows

    assert list_sync_executions(db, 20) == rows


def test_run_sync_execution_marks_success():
    db = MagicMock()
    execution = _execution()
    db.get.return_value = execution
    result = {
        "status": "SUCCESS",
        "total_sources": 1,
        "successful_sources": 1,
        "failed_sources": 0,
    }

    with (
        patch(
            "UsersAPI.domains.clients.services.screening_sync_service.SessionLocal",
            return_value=db,
        ),
        patch(
            "UsersAPI.domains.clients.services.screening_sync_service.sync_all_screening_lists_bulk",
            return_value=result,
        ),
    ):
        run_sync_execution(execution.id)

    assert execution.status == "SUCCESS"
    assert execution.finished_at is not None
    assert execution.duration_ms is not None
    assert execution.total_sources == 1
    assert execution.successful_sources == 1
    assert execution.failed_sources == 0
    assert execution.result == result
    db.close.assert_called_once()


def test_run_sync_execution_marks_error():
    db = MagicMock()
    execution = _execution()
    db.get.return_value = execution

    with (
        patch(
            "UsersAPI.domains.clients.services.screening_sync_service.SessionLocal",
            return_value=db,
        ),
        patch(
            "UsersAPI.domains.clients.services.screening_sync_service.sync_all_screening_lists_bulk",
            side_effect=RuntimeError("falló proveedor"),
        ),
    ):
        run_sync_execution(execution.id)

    assert execution.status == "ERROR"
    assert execution.finished_at is not None
    assert execution.duration_ms is not None
    assert execution.error_message == "falló proveedor"
    db.rollback.assert_called_once()
    db.close.assert_called_once()


def test_run_sync_execution_ignores_unknown_execution():
    db = MagicMock()
    db.get.return_value = None

    with patch(
        "UsersAPI.domains.clients.services.screening_sync_service.SessionLocal",
        return_value=db,
    ):
        run_sync_execution(uuid4())

    db.close.assert_called_once()


def test_accepted_schema():
    execution = _execution()
    result = _accepted(execution, "ok")
    assert result.id == execution.id
    assert result.status == "PENDING"
    assert result.message == "ok"


def test_screening_routes_schedule_background_tasks():
    execution = _execution()
    db = MagicMock()
    tasks = MagicMock()

    with patch(
        "UsersAPI.domains.clients.routes.screening_routes.create_sync_execution",
        return_value=execution,
    ):
        result = __import__("asyncio").run(sync_screening_lists_route(tasks, db))

    assert result.id == execution.id
    tasks.add_task.assert_called_once_with(run_sync_execution, execution.id)


def test_manual_screening_route_records_user():
    execution = _execution()
    db = MagicMock()
    tasks = MagicMock()
    user = SimpleNamespace(id=7, email="admin@example.com")

    with patch(
        "UsersAPI.domains.clients.routes.screening_routes.create_sync_execution",
        return_value=execution,
    ) as creator:
        result = __import__("asyncio").run(manual_sync_screening_lists_route(tasks, db, user))

    assert result.id == execution.id
    creator.assert_called_once_with(
        db,
        trigger_type="MANUAL",
        triggered_by=7,
        triggered_by_email="admin@example.com",
    )
    tasks.add_task.assert_called_once_with(run_sync_execution, execution.id)


def test_list_sync_executions_route_delegates():
    rows = [_execution("SUCCESS")]
    db = MagicMock()
    with patch(
        "UsersAPI.domains.clients.routes.screening_routes.list_sync_executions",
        return_value=rows,
    ) as service:
        result = __import__("asyncio").run(list_sync_executions_route(db))

    assert result == rows
    service.assert_called_once_with(db)
