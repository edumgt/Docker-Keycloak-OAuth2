# Docker-Keycloak-OAuth2

Keycloak 기반 통합 인증(SSO) 구조를 Python 백엔드로 연동한 PoC 저장소입니다.  
요청하신 기술 스택( `Keycloak + OAuth2/OIDC + PostgreSQL + Docker` )을 기준으로 실행 가능한 구성까지 포함합니다.

## 1. 구현 목표

1. 통합 인증 서버(IdP)
- Keycloak 기반 인증 서버
- OAuth2 / OpenID Connect 기반 인증
- Access Token / Refresh Token 발급 및 검증

2. 회원 관리
- 단일 사용자 식별자(`customer_id`) 기반 관리
- 회원 단계 개념 지원  
  (`visitor` → `consulting_customer` → `member` → `service_user` → `medical_service_user`)
- 계정 상태 관리 (`active`, `dormant`, `withdrawn`)

3. 동의 관리
- 공통 동의 + 서비스별 동의 구조
- 필수/선택 동의 구분
- 목적/버전/국가/언어 단위 동의 이력 관리

## 2. 실제 구성(현재 저장소)

- `backend` : FastAPI(Python) 기반 API 서버
- `frontend` : Tailwind 기반 로그인 UI (`/app-ui`, backend static 서빙)
- `keycloak` : OAuth2/OIDC IdP
- `postgres` : Keycloak + Backend 데이터 저장
- `capture` : 실행 화면 캡처용 Playwright 컨테이너

## 3. 기술 스택

- BE: Python 3.12, FastAPI, SQLAlchemy, httpx
- FE: HTML + Tailwind CSS
- IdP: Keycloak 26
- Auth Protocol: OAuth2, OpenID Connect
- DB: PostgreSQL 16
- Infra: Docker Compose

## 4. 아키텍처

```text
[Client(Web/App)]
      |
      v
[Python Backend(FastAPI)] <----> [Keycloak]
      |                               |
      v                               v
   [PostgreSQL] <---------------------+
```

## 5. 실행 방법

### 5.1 사전 요구사항

- Docker
- Docker Compose

### 5.2 컨테이너 기동

일반 환경:

```bash
docker compose up -d --build
```

`docker-buildx`가 없는 환경:

```bash
DOCKER_BUILDKIT=0 docker compose up -d --build
```

상태 확인:

```bash
docker compose ps
```

중지:

```bash
docker compose down
```

## 6. 접속 정보

- Backend Swagger: http://localhost:8000/docs
- Backend OpenAPI: http://localhost:8000/openapi.json
- Frontend(Login UI): http://localhost:8000/app-ui
- Keycloak: http://localhost:8080
- Keycloak Realm: `integrated-id`

기본 계정/클라이언트:

- Keycloak Admin: `admin / admin1234`
- Demo User1: `demo-user / demo1234`
- Demo User2: `demo-user2 / demo2234`
- Demo User3: `demo-user3 / demo3234`
- OIDC Client: `be-client` (secret: `be-client-secret`)

## 7. 계정/JWT/로그인 테스트 자동 실행

다음 스크립트를 실행하면 아래를 한 번에 수행합니다.

- 로그인 가능한 계정 3개 보장 생성
- JWT 3개 발급
- 계정별 로그인(token/userinfo) 테스트
- 결과 파일 저장

```bash
./scripts/provision-users-and-test.sh
```

산출물:

- `artifacts/jwt-tokens.json` (JWT 3개 포함)
- `artifacts/login-test-results.json` (로그인 테스트 결과)

최근 테스트 결과 예시:

- `overall_passed: true`
- `demo-user`: token 200 / userinfo 200
- `demo-user2`: token 200 / userinfo 200
- `demo-user3`: token 200 / userinfo 200

