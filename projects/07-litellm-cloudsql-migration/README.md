# LiteLLM Cloud SQL 마이그레이션과 DB Connection 안정화

## Overview

Kubernetes 클러스터 안에서 StatefulSet으로 운영하던 LiteLLM PostgreSQL을 Cloud SQL for PostgreSQL로 이전했습니다. PostgreSQL 18.4에서 17로 버전이 낮아지는 조건에서도 데이터를 안전하게 옮길 수 있는지 로컬 환경에서 먼저 검증했고, 실제 운영에서는 스키마 생성과 데이터 이관을 컷오버 하루 전에 끝내 전환 시점의 작업을 LiteLLM 파드 교체로 줄였습니다.

전환 직후 기존 Virtual Key와 실제 LLM 호출을 확인했고, 운영 안정화 후 In-cluster PostgreSQL을 폐기했습니다. 이후 DB Connection Full 문제가 발생해 PgBouncer를 도입했습니다. 현재는 최대 100개인 Cloud SQL 연결을 40개 미만으로 유지하고 있습니다.

## Architecture

### Before

```text
[내부 서비스 / 업무 자동화]
              │
              ▼
       [LiteLLM Pods]
              │
              ▼
[In-cluster PostgreSQL StatefulSet]
```

### After

```text
[내부 서비스 / 업무 자동화]
              │
              ▼
       [LiteLLM Pods]
              │
              ▼
          [PgBouncer]
              │
              ▼
 [Cloud SQL for PostgreSQL 17]
```

## Problem

### 1. In-cluster PostgreSQL의 운영 부담

LiteLLM의 인증·팀·비용 데이터를 단일 PostgreSQL StatefulSet에 저장하고 있었습니다. 데이터베이스 가용성, 백업, 복구와 스토리지 관리를 Kubernetes 클러스터 안에서 직접 책임져야 했고, 장애 시 LiteLLM 전체가 영향을 받는 구조였습니다.

### 2. PostgreSQL 버전 차이

기존 데이터베이스는 PostgreSQL 18.4였지만 이전 대상인 Cloud SQL은 PostgreSQL 17을 사용해야 했습니다. 전체 스키마를 그대로 복원하는 방식은 버전 차이로 인한 실패 가능성이 있어, 신규 스키마와 기존 데이터를 분리해 이관하는 절차가 필요했습니다.

### 3. LiteLLM 마이그레이션 경로의 불명확성

LiteLLM 메인 저장소에서 일반적인 Prisma migration 디렉터리를 찾을 수 없었습니다. 운영 이미지 내부를 확인한 결과 migration 파일과 `schema.prisma`가 `litellm_proxy_extras` Python 패키지에 포함된 구조임을 확인했습니다.

### 4. 컷오버 중 데이터 변경

서비스를 오래 중단하지 않으면서도 기존 Virtual Key와 핵심 설정은 보존해야 했습니다. 반면 호출 로그와 리포트 데이터는 컷오버 직전까지 계속 쌓이기 때문에 모든 데이터를 같은 시점으로 맞추면 전환 시간이 길어지는 문제가 있었습니다.

## Key Decisions

### 1. 스키마와 데이터를 분리해 이관

Cloud SQL에는 LiteLLM 운영 이미지를 사용한 Kubernetes Job으로 Prisma migration을 먼저 적용했습니다. 기존 PostgreSQL에서는 데이터만 덤프해 `pg_restore --data-only`로 복원했습니다. 이 방식으로 PostgreSQL 버전 차이가 스키마 복원에 미치는 영향을 줄였습니다.

### 2. 운영 전 전체 흐름 리허설

운영 백업본을 사용해 minikube의 PostgreSQL 17 환경에서 전체 이관 절차를 먼저 실행했습니다. Prisma migration 적용부터 데이터 복원, 외래키 검사와 LiteLLM 기동까지 한 번에 재현했으며 세부 결과는 아래 Validation 표에 정리했습니다.

실제 Virtual Key를 이용한 LLM 호출과 Provider 자격증명 복호화는 로컬에서 검증할 수 없어 운영 컷오버 직후의 필수 확인 항목으로 남겼습니다.

### 3. 하루 전 데이터 이관

컷오버 하루 전에 Cloud SQL 스키마 생성과 기존 DB 데이터 이관을 완료했습니다. 인증과 서비스 운영에 필요한 데이터는 보존하되, 이후 생성된 하루치 호출 로그와 리포트 데이터는 유실을 감수했습니다. 덕분에 실제 컷오버 구간에서는 DB 복원 작업을 제외할 수 있었습니다.

### 4. Endpoint 변경을 이용한 파드 전환

기존 LiteLLM 파드는 In-cluster PostgreSQL을 바라보는 상태로 유지했습니다. Helm values의 DB endpoint를 Cloud SQL로 변경한 뒤 배포해, 새 파드는 생성되는 즉시 Cloud SQL에 연결하도록 했습니다.

