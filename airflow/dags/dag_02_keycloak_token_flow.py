"""
DAG 02 – Keycloak OAuth2 토큰 발급 및 보호된 API 호출

목적:
    Keycloak Direct Grant(Resource Owner Password) 방식으로 Access Token 을 발급받고,
    해당 토큰을 사용하여 보호된 Backend API 엔드포인트를 호출하는 전체 흐름을 시연합니다.
    Airflow XCom 을 통해 태스크 간 토큰 데이터를 전달합니다.

태스크 구성:
    1. fetch_keycloak_token   – Keycloak 에서 OAuth2 Access Token 발급
    2. decode_token_claims    – JWT 클레임(sub, email, exp 등) 디코딩 및 출력
    3. call_protected_userinfo – Access Token 으로 Backend /auth/userinfo 호출
    4. call_protected_members  – Access Token 으로 Backend /members 목록 조회

실행 주기: 수동 트리거 (schedule_interval=None)

주의:
    Direct Grant 방식은 데모/개발 환경 전용입니다.
    운영 환경에서는 Authorization Code + PKCE 흐름을 사용하세요.
"""

import base64
import json
import os
from datetime import datetime, timedelta

import requests
from airflow import DAG
from airflow.operators.python import PythonOperator

KEYCLOAK_BASE_URL = os.environ.get("KEYCLOAK_BASE_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "integrated-id")
BACKEND_BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://backend:8000")

# 데모용 자격 증명 (운영 환경에서는 Airflow Variables / Connections 로 관리)
DEMO_USERNAME = "demo-user"
DEMO_PASSWORD = "demo1234"
CLIENT_ID = "airflow-client"
CLIENT_SECRET = "airflow-client-secret"

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(seconds=30),
}


def fetch_keycloak_token(**context):
    """
    Keycloak Direct Grant(Password) 방식으로 OAuth2 토큰 발급.

    반환 데이터(XCom):
        access_token  – API 호출에 사용하는 Bearer 토큰
        expires_in    – 유효 기간(초)
        token_type    – 토큰 유형 (bearer)
    """
    token_url = (
        f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}"
        "/protocol/openid-connect/token"
    )
    payload = {
        "grant_type": "password",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "username": DEMO_USERNAME,
        "password": DEMO_PASSWORD,
        "scope": "openid profile email",
    }

    resp = requests.post(token_url, data=payload, timeout=30)
    resp.raise_for_status()
    token_data = resp.json()

    print(f"[OK] Token issued. type={token_data['token_type']}, expires_in={token_data['expires_in']}s")

    # 다음 태스크에서 사용할 수 있도록 XCom 에 저장
    ti = context["ti"]
    ti.xcom_push(key="access_token", value=token_data["access_token"])
    ti.xcom_push(key="expires_in", value=token_data["expires_in"])
    return token_data["expires_in"]


def decode_token_claims(**context):
    """
    JWT Access Token 의 Payload 클레임을 Base64 디코딩하여 출력.
    서명 검증은 수행하지 않습니다 (조회/로깅 목적).
    """
    ti = context["ti"]
    access_token = ti.xcom_pull(task_ids="fetch_keycloak_token", key="access_token")

    # JWT 구조: header.payload.signature
    parts = access_token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT structure")

    # Base64url 패딩 보정 후 디코딩
    payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
    payload_json = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
    claims = json.loads(payload_json)

    print("=== JWT Claims ===")
    for key in ("iss", "sub", "aud", "azp", "preferred_username", "email", "exp", "iat"):
        print(f"  {key}: {claims.get(key)}")

    return {k: claims.get(k) for k in ("sub", "preferred_username", "email")}


def call_protected_userinfo(**context):
    """
    Access Token 을 Authorization: Bearer 헤더로 첨부하여
    Backend /api/v1/auth/userinfo 엔드포인트 호출.
    """
    ti = context["ti"]
    access_token = ti.xcom_pull(task_ids="fetch_keycloak_token", key="access_token")

    url = f"{BACKEND_BASE_URL}/api/v1/auth/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}

    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    userinfo = resp.json()

    print(f"[OK] UserInfo payload: {userinfo}")
    return userinfo


def call_protected_members(**context):
    """
    Access Token 으로 Backend /api/v1/members 목록 조회.
    """
    ti = context["ti"]
    access_token = ti.xcom_pull(task_ids="fetch_keycloak_token", key="access_token")

    url = f"{BACKEND_BASE_URL}/api/v1/members"
    headers = {"Authorization": f"Bearer {access_token}"}

    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    members = resp.json()

    print(f"[OK] Total members: {len(members)}")
    for m in members:
        print(f"  - {m.get('customer_id')} | stage={m.get('stage')} | status={m.get('account_status')}")
    return len(members)


with DAG(
    dag_id="dag_02_keycloak_token_flow",
    description="Keycloak OAuth2 토큰 발급 → 보호된 Backend API 호출 데모",
    schedule_interval=None,  # 수동 트리거
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["oauth2", "keycloak", "token", "backend"],
) as dag:
    t_fetch_token = PythonOperator(
        task_id="fetch_keycloak_token",
        python_callable=fetch_keycloak_token,
    )

    t_decode_claims = PythonOperator(
        task_id="decode_token_claims",
        python_callable=decode_token_claims,
    )

    t_userinfo = PythonOperator(
        task_id="call_protected_userinfo",
        python_callable=call_protected_userinfo,
    )

    t_members = PythonOperator(
        task_id="call_protected_members",
        python_callable=call_protected_members,
    )

    # 토큰 발급 후 → 클레임 디코딩 + API 호출 병렬 실행
    t_fetch_token >> t_decode_claims
    t_fetch_token >> [t_userinfo, t_members]