## 8. API 요약

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/v1/health` | DB/Keycloak 연결 상태 |
| GET | `/api/v1/auth/login-url` | Keycloak 인증 URL |
| POST | `/api/v1/auth/token` | Keycloak 토큰 발급(Direct Grant) |
| GET | `/api/v1/auth/userinfo` | Access Token 기반 사용자 정보 |
| POST | `/api/v1/members` | 회원 생성 |
| GET | `/api/v1/members` | 회원 목록 |
| PATCH | `/api/v1/members/{customer_id}/status` | 회원 상태 변경 |
| POST | `/api/v1/consents` | 동의 생성 |
| GET | `/api/v1/members/{customer_id}/consents` | 회원 동의 조회 |

### 8.1 예시: 토큰 발급 및 사용자 정보 조회

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"demo-user","password":"demo1234"}'
```

```bash
TOKEN="<access_token>"
curl http://localhost:8000/api/v1/auth/userinfo \
  -H "Authorization: Bearer ${TOKEN}"
```

## 9. 실행 화면 캡처

스크린샷 재생성:

```bash
./scripts/capture-screens.sh
```

저장 경로:

- `captures/backend-swagger.png`
- `captures/keycloak-login.png`
- `captures/fe-login-success.png` (로그인 성공 후 화면)

### 9.1 Backend Swagger

![Backend Swagger](./captures/backend-swagger.png)

### 9.2 Keycloak Login

![Keycloak Login](./captures/keycloak-login.png)

### 9.3 Frontend Login Success

![Frontend Login Success](./captures/fe-login-success.png)

## 10. 디렉토리 구조

```text
.
├── backend
│   ├── app
│   │   ├── auth.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── main.py
│   │   ├── models.py
│   │   └── schemas.py
│   ├── Dockerfile
│   └── requirements.txt
├── captures
│   ├── backend-swagger.png
│   ├── fe-login-success.png
│   └── keycloak-login.png
├── artifacts
│   ├── jwt-tokens.json
│   └── login-test-results.json
├── docker-compose.yml
├── infra
│   ├── keycloak/realm/integrated-id-realm.json
│   └── postgres/init/01-init-databases.sql
├── scripts/capture-fe-login-success.js
├── scripts/provision-users-and-test.sh
└── scripts/capture-screens.sh
```

## 11. OIDC IdP 기술 설명

### 11.1 OAuth2 와 OIDC 개요

**OAuth2**는 제3자 애플리케이션이 사용자를 대신해 리소스에 접근할 수 있도록 허가하는 **위임 인가(Authorization) 프레임워크**입니다.  
**OIDC(OpenID Connect)**는 OAuth2 위에 **인증(Authentication) 레이어**를 추가한 프로토콜로, `ID Token`이라는 JWT를 통해 "누가 로그인했는지"를 검증합니다.

| 구분 | OAuth2 | OIDC |
|---|---|---|
| 목적 | 인가 (Authorization) | 인증 (Authentication) |
| 결과물 | Access Token | ID Token + Access Token |
| 표준 | RFC 6749 | OpenID Foundation |
| 사용자 정보 | `/userinfo` 엔드포인트 별도 호출 | ID Token 클레임에 직접 포함 가능 |

### 11.2 주요 역할(Roles)

```text
[Resource Owner]   : 최종 사용자 (demo-user 등)
[Client]           : 인가를 요청하는 애플리케이션 (FastAPI Backend, be-client)
[Authorization Server / IdP] : 인증 및 토큰 발급 서버 (Keycloak)
[Resource Server]  : 보호된 리소스 제공 서버 (FastAPI /api/v1/*)
```

- **IdP(Identity Provider)**: 사용자의 신원을 증명하고 토큰을 발급하는 주체입니다. 이 저장소에서는 Keycloak이 IdP 역할을 합니다.
- **RP(Relying Party)**: IdP를 신뢰하여 인증을 위임하는 애플리케이션입니다. 이 저장소에서는 FastAPI 백엔드가 RP 역할을 합니다.

### 11.3 Keycloak OIDC 엔드포인트

Keycloak은 OIDC Discovery 문서(`/.well-known/openid-configuration`)를 통해 모든 엔드포인트를 자동으로 노출합니다.

**Discovery 문서 URL:**

```
http://localhost:8080/realms/integrated-id/.well-known/openid-configuration
```