Rolling update 중에는 기존 파드와 신규 파드가 서로 다른 DB를 바라보는 구간이 있었습니다. T-1일 이후의 호출 로그와 리포트 데이터가 기존 DB에 남을 수 있음을 감수한 상태에서 신규 파드의 Cloud SQL 연결, 기존 Virtual Key 인증과 실제 LLM 호출을 차례로 확인했습니다. 검증을 마친 뒤 기존 파드를 제거했고, 운영 안정화 후 In-cluster PostgreSQL도 폐기했습니다.

## Migration Flow

```text
[T-1일]
Cloud SQL PG 17 준비
  → Prisma migration 사전 적용
  → 기존 DB 데이터 이관
  → 무결성 및 LiteLLM 기동 검증

[Cutover]
Helm values의 DB endpoint 변경
  → 신규 LiteLLM 파드 생성
  → Cloud SQL 연결 확인
  → 기존 Virtual Key 검증
  → 실제 LLM 호출 검증
  → 기존 파드 제거

[안정화 후]
In-cluster PostgreSQL 폐기
```

## Post-migration Issue: DB Connection Full

Cloud SQL 전환 후 DB 연결 수가 `max_connections`인 100개에 도달하면서 Connection Full 문제가 발생했습니다. 당시 LiteLLM 파드는 Cloud SQL에 직접 연결하는 구조였습니다.

애플리케이션과 Cloud SQL 사이에 PgBouncer를 추가했습니다. 여러 클라이언트 연결을 제한된 DB 연결로 중계한 뒤부터 실제 연결 수를 40개 미만으로 유지하고 있습니다.

```text
Before: LiteLLM Pods ──────────────> Cloud SQL (Connection Full)

After : LiteLLM Pods ─> PgBouncer ─> Cloud SQL (< 40 / max 100)
```

## Validation

| 단계 | 검증 항목 | 결과 |
| --- | --- | --- |
| 로컬 리허설 | Prisma migration | 122개 적용, Job 실행 6초 |
| 로컬 리허설 | 운영 데이터 복원 | 55개 테이블 복원 |
| 로컬 리허설 | 외래키 무결성 | 28개 검사, 위반 0건 |
| 로컬 리허설 | LiteLLM 기동 | DB readiness 정상 |
| 운영 컷오버 | 기존 Virtual Key | 정상 인증 확인 |
| 운영 컷오버 | 실제 LLM 호출 | 정상 응답 확인 |
| 운영 안정화 | 기존 PostgreSQL | 폐기 완료 |
| 운영 안정화 | Cloud SQL 연결 수 | PgBouncer 도입 후 40개 미만 유지 |

## Results

- PostgreSQL 18.4 기반 In-cluster DB를 Cloud SQL PostgreSQL 17로 이전했습니다.
- 스키마 생성과 데이터 이관을 하루 전에 수행해 실제 컷오버에서 DB 복원 작업을 제거했습니다.
- 기존 Virtual Key를 재발급하지 않고 인증과 실제 LLM 호출이 정상 동작하는 것을 확인했습니다.
- 안정화 후 기존 PostgreSQL StatefulSet을 폐기해 클러스터 내부의 Stateful 운영 부담을 줄였습니다.
- PgBouncer 도입 후 최대 100개인 Cloud SQL 연결을 40개 미만으로 유지하고 있습니다.

## Trade-offs

- 컷오버 시간을 줄이는 대신 이관 이후 생성된 하루치 호출 로그와 리포트 데이터의 유실을 수용했습니다.
- Rolling update 중 기존 파드와 신규 파드가 서로 다른 DB endpoint를 바라봤습니다. 이 구간에 기존 DB로 쌓인 호출 로그와 리포트 데이터는 유실 범위에 포함했습니다.
- Cloud SQL 전환만으로 Connection 관리가 끝나지는 않았습니다. 직접 연결 구조에서 한도에 도달한 뒤 PgBouncer를 추가했습니다.

## Retrospective

사전 리허설에서 PostgreSQL 버전 차이와 LiteLLM migration 구조를 먼저 확인했습니다. 스키마 적용과 데이터 복원, 애플리케이션 전환을 나눠 진행한 덕분에 컷오버 당일에는 파드 교체와 기능 검증에 집중할 수 있었습니다.

DB 연결 한도 검증은 부족했습니다. 데이터 정합성과 기능만 확인할 것이 아니라 파드·워커 수에 따른 Connection Pool 크기, DB 연결 한도와 장애 임계치까지 리허설에 포함해야 한다는 교훈을 얻었습니다.

## Tech Stack

- **Application**: LiteLLM Proxy, Prisma
- **Database**: PostgreSQL 18.4, Cloud SQL for PostgreSQL 17, PgBouncer
- **Infrastructure**: GKE, Kubernetes, Helm
- **Migration / Validation**: Kubernetes Job, pg_dump, pg_restore, SQL

> 실제 업무 경험을 바탕으로 작성했으며, 내부 클러스터·계정·Secret 등 민감한 식별 정보는 제거하거나 일반화했습니다.
