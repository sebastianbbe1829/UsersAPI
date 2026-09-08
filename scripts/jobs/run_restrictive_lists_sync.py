import os
import sys

from UsersAPI.domains.clients.services.screening_sync_job import (
    run_restrictive_lists_sync_job,
)


def _trigger_type() -> str:
    event_name = os.getenv("GITHUB_EVENT_NAME", "")
    if event_name == "schedule":
        return "SCHEDULE"
    if event_name == "workflow_dispatch":
        return os.getenv("SCREENING_SYNC_TRIGGER_TYPE", "MANUAL").upper()
    return "MANUAL"


if __name__ == "__main__":
    trigger = _trigger_type()
    result = run_restrictive_lists_sync_job(trigger)
    print(result)

    if result.get("status") in {"ERROR", "PARTIAL_ERROR"}:
        sys.exit(1)
