"""
DAG 01 – 헬스 체크 (Health Check)

목적:
    Keycloak 과 Backend API 의 가용성을 주기적으로 확인합니다.
    서비스 장애를 조기에 감지하고 Airflow 태스크 실패로 알림을 받을 수 있습니다.

태스크 구성:
    check_keycloak  → Keycloak Realm 메타데이터 엔드포인트 호출
    check_backend   → FastAPI /api/v1/health 엔드포인트 호출
    (두 태스크는 독립적으로 병렬 실행)

실행 주기: 5분마다
"""

import os
from datetime import datetime, timedelta

import requests
from airflow import DAG
from airflow.operators.python import PythonOperator

KEYCLOAK_BASE_URL = os.environ.get("KEYCLOAK_BASE_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "integrated-id")
BACKEND_BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://backend:8000")

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}


def check_keycloak(**context):
    """Keycloak Realm 메타데이터 엔드포인트로 가용성 확인"""
    url = f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    print(f"[OK] Keycloak realm='{data['realm']}' is reachable.")
    return {"realm": data["realm"], "status": "ok"}


def check_backend(**context):
    """FastAPI 백엔드 헬스 엔드포인트로 DB·Keycloak 연결 상태 확인"""
    url = f"{BACKEND_BASE_URL}/api/v1/health"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    print(
        f"[OK] Backend status={data['status']} "
        f"db={data['database']} keycloak={data['keycloak']}"
    )
    if data["status"] != "ok":
        raise ValueError(f"Backend degraded: {data}")
    return data


with DAG(
    dag_id="dag_01_health_check",
    description="Keycloak 및 Backend API 헬스 체크",
    schedule_interval=timedelta(minutes=5),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["health", "keycloak", "backend"],
) as dag:
    t_keycloak = PythonOperator(
        task_id="check_keycloak",
        python_callable=check_keycloak,
    )

    t_backend = PythonOperator(
        task_id="check_backend",
        python_callable=check_backend,
    )

    # 두 태스크는 독립적으로 병렬 실행
    [t_keycloak, t_backend]
