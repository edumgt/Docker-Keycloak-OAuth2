"""
DAG 03 – 회원 라이프사이클 관리 (Member Lifecycle)

목적:
    Keycloak 인증을 통해 발급된 Access Token 으로 Backend API 를 호출하여
    회원 등록 → 상태 변경 → 동의 등록 → 동의 조회의 전체 워크플로를 시연합니다.

    실제 배치 작업(야간 회원 프로비저닝, 동의 상태 갱신 등)에 적용할 수 있는
    패턴을 보여주는 예제입니다.

태스크 구성:
    1. get_auth_token       – Keycloak 에서 서비스용 Access Token 발급
    2. create_member        – Backend API 로 신규 회원 등록
    3. update_member_status – 회원 상태를 'active' → 'dormant' 로 변경
    4. register_consent     – 회원 동의 항목 등록
    5. verify_consents      – 등록된 동의 목록 조회 및 검증

실행 주기: 매일 자정 (schedule_interval="@daily")
"""

import os
import uuid
from datetime import datetime, timedelta

import requests
from airflow import DAG
from airflow.operators.python import PythonOperator

KEYCLOAK_BASE_URL = os.environ.get("KEYCLOAK_BASE_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "integrated-id")
BACKEND_BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://backend:8000")

CLIENT_ID = "airflow-client"
CLIENT_SECRET = "airflow-client-secret"
DEMO_USERNAME = "demo-user"
DEMO_PASSWORD = "demo1234"

default_args = {
    "owner": "airflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}


def get_auth_token(**context):
    """Keycloak Direct Grant 방식으로 Access Token 발급 후 XCom 저장"""
    token_url = (
        f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}"
        "/protocol/openid-connect/token"
    )
    resp = requests.post(
        token_url,
        data={
            "grant_type": "password",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "username": DEMO_USERNAME,
            "password": DEMO_PASSWORD,
            "scope": "openid profile email",
        },
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    context["ti"].xcom_push(key="access_token", value=token)
    print("[OK] Access token obtained from Keycloak.")
    return "token_obtained"


def create_member(**context):
    """
    Backend API 로 신규 회원을 등록합니다.
    customer_id 는 실행 날짜를 포함한 고유값으로 생성합니다.

    POST /api/v1/members
    """
    ti = context["ti"]
    access_token = ti.xcom_pull(task_ids="get_auth_token", key="access_token")

    # 실행 날짜 기반 고유 customer_id (멱등 재실행 지원)
    run_date = context["ds"].replace("-", "")  # e.g. 20240101
    customer_id = f"batch-{run_date}"
    email = f"batch-{run_date}@example.com"

    url = f"{BACKEND_BASE_URL}/api/v1/members"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    body = {
        "customer_id": customer_id,
        "email": email,
        "stage": "visitor",
        "account_status": "active",
    }

    resp = requests.post(url, json=body, headers=headers, timeout=30)

    if resp.status_code == 409:
        # 이미 존재하는 경우: 멱등 처리(재실행 시 무시)
        print(f"[SKIP] Member '{customer_id}' already exists.")
    else:
        resp.raise_for_status()
        member = resp.json()
        print(f"[OK] Created member: id={member['id']} customer_id={member['customer_id']}")

    ti.xcom_push(key="customer_id", value=customer_id)
    return customer_id


def update_member_status(**context):
    """
    회원 상태를 'active' 에서 'dormant' 로 변경합니다.

    PATCH /api/v1/members/{customer_id}/status
    """
    ti = context["ti"]
    access_token = ti.xcom_pull(task_ids="get_auth_token", key="access_token")
    customer_id = ti.xcom_pull(task_ids="create_member", key="customer_id")

    url = f"{BACKEND_BASE_URL}/api/v1/members/{customer_id}/status"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    resp = requests.patch(url, json={"account_status": "dormant"}, headers=headers, timeout=30)
    resp.raise_for_status()
    member = resp.json()
    print(f"[OK] Member '{customer_id}' status updated to '{member['account_status']}'.")
    return member["account_status"]


def register_consent(**context):
    """
    회원에게 서비스 이용 동의 항목을 등록합니다.

    POST /api/v1/consents
    """
    ti = context["ti"]
    access_token = ti.xcom_pull(task_ids="get_auth_token", key="access_token")
    customer_id = ti.xcom_pull(task_ids="create_member", key="customer_id")

    url = f"{BACKEND_BASE_URL}/api/v1/consents"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    body = {
        "customer_id": customer_id,
        "consent_type": "service",
        "service_name": "batch-demo-service",
        "purpose": "batch_processing",
        "is_required": True,
        "is_agreed": True,
        "consent_version": "1.0",
        "country_code": "KR",
        "language_code": "ko",
    }

    resp = requests.post(url, json=body, headers=headers, timeout=30)

    if resp.status_code == 409:
        print(f"[SKIP] Consent already registered for '{customer_id}'.")
    else:
        resp.raise_for_status()
        consent = resp.json()
        print(
            f"[OK] Consent registered: id={consent['id']} "
            f"type={consent['consent_type']} agreed={consent['is_agreed']}"
        )
    return "consent_registered"


def verify_consents(**context):
    """
    회원의 동의 목록을 조회하여 등록 결과를 검증합니다.

    GET /api/v1/members/{customer_id}/consents
    """
    ti = context["ti"]
    access_token = ti.xcom_pull(task_ids="get_auth_token", key="access_token")
    customer_id = ti.xcom_pull(task_ids="create_member", key="customer_id")

    url = f"{BACKEND_BASE_URL}/api/v1/members/{customer_id}/consents"
    headers = {"Authorization": f"Bearer {access_token}"}

    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    consents = resp.json()

    print(f"[OK] Total consents for '{customer_id}': {len(consents)}")
    for c in consents:
        print(
            f"  - [{c['id']}] type={c['consent_type']} "
            f"service={c['service_name']} agreed={c['is_agreed']} v={c['consent_version']}"
        )

    if not consents:
        raise ValueError(f"No consents found for member '{customer_id}'. Expected at least 1.")

    return len(consents)


with DAG(
    dag_id="dag_03_member_lifecycle",
    description="Keycloak 인증 기반 회원 등록 → 상태 변경 → 동의 등록 워크플로",
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["member", "consent", "lifecycle", "keycloak", "backend"],
) as dag:
    t_token = PythonOperator(
        task_id="get_auth_token",
        python_callable=get_auth_token,
    )

    t_create = PythonOperator(
        task_id="create_member",
        python_callable=create_member,
    )

    t_update_status = PythonOperator(
        task_id="update_member_status",
        python_callable=update_member_status,
    )

    t_consent = PythonOperator(
        task_id="register_consent",
        python_callable=register_consent,
    )

    t_verify = PythonOperator(
        task_id="verify_consents",
        python_callable=verify_consents,
    )

    # 순차 실행: 토큰 → 회원 생성 → (상태 변경 + 동의 등록 병렬) → 검증
    t_token >> t_create >> [t_update_status, t_consent] >> t_verify