| 엔드포인트 | URL 패턴 | 용도 |
|---|---|---|
| Authorization | `/realms/{realm}/protocol/openid-connect/auth` | 인증 코드 요청 (브라우저 리다이렉트) |
| Token | `/realms/{realm}/protocol/openid-connect/token` | 토큰 발급 / 갱신 |
| UserInfo | `/realms/{realm}/protocol/openid-connect/userinfo` | Access Token으로 사용자 정보 조회 |
| Introspection | `/realms/{realm}/protocol/openid-connect/token/introspect` | 토큰 유효성 서버 사이드 검증 |
| End Session | `/realms/{realm}/protocol/openid-connect/logout` | 로그아웃 (세션 종료) |
| JWKS | `/realms/{realm}/protocol/openid-connect/certs` | 토큰 서명 검증용 공개 키 |

본 저장소에서 백엔드가 사용하는 엔드포인트(`config.py`):

```python
# 토큰 발급
keycloak_token_endpoint   = "{base}/realms/{realm}/protocol/openid-connect/token"
# 사용자 정보 조회
keycloak_userinfo_endpoint = "{base}/realms/{realm}/protocol/openid-connect/userinfo"
# 인증 URL 생성 (Authorization Code Flow)
keycloak_auth_endpoint    = "{base}/realms/{realm}/protocol/openid-connect/auth"
```

### 11.4 OIDC Authorization Code Flow

표준 웹 애플리케이션에서 권장되는 인증 흐름입니다.

```text
[브라우저/Client]          [FastAPI Backend]          [Keycloak IdP]
      |                          |                           |
      |--- GET /auth/login-url ->|                           |
      |<-- authorization_url ---|                           |
      |                          |                           |
      |--- 브라우저 리다이렉트 ---------------------------------------->|
      |                          |          (사용자 로그인 UI 표시)     |
      |<------------------------------------------------------|
      |        (로그인 후 ?code=AUTH_CODE 로 redirect_uri로 리다이렉트)  |
      |                          |                           |
      |--- POST /token (code) -->|                           |
      |                          |--- POST /token (code) -->|
      |                          |       grant_type=authorization_code   |
      |                          |<-- {access_token, id_token, ...} ----|
      |<-- {access_token, ...} --|                           |
      |                          |                           |
      |--- GET /userinfo ------->|                           |
      |   (Bearer access_token)  |--- GET /userinfo ------->|
      |                          |<-- {sub, email, name} ---|
      |<-- {user info} ----------|                           |
```

> 본 저장소의 `/api/v1/auth/token`은 데모 목적으로 **Direct Grant(Resource Owner Password Credentials)** 방식을 사용합니다.  
> 운영 환경에서는 반드시 위의 **Authorization Code + PKCE** 흐름을 사용해야 합니다.

**Direct Grant Flow (현재 구현):**

```text
[Client]                           [Keycloak IdP]
   |                                      |
   |--- POST /token ---------------------->|
   |    grant_type=password               |
   |    username / password               |
   |    client_id / client_secret         |
   |    scope=openid profile email        |
   |<-- {access_token, refresh_token, id_token, ...} ---|
```

### 11.5 토큰 종류 및 역할

| 토큰 | 형식 | 용도 | 유효기간(예시) |
|---|---|---|---|
| **ID Token** | JWT (서명됨) | 사용자 신원 확인 (OIDC 전용) | 5분 |
| **Access Token** | JWT (서명됨) | API 리소스 접근 인가 | 5분 |
| **Refresh Token** | Opaque 또는 JWT | Access Token 갱신 | 30분~수일 |

- **ID Token**: `sub`(사용자 식별자), `email`, `name` 등의 클레임을 포함하며 RP가 직접 파싱합니다. **Resource Server에 전송하지 않습니다.**
- **Access Token**: API 호출 시 `Authorization: Bearer <token>` 헤더로 전달합니다. Resource Server는 서명 검증 또는 Introspection으로 유효성을 확인합니다.
- **Refresh Token**: 만료된 Access Token 재발급에만 사용합니다. 외부에 노출되어선 안 됩니다.

### 11.6 ID Token (JWT) 구조

JWT는 `.`으로 구분된 세 부분(`Header.Payload.Signature`)으로 구성됩니다.

**Header:**
```json
{
  "alg": "RS256",
  "typ": "JWT",
  "kid": "키 식별자(JWKS에서 공개 키 조회에 사용)"
}
```

