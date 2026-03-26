"""
Airflow Webserver Configuration – Keycloak OAuth2/OIDC 연동

이 파일은 Apache Airflow 웹 UI의 인증 방식을 설정합니다.
Keycloak을 OAuth2/OIDC 제공자로 사용하여 통합 인증(SSO)을 구현합니다.

흐름 요약:
  1. 사용자가 Airflow UI(http://localhost:8888) 에 접속
  2. Airflow 가 Keycloak 로그인 페이지(http://localhost:8080)로 리다이렉트
  3. 사용자가 Keycloak 계정(demo-user 등)으로 로그인
  4. Keycloak 이 Authorization Code 를 포함하여 Airflow 로 콜백
  5. Airflow 서버가 내부 네트워크(keycloak:8080)에서 Access Token 교환
  6. 사용자 정보(email, name)를 Airflow DB 에 자동 등록 후 로그인 완료
"""

from flask_appbuilder.security.manager import AUTH_OAUTH

# ---------------------------------------------------------------------------
# 인증 방식: OAuth2 (Keycloak)
# ---------------------------------------------------------------------------
AUTH_TYPE = AUTH_OAUTH

# 최초 로그인 시 Airflow DB 에 사용자를 자동 등록
AUTH_USER_REGISTRATION = True

# 자동 등록된 사용자에게 부여할 기본 역할 (데모용 Admin – 운영 환경에서는 Viewer 권장)
AUTH_USER_REGISTRATION_ROLE = "Admin"

# 로그인 시마다 Keycloak 역할을 Airflow 역할과 동기화
AUTH_ROLES_SYNC_AT_LOGIN = True

# Keycloak realm 역할 → Airflow 역할 매핑
# Keycloak 에서 realm-level role 이름으로 관리하고 아래에 매핑합니다.
AUTH_ROLES_MAPPING = {
    "airflow_admin":  ["Admin"],
    "airflow_op":     ["Op"],
    "airflow_user":   ["User"],
    "airflow_viewer": ["Viewer"],
}

# ---------------------------------------------------------------------------
# OAuth2 공급자: Keycloak
#
# authorize_url  : 브라우저가 직접 접근하므로 로컬호스트(외부) URL 사용
# access_token_url / userinfo_endpoint:
#                  Airflow 서버가 Docker 내부 네트워크에서 호출하므로
#                  컨테이너 서비스명(keycloak:8080) URL 사용
# ---------------------------------------------------------------------------
OAUTH_PROVIDERS = [
    {
        "name": "keycloak",
        "icon": "fa-key",
        "token_key": "access_token",
        "remote_app": {
            "client_id": "airflow-client",
            "client_secret": "airflow-client-secret",
            # 브라우저 → Keycloak 로그인 페이지 (외부 접근 가능 URL)
            "authorize_url": "http://localhost:8080/realms/integrated-id/protocol/openid-connect/auth",
            # Airflow 서버 → Keycloak 토큰 교환 (Docker 내부 네트워크)
            "access_token_url": "http://keycloak:8080/realms/integrated-id/protocol/openid-connect/token",
            # Airflow 서버 → Keycloak 사용자 정보 조회
            "userinfo_endpoint": "http://keycloak:8080/realms/integrated-id/protocol/openid-connect/userinfo",
            # JWT 서명 검증용 공개 키
            "jwks_uri": "http://keycloak:8080/realms/integrated-id/protocol/openid-connect/certs",
            "client_kwargs": {
                "scope": "openid email profile",
            },
        },
    }
]
