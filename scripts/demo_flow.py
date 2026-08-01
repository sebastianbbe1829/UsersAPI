import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import requests

BASE_URL = "http://127.0.0.1:8000"


def run_demo():
    print("1) Creando usuario inicial...")
    create_resp = requests.post(
        f"{BASE_URL}/users",
        json={
            "dni": "10000001",
            "name": "Demo User",
            "email": "demo@example.com",
            "phone": "3001111111",
            "password": "demo123",
        },
        timeout=10,
    )
    print("Status:", create_resp.status_code)
    print(create_resp.text)

    print("\n2) Haciendo login...")
    login_resp = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": "demo@example.com", "password": "demo123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    print("Status:", login_resp.status_code)
    print(login_resp.text)

    token = login_resp.json().get("access_token")

    print("\n3) Listando usuarios...")
    users_resp = requests.get(
        f"{BASE_URL}/users",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    print("Status:", users_resp.status_code)
    print(users_resp.text)


if __name__ == "__main__":
    run_demo()
