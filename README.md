# Docker-Keycloak-OAuth2

Keycloak 기반 통합 인증(SSO) 구조를 Python 백엔드로 연동하고,  
**Apache Airflow 를 추가하여 OAuth2 인증 기반의 실제 배치 워크플로를 구현한 PoC 저장소**입니다.

요청하신 기술 스택 (`Keycloak + OAuth2/OIDC + PostgreSQL + Airflow + Docker`) 을 기준으로  
실행 가능한 구성까지 포함합니다.

---

## 0. 기술 용어 쉬운 설명 📖

> 이 프로젝트에서 자주 등장하는 어려운 단어들을 **쉬운 말**로 먼저 설명합니다.  
> 이미 알고 있다면 [1. 구현 목표](#1-구현-목표)로 바로 넘어가도 됩니다.

---

### 🔑 SSO (Single Sign-On, 통합 로그인)

**한 번 로그인하면 여러 서비스를 다시 로그인하지 않아도 되는 기능**입니다.

예시:
- 구글 계정으로 한 번 로그인하면 Gmail, YouTube, Google Drive 를 별도 로그인 없이 사용하는 것과 같습니다.
- 이 프로젝트에서는 **Keycloak** 에 한 번 로그인하면 **Airflow UI** 와 **Backend API** 를 별도 로그인 없이 이용합니다.

---

### 🏛️ Keycloak (키클록)

**"로그인 전문 서버"** 입니다.

직접 로그인 화면을 만들거나 비밀번호를 관리하는 코드를 짜는 대신,  
Keycloak 이라는 전문 서버에게 "인증은 네가 담당해!" 하고 맡기는 방식입니다.

- 사용자 계정 저장 및 관리
- 로그인 화면 제공
- 로그인 성공 시 토큰(출입증) 발급
- 소셜 로그인(구글, 깃허브 등) 연동 가능

> 💡 회사 사원증 발급 담당 부서와 같다고 생각하면 됩니다.

---

### 🌐 OAuth2 (오어스 투)

**"다른 앱에게 내 정보를 빌려줄 때 사용하는 표준 방법"** 입니다.

예시:
- "카카오 계정으로 로그인" 버튼을 클릭하면 카카오가 해당 앱에 여러분의 기본 정보를 넘겨주는 방식이 OAuth2 입니다.
- **직접 비밀번호를 알려주지 않고**, "이 앱이 이 정보에 접근해도 됩니다"라는 **허가증(Access Token)** 만 발급합니다.

| 개념 | 비유 |
|---|---|
| Resource Owner (자원 소유자) | 나 (사용자) |
| Client (클라이언트) | 내 정보에 접근하려는 앱 (Airflow, FastAPI 백엔드) |
| Authorization Server (인가 서버) | 허가증 발급 기관 (Keycloak) |
| Resource Server (자원 서버) | 내 정보가 있는 서버 (Backend API) |

---

### 🪪 OIDC (OpenID Connect, 오픈아이디 커넥트)

**OAuth2 에 "이 사람이 누구인지 확인"하는 기능을 추가한 것** 입니다.

- **OAuth2** 는 "이 앱이 내 파일에 접근해도 돼" → **허가(Authorization)** 에 집중
- **OIDC** 는 거기에 더해 "지금 로그인한 사람이 진짜 홍길동입니다" → **신원 확인(Authentication)** 기능 추가

OIDC 를 사용하면 `ID Token` 이라는 특별한 토큰을 받아 로그인한 사람의 이름, 이메일 등을 바로 알 수 있습니다.

> 💡 OAuth2 = 열쇠 발급 / OIDC = 열쇠 발급 + 신분증 확인

---

### 🎫 JWT (JSON Web Token, 제이더블유티)

**"위조할 수 없는 디지털 출입증"** 입니다.

로그인에 성공하면 서버가 JWT 를 발급해 줍니다. 이 출입증에는:
- 누가 로그인했는지 (sub, email)
- 언제까지 유효한지 (exp)
- 어떤 권한이 있는지 (roles)

이 정보가 암호화된 서명과 함께 담겨 있습니다.

```
eyJhbGciOiJSUzI1NiJ9   ← 헤더 (알고리즘 정보)
.eyJzdWIiOiJkZW1vIn0   ← 페이로드 (사용자 정보)
.SflKxwRJSMeKKF2QT4fw  ← 서명 (위조 방지)
```

> 💡 JWT = 위조 방지 스티커가 붙은 놀이동산 손목 밴드

---

### 🔒 Access Token / Refresh Token

| 토큰 | 역할 | 유효 기간 |
|---|---|---|
| **Access Token** | API 서버에 "나 인증된 사용자야"라고 보여주는 출입증 | 짧음 (5분~1시간) |
| **Refresh Token** | Access Token 이 만료되면 새로 발급받는 데 사용하는 재발급권 | 길음 (수 시간~수 일) |

> 💡 Access Token = 단기 주차권 / Refresh Token = 주차권 재발급 쿠폰

---

### ✈️ Apache Airflow (아파치 에어플로우)

**"할 일 목록(작업 흐름)을 자동으로 순서대로 실행해주는 스케줄러"** 입니다.

예:
- 매일 자정에 "신규 회원 데이터 처리 → 이메일 발송 → 리포트 생성" 순서로 자동 실행
- 특정 작업이 실패하면 재시도하거나 알림 발송

이 프로젝트에서는:
- **DAG** 로 작업 흐름을 정의
- Keycloak 에서 토큰을 받아 Backend API 를 자동으로 호출
- Airflow 웹 UI 에도 Keycloak SSO 로 로그인

> 💡 Airflow = 작업 지시서를 받아 순서대로 실행해 주는 공장 로봇

---

### 📊 DAG (Directed Acyclic Graph, 방향성 비순환 그래프)

이름이 어렵지만 쉽게 말하면: **"순서가 있는 작업 흐름도"** 입니다.

- **Directed (방향성)**: 작업에 실행 순서가 있음 (A → B → C)
- **Acyclic (비순환)**: 작업이 다시 자기 자신으로 돌아오지 않음 (무한 루프 없음)
- **Graph (그래프)**: 작업들이 연결된 구조

예를 들어 DAG 03 의 흐름:

```
[토큰 발급]
    └──> [회원 등록]
              ├──> [상태 변경]  ← 병렬 실행
              └──> [동의 등록]  ← 병렬 실행
                       └──> [결과 검증]
```

> 💡 DAG = 요리 레시피처럼 "먼저 재료 준비 → 동시에 볶기+끓이기 → 마지막에 플레이팅"

---

### 📬 XCom (Cross-Communication, 크로스컴)

**"Airflow 작업들이 서로 데이터를 주고받는 우편함"** 입니다.

하나의 DAG 안에서 여러 태스크(작업)가 실행될 때,  
앞 작업의 결과를 뒤 작업에 전달할 때 XCom 을 사용합니다.

```python
# 태스크 A: 토큰을 발급하고 XCom 에 저장
ti.xcom_push(key="access_token", value="eyJhbGci...")

# 태스크 B: XCom 에서 토큰을 꺼내서 API 호출에 사용
token = ti.xcom_pull(task_ids="태스크A", key="access_token")
```

> 💡 XCom = 작업자들 사이의 쪽지 전달함

---

### 🐳 Docker / Docker Compose

**Docker**: 애플리케이션과 그 실행 환경을 하나의 **컨테이너(박스)** 에 담아 어디서든 동일하게 실행합니다.

> 💡 Docker = 모든 재료와 조리도구가 들어있는 밀키트

**Docker Compose**: 여러 컨테이너(Keycloak, PostgreSQL, Airflow, Backend)를 **한 번에 실행**하고 관리합니다.

```bash
docker compose up -d   # 모든 서비스 한 번에 시작
docker compose down    # 모든 서비스 한 번에 종료
```

> 💡 Docker Compose = 밀키트 여러 개를 동시에 조리하는 스마트 오븐

---

### 🗃️ PostgreSQL (포스트그레SQL)

**"데이터를 표(Table) 형태로 저장하는 데이터베이스"** 입니다.

이 프로젝트에서는 하나의 PostgreSQL 서버에 **3개의 데이터베이스**가 존재합니다:

| 데이터베이스 | 용도 |
|---|---|
| `keycloak` | Keycloak 이 사용자 계정·설정 저장 |
| `app_db` | Backend API 가 회원·동의 데이터 저장 |
| `airflow` | Airflow 가 DAG 실행 이력·상태 저장 |

---

### ⚡ FastAPI (패스트에이피아이)

**"Python 으로 빠르게 REST API 서버를 만드는 프레임워크"** 입니다.

- `/api/v1/members` 같은 URL 경로를 Python 함수로 쉽게 만들 수 있음
- `/docs` 에 접속하면 **Swagger UI** (API 테스트 화면) 가 자동 생성됨
- Keycloak 이 발급한 JWT 토큰을 검증하여 인증된 사용자만 API 사용 허용

---

### 🏠 Realm (Keycloak 렐름)

**"Keycloak 안의 독립적인 인증 구역"** 입니다.

하나의 Keycloak 서버에서 여러 개의 독립된 인증 도메인을 운영할 수 있습니다.  
이 프로젝트는 `integrated-id` 라는 이름의 Realm 을 사용합니다.

> 💡 Realm = 아파트 단지 안의 독립된 동(棟)

---

### 🔄 Authorization Code Flow (인가 코드 흐름)

**브라우저를 통해 로그인하는 가장 안전한 OAuth2 방식** 입니다.

1. 브라우저 → Keycloak 로그인 페이지로 이동
2. 로그인 성공 → Keycloak 이 **단 한 번만 쓸 수 있는 임시 코드** 발급
3. 앱 서버 → 임시 코드를 Keycloak 에 제출하여 **실제 토큰** 교환

> 💡 임시 코드 = 은행 번호표 (한 번 쓰면 사라짐)

이 프로젝트에서 **Airflow 웹 UI 로그인**에 사용됩니다.

---

### 🔑 Bearer Token (베어러 토큰)

**API 를 호출할 때 "내가 인증된 사용자야"를 증명하는 방법** 입니다.

HTTP 요청 헤더에 토큰을 첨부합니다:

```
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
```

> 💡 Bearer Token = 입장권을 들고(bear) 있는 것처럼, 토큰을 보여주면 입장 허용

---

### 📋 용어 한눈에 보기

| 용어 | 한 줄 설명 |
|---|---|
| **SSO** | 한 번 로그인으로 여러 서비스 이용 |
| **Keycloak** | 로그인·사용자 관리 전담 서버 |
| **OAuth2** | 앱에게 내 정보 접근을 허가하는 표준 방법 |
| **OIDC** | OAuth2 + 신원 확인 기능 |
| **JWT** | 위조 불가능한 디지털 출입증 |
| **Access Token** | API 접근용 단기 출입증 |
| **Refresh Token** | Access Token 재발급용 쿠폰 |
| **Airflow** | 작업 흐름 자동 실행 스케줄러 |
| **DAG** | Airflow 에서 작업 순서를 정의한 흐름도 |
| **XCom** | Airflow 태스크 간 데이터 전달 우편함 |
| **Docker** | 앱 실행 환경을 담은 컨테이너 |
| **Docker Compose** | 여러 컨테이너를 한 번에 관리 |
| **PostgreSQL** | 표 형태로 데이터를 저장하는 DB |
| **FastAPI** | Python REST API 서버 프레임워크 |
| **Realm** | Keycloak 안의 독립 인증 구역 |
| **Bearer Token** | API 호출 시 인증을 증명하는 토큰 첨부 방식 |

---

## 1. 구현 목표

1. **통합 인증 서버(IdP)**
   - Keycloak 기반 인증 서버
   - OAuth2 / OpenID Connect(OIDC) 기반 인증
   - Access Token / Refresh Token 발급 및 검증

2. **회원 관리**
   - 단일 사용자 식별자(`customer_id`) 기반 관리
   - 회원 단계 개념 지원  
     (`visitor` → `consulting_customer` → `member` → `service_user` → `medical_service_user`)
   - 계정 상태 관리 (`active`, `dormant`, `withdrawn`)

3. **동의 관리**
   - 공통 동의 + 서비스별 동의 구조
   - 필수/선택 동의 구분
   - 목적/버전/국가/언어 단위 동의 이력 관리

4. **Airflow 배치 워크플로**
   - Keycloak OAuth2 로 Airflow 웹 UI 로그인(SSO)
   - Keycloak 토큰을 발급받아 보호된 Backend API 를 호출하는 DAG
   - 회원 등록 → 상태 변경 → 동의 등록의 실제 배치 워크플로 DAG

---

## 2. 전체 아키텍처

```text
[브라우저 / Airflow UI]
         |
         | OAuth2/OIDC (SSO Login)
         v
  [Keycloak :8080]  ←──────────────────────────┐
         |                                      |
         | JWT 발급                             |
         v                                      |
[Airflow Webserver :8888]   [Airflow Scheduler] |
         |                          |           |
         | DAG 실행                  |           |
         v                          |           |
[Python Backend :8000]  ←───────────┘           |
     (FastAPI)           REST API + Bearer Token |
         |                                      |
         v                                      |
   [PostgreSQL :5432]  ←─────────────────────── ┘
   ┌─────────────────┐   DB
   │  keycloak (DB)  │
   │  app_db   (DB)  │
   │  airflow  (DB)  │
   └─────────────────┘
```

| 컴포넌트 | 역할 |
|---|---|
| **Keycloak** | OAuth2/OIDC IdP – 토큰 발급, 사용자 관리, Airflow SSO 인증 제공 |
| **Backend (FastAPI)** | REST API 서버 – Keycloak JWT 검증 후 회원·동의 데이터 처리 |
| **Airflow** | 배치 워크플로 오케스트레이터 – Keycloak 인증 기반 DAG 실행 |
| **PostgreSQL** | 모든 서비스(Keycloak·Backend·Airflow)의 메타데이터 저장 |

---

## 3. 기술 스택

| 분류 | 기술 | 버전 |
|---|---|---|
| **Backend** | Python, FastAPI, SQLAlchemy, httpx | Python 3.12, FastAPI latest |
| **Frontend** | HTML + Tailwind CSS | — |
| **IdP** | Keycloak | 26.1.4 |
| **Auth Protocol** | OAuth2, OpenID Connect | RFC 6749 / OpenID Foundation |
| **Workflow** | Apache Airflow | 2.9.3 |
| **Airflow Executor** | LocalExecutor (PostgreSQL metadb) | — |
| **Airflow Auth** | Flask-AppBuilder OAuth2 (Keycloak) | — |
| **DB** | PostgreSQL | 16 |
| **Infra** | Docker Compose | v2 |

---

## 4. 디렉토리 구조

```text
.
├── airflow/
│   ├── dags/
│   │   ├── dag_01_health_check.py        ← Keycloak/Backend 헬스 체크 DAG
│   │   ├── dag_02_keycloak_token_flow.py ← OAuth2 토큰 발급 → API 호출 DAG
│   │   └── dag_03_member_lifecycle.py    ← 회원 등록/상태/동의 워크플로 DAG
│   └── webserver_config.py              ← Airflow 웹 UI Keycloak OAuth2 설정
├── backend/
│   ├── app/
│   │   ├── auth.py    ← Keycloak 토큰 발급·검증·userinfo 호출
│   │   ├── config.py  ← 환경변수 기반 설정(Pydantic Settings)
│   │   ├── db.py      ← SQLAlchemy 세션 관리
│   │   ├── main.py    ← FastAPI 라우터
│   │   ├── models.py  ← ORM 모델(Member, Consent)
│   │   ├── schemas.py ← Pydantic 스키마
│   │   └── static/index.html  ← Tailwind 로그인 UI
│   ├── Dockerfile
│   └── requirements.txt
├── captures/              ← 실행 화면 스크린샷
├── artifacts/             ← JWT·로그인 테스트 결과
├── infra/
│   ├── keycloak/realm/integrated-id-realm.json  ← Realm 자동 임포트 설정
│   └── postgres/init/01-init-databases.sql      ← keycloak·app_db·airflow DB 초기화
├── scripts/
│   ├── provision-users-and-test.sh  ← 계정 생성 + JWT 발급 + 로그인 테스트
│   └── capture-screens.sh           ← 화면 캡처
└── docker-compose.yml
```

---

## 5. 실행 방법

### 5.1 사전 요구사항

- Docker Engine 24+
- Docker Compose v2.1+  
  (`service_completed_successfully` 조건을 지원하는 버전 필요)

### 5.2 컨테이너 기동

일반 환경:

```bash
docker compose up -d --build
```

`docker-buildx` 가 없는 환경:

```bash
DOCKER_BUILDKIT=0 docker compose up -d --build
```

> **기동 순서**  
> `postgres` (healthy) → `keycloak` / `backend` / `airflow-init`  
> → `airflow-webserver` / `airflow-scheduler` (airflow-init 완료 후)

### 5.3 기동 상태 확인

```bash
docker compose ps
```

정상 상태 예시:

```
NAME                    STATUS
dko-postgres            Up (healthy)
dko-keycloak            Up
dko-backend             Up
dko-airflow-init        Exited (0)     ← 정상 종료(초기화 완료)
dko-airflow-webserver   Up (healthy)
dko-airflow-scheduler   Up (healthy)
```

### 5.4 컨테이너 중지

```bash
docker compose down
```

데이터 볼륨까지 삭제 (초기화):

```bash
docker compose down -v
```

---

## 6. 접속 정보

| 서비스 | URL | 설명 |
|---|---|---|
| **Airflow UI** | http://localhost:8888 | 워크플로 관리 (Keycloak SSO 로그인) |
| **Backend Swagger** | http://localhost:8000/docs | FastAPI API 문서 |
| **Frontend(Login UI)** | http://localhost:8000/app-ui | Tailwind 로그인 UI |
| **Keycloak Admin** | http://localhost:8080 | Keycloak 관리 콘솔 |
| **Keycloak Realm** | http://localhost:8080/realms/integrated-id | Realm 메타데이터 |

---

## 7. 계정 정보

### 7.1 Keycloak 관리자

| 항목 | 값 |
|---|---|
| Keycloak Admin | `admin / admin1234` |

### 7.2 데모 사용자 (Keycloak Realm: `integrated-id`)

아래 계정으로 **Airflow UI** 및 **Backend API** 모두 로그인할 수 있습니다.

| 사용자명 | 비밀번호 | 이메일 |
|---|---|---|
| `demo-user` | `demo1234` | demo-user@example.com |
| `demo-user2` | `demo2234` | demo-user2@example.com |
| `demo-user3` | `demo3234` | demo-user3@example.com |

### 7.3 Keycloak 클라이언트

| Client ID | 용도 | Secret |
|---|---|---|
| `be-client` | FastAPI Backend OIDC 클라이언트 | `be-client-secret` |
| `airflow-client` | Airflow 웹 UI OAuth2 로그인 클라이언트 | `airflow-client-secret` |

---

## 8. Airflow 상세 설명

### 8.1 Airflow + Keycloak SSO 로그인 흐름

Airflow 웹 UI 는 `AUTH_TYPE = AUTH_OAUTH` 로 설정되어 Keycloak 을 통해서만 로그인합니다.

```text
[브라우저]                    [Airflow Webserver]          [Keycloak]
    |                                |                         |
    |-- GET http://localhost:8888 -->|                         |
    |<-- 302 Redirect --------------|                         |
    |                                                          |
    |-- GET /realms/integrated-id/protocol/openid-connect/auth (localhost:8080)
    |                                                          |
    |<-- 로그인 UI 표시 ----------------------------------------|
    |                                                          |
    |-- POST (username/password) ------------------------------>|
    |<-- 302 ?code=AUTH_CODE -----------------------------------| 
    |                                                          |
    |-- GET http://localhost:8888/oauth-authorized/keycloak?code=...
    |                                |                         |
    |                                |-- POST /token (code) -->|  (내부 네트워크)
    |                                |<-- {access_token} ------|
    |                                |-- GET /userinfo ------->|  (내부 네트워크)
    |                                |<-- {email, name} --------|
    |                                |                         |
    |                                | (최초 로그인 시 DB 에 자동 등록 / Admin 역할 부여)
    |<-- Airflow Dashboard ----------|
```

**핵심 포인트:**

| URL 종류 | 사용 URL | 이유 |
|---|---|---|
| `authorize_url` (브라우저 리다이렉트) | `http://localhost:8080/...` | 브라우저가 직접 접근 |
| `access_token_url` (서버→Keycloak) | `http://keycloak:8080/...` | Docker 내부 네트워크 |
| `userinfo_endpoint` (서버→Keycloak) | `http://keycloak:8080/...` | Docker 내부 네트워크 |

### 8.2 Airflow 웹 UI 로그인 방법

1. 브라우저에서 http://localhost:8888 접속
2. **"Sign in with Keycloak"** 버튼 클릭
3. Keycloak 로그인 페이지에서 데모 계정으로 로그인  
   예: `demo-user / demo1234`
4. 최초 로그인 시 Airflow DB 에 **Admin** 권한으로 자동 등록

> **참고:** `AUTH_USER_REGISTRATION_ROLE = "Admin"` 으로 설정되어 있어  
> Keycloak 으로 로그인하는 모든 사용자는 Airflow Admin 권한을 받습니다.  
> 운영 환경에서는 `Viewer` 로 변경하고 역할 매핑(`AUTH_ROLES_MAPPING`)을 사용하세요.

### 8.3 Airflow 환경변수 설명

`docker-compose.yml` 의 `x-airflow-common` 공통 블록에 정의된 환경변수:

| 환경변수 | 값 | 설명 |
|---|---|---|
| `AIRFLOW__CORE__EXECUTOR` | `LocalExecutor` | Worker 없이 DB 기반으로 태스크 실행 |
| `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` | `postgresql+psycopg2://airflow:airflow@postgres:5432/airflow` | Airflow 메타데이터 DB |
| `AIRFLOW__CORE__FERNET_KEY` | `ZmDfcTF7_...` | XCom·Variables 암호화 키 |
| `AIRFLOW__WEBSERVER__SECRET_KEY` | `airflow-dev-secret-key-...` | Flask 세션 서명 키 |
| `AIRFLOW__WEBSERVER__BASE_URL` | `http://localhost:8888` | OAuth2 콜백 URL 생성 기준 |
| `AIRFLOW__CORE__LOAD_EXAMPLES` | `false` | 예제 DAG 비활성화 |
| `KEYCLOAK_BASE_URL` | `http://keycloak:8080` | DAG 에서 참조하는 Keycloak URL |
| `KEYCLOAK_REALM` | `integrated-id` | DAG 에서 참조하는 Realm |
| `BACKEND_BASE_URL` | `http://backend:8000` | DAG 에서 참조하는 Backend URL |

> **운영 전 변경 필수:** `FERNET_KEY`, `SECRET_KEY` 는 반드시 안전한 값으로 교체하세요.  
> Fernet 키 생성: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

---

## 9. 예제 DAG 설명

### DAG 01 – 헬스 체크 (`dag_01_health_check`)

| 항목 | 내용 |
|---|---|
| **실행 주기** | 5분마다 자동 실행 |
| **목적** | Keycloak 과 Backend API 의 가용성을 주기적으로 모니터링 |
| **태그** | `health`, `keycloak`, `backend` |

**태스크 흐름:**

```text
check_keycloak  ──(병렬)──  check_backend
```

| 태스크 | 호출 엔드포인트 | 성공 조건 |
|---|---|---|
| `check_keycloak` | `GET /realms/integrated-id` | HTTP 200 + realm 정보 반환 |
| `check_backend` | `GET /api/v1/health` | HTTP 200 + `status: "ok"` |

---

### DAG 02 – Keycloak 토큰 발급 흐름 (`dag_02_keycloak_token_flow`)

| 항목 | 내용 |
|---|---|
| **실행 주기** | 수동 트리거 (Airflow UI 에서 ▶ 버튼 클릭) |
| **목적** | OAuth2 Direct Grant 로 토큰을 발급받고 보호된 API 를 호출하는 전 과정 시연 |
| **태그** | `oauth2`, `keycloak`, `token`, `backend` |

**태스크 흐름:**

```text
fetch_keycloak_token
    ├──> decode_token_claims     (JWT 클레임 디코딩·출력)
    ├──> call_protected_userinfo (Bearer 토큰으로 /auth/userinfo 호출)
    └──> call_protected_members  (Bearer 토큰으로 /members 목록 조회)
```

**XCom 데이터 흐름:**

```text
fetch_keycloak_token
  └── xcom_push(key="access_token") ──> 3개 하위 태스크에서 xcom_pull 로 사용
```

| 태스크 | 동작 설명 |
|---|---|
| `fetch_keycloak_token` | Keycloak `/token` 엔드포인트에 Direct Grant 요청 → Access Token 발급 |
| `decode_token_claims` | JWT Payload 를 Base64 디코딩 → `sub`, `email`, `preferred_username`, `exp` 출력 |
| `call_protected_userinfo` | `Authorization: Bearer {token}` 헤더로 Backend `/auth/userinfo` 호출 |
| `call_protected_members` | 동일 토큰으로 Backend `/members` 전체 목록 조회 |

---

### DAG 03 – 회원 라이프사이클 (`dag_03_member_lifecycle`)

| 항목 | 내용 |
|---|---|
| **실행 주기** | 매일 자정 (`@daily`) |
| **목적** | Keycloak 인증 기반으로 회원 등록 → 상태 변경 → 동의 등록의 전체 워크플로 시연 |
| **태그** | `member`, `consent`, `lifecycle`, `keycloak`, `backend` |

**태스크 흐름:**

```text
get_auth_token
    └──> create_member
             ├──> update_member_status  (active → dormant)
             └──> register_consent      (서비스 이용 동의 등록)
                      └──> verify_consents  (동의 목록 조회·검증)
```

> `update_member_status` 와 `register_consent` 는 병렬 실행된 후 `verify_consents` 로 합류합니다.

| 태스크 | 호출 API | 동작 설명 |
|---|---|---|
| `get_auth_token` | `POST /token` | Keycloak 에서 Access Token 발급 → XCom 저장 |
| `create_member` | `POST /api/v1/members` | 실행 날짜 기반 `customer_id` 로 신규 회원 등록 (409 는 멱등 처리) |
| `update_member_status` | `PATCH /api/v1/members/{id}/status` | 회원 상태를 `dormant` 로 변경 |
| `register_consent` | `POST /api/v1/consents` | 서비스 이용 동의 항목 등록 (409 는 멱등 처리) |
| `verify_consents` | `GET /api/v1/members/{id}/consents` | 동의 목록 조회 후 1건 이상인지 검증 |

**멱등성(Idempotency):**  
`customer_id = batch-{YYYYMMDD}` 형식으로 생성하여 같은 날 재실행해도  
`409 Conflict` 를 무시하고 정상 완료됩니다.

---

## 10. DAG 수동 실행 방법

### 10.1 Airflow UI 에서 실행

1. http://localhost:8888 → Keycloak 로그인
2. **DAGs** 탭에서 원하는 DAG 선택
3. 우측 상단 **▶ (Trigger DAG)** 버튼 클릭
4. **Graph View** 에서 태스크 실행 상태 확인
5. 태스크 클릭 → **Log** 탭에서 실행 로그 확인

### 10.2 CLI 에서 실행

```bash
# DAG 02 수동 트리거
docker compose exec airflow-scheduler airflow dags trigger dag_02_keycloak_token_flow

# DAG 03 수동 트리거 (실행 날짜 지정)
docker compose exec airflow-scheduler airflow dags trigger dag_03_member_lifecycle \
  --conf '{"run_date": "2024-01-01"}'

# 특정 DAG 의 최근 실행 상태 확인
docker compose exec airflow-scheduler airflow dags list-runs -d dag_01_health_check

# 태스크 로그 확인
docker compose exec airflow-scheduler \
  airflow tasks logs dag_02_keycloak_token_flow fetch_keycloak_token <run_id>
```

---

## 11. 계정/JWT/로그인 테스트 자동 실행

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

---

## 12. Backend API 요약

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/v1/health` | DB/Keycloak 연결 상태 |
| GET | `/api/v1/auth/login-url` | Keycloak 인증 URL 생성 |
| POST | `/api/v1/auth/token` | Keycloak 토큰 발급(Direct Grant) |
| GET | `/api/v1/auth/userinfo` | Access Token 기반 사용자 정보 |
| POST | `/api/v1/members` | 회원 생성 |
| GET | `/api/v1/members` | 회원 목록 |
| PATCH | `/api/v1/members/{customer_id}/status` | 회원 상태 변경 |
| POST | `/api/v1/consents` | 동의 생성 |
| GET | `/api/v1/members/{customer_id}/consents` | 회원 동의 조회 |

### 12.1 예시: 토큰 발급 및 사용자 정보 조회

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

---

## 13. 실행 화면 캡처

스크린샷 재생성:

```bash
./scripts/capture-screens.sh
```

저장 경로:

- `captures/backend-swagger.png`
- `captures/keycloak-login.png`
- `captures/fe-login-success.png`

### 13.1 Backend Swagger

![Backend Swagger](./captures/backend-swagger.png)

### 13.2 Keycloak Login

![Keycloak Login](./captures/keycloak-login.png)

### 13.3 Frontend Login Success

![Frontend Login Success](./captures/fe-login-success.png)

---

## 14. OIDC / OAuth2 기술 설명

### 14.1 OAuth2 와 OIDC 개요

**OAuth2** 는 제3자 애플리케이션이 사용자를 대신해 리소스에 접근할 수 있도록 허가하는 **위임 인가(Authorization) 프레임워크**입니다.  
**OIDC(OpenID Connect)** 는 OAuth2 위에 **인증(Authentication) 레이어**를 추가한 프로토콜로, `ID Token` 이라는 JWT 를 통해 "누가 로그인했는지"를 검증합니다.

| 구분 | OAuth2 | OIDC |
|---|---|---|
| 목적 | 인가 (Authorization) | 인증 (Authentication) |
| 결과물 | Access Token | ID Token + Access Token |
| 표준 | RFC 6749 | OpenID Foundation |
| 사용자 정보 | `/userinfo` 엔드포인트 별도 호출 | ID Token 클레임에 직접 포함 가능 |

### 14.2 주요 역할(Roles)

```text
[Resource Owner]   : 최종 사용자 (demo-user 등)
[Client]           : 인가를 요청하는 애플리케이션 (FastAPI Backend, Airflow)
[Authorization Server / IdP] : 인증 및 토큰 발급 서버 (Keycloak)
[Resource Server]  : 보호된 리소스 제공 서버 (FastAPI /api/v1/*)
```

### 14.3 Keycloak OIDC 엔드포인트

**Discovery 문서 URL:**

```
http://localhost:8080/realms/integrated-id/.well-known/openid-configuration
```

| 엔드포인트 | URL 패턴 | 용도 |
|---|---|---|
| Authorization | `/realms/{realm}/protocol/openid-connect/auth` | 인증 코드 요청 (브라우저 리다이렉트) |
| Token | `/realms/{realm}/protocol/openid-connect/token` | 토큰 발급 / 갱신 |
| UserInfo | `/realms/{realm}/protocol/openid-connect/userinfo` | Access Token 으로 사용자 정보 조회 |
| Introspection | `/realms/{realm}/protocol/openid-connect/token/introspect` | 토큰 유효성 서버 사이드 검증 |
| End Session | `/realms/{realm}/protocol/openid-connect/logout` | 로그아웃 (세션 종료) |
| JWKS | `/realms/{realm}/protocol/openid-connect/certs` | 토큰 서명 검증용 공개 키 |

### 14.4 OIDC Authorization Code Flow

Airflow UI 로그인에 사용되는 표준 웹 애플리케이션 인증 흐름:

```text
[브라우저]             [Airflow Webserver]         [Keycloak IdP]
    |                          |                           |
    |-- GET /                ->|                           |
    |<-- 302 /oauth-login -----|                           |
    |                          |                           |
    |-- GET /auth?client_id=airflow-client&redirect_uri=...------>|
    |                          |         (로그인 UI 표시)          |
    |<------------------------------------------------------|
    |                                                       |
    |--(사용자 로그인: demo-user/demo1234)----------------->|
    |<-- 302 ?code=AUTH_CODE --------------------------------|
    |                          |                           |
    |-- GET /oauth-authorized/keycloak?code=... ----------->|
    |                          |                           |
    |                          |-- POST /token (code) --->|  (내부)
    |                          |<-- {access_token} --------|
    |                          |-- GET /userinfo ---------->|  (내부)
    |                          |<-- {email, name} ----------|
    |<-- Airflow Dashboard -----|
```

### 14.5 Direct Grant Flow (DAG 에서 사용)

DAG 내에서 API 호출 시 사용하는 방식 (데모/배치 전용):

```text
[Airflow DAG Task]                    [Keycloak IdP]
    |                                       |
    |-- POST /token ----------------------->|
    |   grant_type=password                 |
    |   username / password                 |
    |   client_id / client_secret           |
    |<-- {access_token, expires_in, ...} ---|
    |                                       |
    |-- GET /api/v1/members (Bearer token) ->|  [Backend]
    |<-- [{member data}] ─────────────────────────────────|
```

> 운영 환경에서는 반드시 **Authorization Code + PKCE** 흐름을 사용하세요.

### 14.6 토큰 종류 및 역할

| 토큰 | 형식 | 용도 | 유효기간(예시) |
|---|---|---|---|
| **ID Token** | JWT (서명됨) | 사용자 신원 확인 (OIDC 전용) | 5분 |
| **Access Token** | JWT (서명됨) | API 리소스 접근 인가 | 5분 |
| **Refresh Token** | Opaque 또는 JWT | Access Token 갱신 | 30분~수일 |

### 14.7 Keycloak Realm / Client 구성

```
Keycloak
└── Realm: integrated-id
    ├── Clients
    │   ├── be-client              ← FastAPI Backend OIDC 클라이언트
    │   │   ├── Standard Flow: 활성화
    │   │   ├── Direct Access Grants: 활성화
    │   │   └── Service Accounts: 활성화
    │   └── airflow-client         ← Airflow 웹 UI OAuth2 클라이언트
    │       ├── Standard Flow: 활성화 (Authorization Code Flow)
    │       └── Direct Access Grants: 활성화 (DAG 내 토큰 발급용)
    ├── Roles
    │   ├── member
    │   └── medical-user
    └── Users
        ├── demo-user
        ├── demo-user2
        └── demo-user3
```

### 14.8 Airflow + Flask-AppBuilder OAuth2 설정 포인트

`airflow/webserver_config.py` 에서 설정하는 주요 항목:

| 설정 | 값 | 설명 |
|---|---|---|
| `AUTH_TYPE` | `AUTH_OAUTH` | OAuth2 공급자(Keycloak)로만 로그인 |
| `AUTH_USER_REGISTRATION` | `True` | 최초 로그인 시 자동 사용자 등록 |
| `AUTH_USER_REGISTRATION_ROLE` | `"Admin"` | 자동 등록 사용자의 기본 역할 (데모용) |
| `AUTH_ROLES_SYNC_AT_LOGIN` | `True` | 로그인 시마다 Keycloak 역할 동기화 |
| `OAUTH_PROVIDERS[].authorize_url` | `http://localhost:8080/...` | 브라우저가 접근 가능한 외부 URL |
| `OAUTH_PROVIDERS[].access_token_url` | `http://keycloak:8080/...` | 서버 간 내부 네트워크 URL |

---

## 15. 운영 전 고려사항

| 항목 | 현재(PoC) | 운영 권장 |
|---|---|---|
| 인증 방식 | Direct Grant (DAG) | Authorization Code + PKCE |
| Airflow Fernet Key | 고정값 | `Fernet.generate_key()` 로 생성 후 Secret Manager 관리 |
| Airflow Secret Key | 고정값 | 환경변수 또는 Secret Manager |
| Airflow 역할 부여 | 모든 사용자 Admin | `AUTH_USER_REGISTRATION_ROLE = "Viewer"` + 역할 매핑 |
| Airflow Executor | LocalExecutor | CeleryExecutor / KubernetesExecutor |
| TLS | 없음 | Nginx/Ingress + Let's Encrypt |
| 민감 정보 | 환경변수 직접 설정 | `.env` + Docker Secrets / Vault |
| DB 계정 | 단순 패스워드 | 강한 패스워드 + SSL 연결 |
| Keycloak Direct Grant | 활성화 | 비활성화 (운영 환경) |