**Payload (클레임 예시):**
```json
{
  "iss": "http://localhost:8080/realms/integrated-id",
  "sub": "사용자 고유 UUID (Keycloak 내부 ID)",
  "aud": "be-client",
  "exp": 1710000300,
  "iat": 1710000000,
  "auth_time": 1710000000,
  "azp": "be-client",
  "email": "demo-user@example.com",
  "email_verified": true,
  "name": "Demo User",
  "preferred_username": "demo-user",
  "given_name": "Demo",
  "family_name": "User"
}
```

**주요 클레임 설명:**

| 클레임 | 설명 |
|---|---|
| `iss` (Issuer) | 토큰 발급자 (Keycloak Realm URL) |
| `sub` (Subject) | 사용자 고유 식별자 (UUID) |
| `aud` (Audience) | 토큰 수신 대상 Client ID |
| `exp` (Expiration) | 만료 시각 (Unix timestamp) |
| `iat` (Issued At) | 발급 시각 (Unix timestamp) |
| `azp` (Authorized Party) | 토큰을 요청한 Client |
| `preferred_username` | 로그인 ID |

**Signature:** Keycloak의 RSA 개인 키로 서명하며, 수신 측은 JWKS 엔드포인트에서 공개 키를 받아 검증합니다.

### 11.7 Keycloak Realm / Client 구성

**Realm**은 Keycloak의 최상위 격리 단위로, 독립된 사용자/클라이언트/정책 세트를 갖습니다.

```
Keycloak
└── Realm: integrated-id          ← 이 저장소에서 사용하는 Realm
    ├── Clients
    │   └── be-client              ← FastAPI 백엔드가 사용하는 OIDC 클라이언트
    │       ├── Protocol: openid-connect
    │       ├── Access Type: confidential (client_secret 필요)
    │       ├── Standard Flow: 활성화 (Authorization Code Flow)
    │       ├── Direct Access Grants: 활성화 (Resource Owner Password)
    │       └── Service Accounts: 활성화 (Client Credentials Flow)
    ├── Roles
    │   ├── member
    │   └── medical-user
    └── Users
        ├── demo-user
        ├── demo-user2
        └── demo-user3
```

**Client 종류 비교:**

| 구분 | Public Client | Confidential Client |
|---|---|---|
| Client Secret | 없음 | 있음 (서버 사이드에서만 보관) |
| 주요 사용처 | SPA, 모바일 앱 | 서버 사이드 웹 앱, 백엔드 |
| 보안 강화 방법 | PKCE 필수 적용 | Client Secret + PKCE 권장 |
| 이 저장소 | — | `be-client` (confidential) |

### 11.8 백엔드 OIDC 연동 포인트

| 기능 | 코드 위치 | 호출 엔드포인트 | 설명 |
|---|---|---|---|
| 토큰 발급 | `auth.py::issue_token` | `POST /token` | Direct Grant로 Access/ID/Refresh Token 발급 |
| 사용자 정보 조회 | `auth.py::fetch_userinfo` | `GET /userinfo` | Access Token으로 사용자 클레임 조회 |
| 인증 URL 생성 | `auth.py::build_authorization_url` | `GET /auth` | Authorization Code Flow 시작점 URL 생성 |
| Keycloak 상태 확인 | `auth.py::keycloak_alive` | `GET /realms/{realm}` | Realm 메타데이터 응답으로 생존 여부 확인 |

**Scope 설명:**

토큰 요청 시 `scope=openid profile email`을 지정합니다.

| Scope | 포함 클레임 |
|---|---|
| `openid` | `sub`, `iss`, `aud`, `exp`, `iat` (ID Token 발급의 필수 조건) |
| `profile` | `name`, `given_name`, `family_name`, `preferred_username` |
| `email` | `email`, `email_verified` |

## 12. 운영 전 고려사항

- Direct Grant 비활성화 및 표준 Authorization Code(+PKCE) 적용
- Client Secret/DB 계정 등 민감정보를 `.env` 및 Secret Manager로 분리
- Keycloak/Backend TLS 적용 및 리버스 프록시(Nginx, Ingress) 구성
- 동의 이력 감사 로그 및 의료/비의료 데이터 분리 저장소 설계
