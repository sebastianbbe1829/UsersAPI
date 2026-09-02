from UsersAPI.services.extinguisher_recharge_job import run_extinguisher_recharge_notification_job


if __name__ == "__main__":
    result = run_extinguisher_recharge_notification_job(wait_for_schedule=True)
    print(result)
