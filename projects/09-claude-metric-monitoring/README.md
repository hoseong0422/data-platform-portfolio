# Claude Metric Monitoring · Signal to Seat Decision

## Overview

Claude Code와 claude.ai의 사용 흔적을 OpenTelemetry 기반으로 관측하고, ClickStack·데이터 파이프라인·익명 분석을 연결해 사용량을 좌석 운영 판단으로 바꾼 프로젝트입니다.

모니터링을 대시보드 하나로 끝내지 않고 `수집 → 저장 → 보존 → 집계 → 추천`의 전체 경로로 설계했습니다. 분석용 원문·개인 식별자·접근 자격 증명은 포트폴리오 범위에 포함하지 않았습니다.

## Problem

- Claude Code, claude.ai, Delivery 신호가 서로 다른 형태로 쌓여 바로 비교하기 어려웠습니다.
- RAW 보존 기간과 ClickHouse 비용·복구 요구를 함께 만족해야 했습니다.
- Premium 좌석 상향을 단일 중앙값으로 판단하면 순간적인 spike만으로 후보가 과다하게 추천됐습니다.
- 사용량 분석은 개인 정보와 프롬프트 원문을 포함할 수 있어 공유 범위와 지표 정의를 먼저 정해야 했습니다.

## Key Decisions

### 1. 로컬 PoC에서 조직 운영 레이어로 확장

초기에는 Docker 기반 ClickStack(HyperDX·ClickHouse·OpenTelemetry Collector)으로 Claude Code 신호와 대시보드 형태를 빠르게 검증했습니다. 조직 모니터링은 GKE ClickStack과 일배치 Mart로 확장했습니다.

### 2. HOT / COLD / Mart 수명주기 분리

```text
Claude Code ──OTLP──> OTel Collector ──> ClickHouse
claude.ai export ────────────────────────┘
                              │
                     40-day HOT / Materialized View
                              │
                    GCS Parquet COLD RAW
                              │
                  BigQuery Mart ──> Looker / Sheet
```

- ClickHouse는 실시간 탐색과 최근 기간 집계에 사용
- Materialized View와 일배치로 분석 Mart를 생성
- RAW는 GCS Parquet로 보존해 재집계 가능하게 구성
- BigQuery Mart와 Looker에서 좌석 활용·재배정 신호를 확인

### 3. 개인정보와 공유 범위를 경로에서 분리

- 사용자 식별자는 첫 마스킹 단계에서 처리
- 전사 공유용 JSON/HTML에는 익명 집계만 남김
- 좌석 후보와 개인 식별이 필요한 결과는 `internal_only` 범위로 분리
- 프롬프트·도구 본문·raw API body는 기본 분석 재료로 포함하지 않음
- 지표 정의와 날짜 기준도 버전 기록

## Signal Model

8개 메트릭을 세 가지 신호로 묶었습니다.

| 신호 | 예시 |
| --- | --- |
| Chat | 활성 사용자·메시지·대화 |
| Claude Code | 세션·토큰·비용·활성 시간·코드 라인 |
| Delivery | 커밋·PR·편집 결정·trace |

운영 화면은 초기 5종에서 Seat Utilization을 추가해 6개 대시보드로 확장했습니다.

- All Metrics
- Events & Logs
- Prompts
- Traces & Latency
- ROI
- Seat Utilization

## Evidence Snapshot

2026-07-01부터 2026-07-29까지 29일의 익명 집계 결과입니다. 내부 비용 환산액은 청구액이 아닙니다.

| 항목 | 관측값 |
| --- | ---: |
| 좌석 커버리지 | 81 / 85명, 95% |
| Claude Code 세션 | 17,640회, 활성 사용자 64명 |
| Delivery 신호 | 커밋 3,634건, PR 704건 |
| Chat | 활성 사용자 75명, 메시지 9,441건, 대화 1,355건 |
| Claude Code 토큰 | 70,439,077,289 |
| 코드 라인 | 1,190,949 |
| 내부 비용 환산액 | $74.4k, 청구액 아님 |

사용 표면의 겹침도 별도로 계산했습니다.

```text
Chat only       17
Chat + Code     59
Code only        5
Neither          4
```

## Seat-fit Decision

Premium 활성 사용자의 중앙값을 한 채널에서 넘으면 상향 후보로 분류하는 방식은 Chat 중앙값이 낮아 19명(47.5%)까지 후보를 넓혔습니다.

기준을 같은 채널의 `P75 사용 강도 + P75 활성일수`를 함께 충족하는 방식으로 바꾸자 후보가 2명(5%)으로 좁혀졌습니다.

```text
Before: Chat 또는 Code 중앙값 초과 → 19명 후보
After : P75 강도 + P75 활성일수 → 2명 후보
```

이 규칙은 자동 결제가 아니라 관리자가 좌석을 검토할 때 사용하는 신호입니다. 일시적인 spike보다 지속적인 사용 패턴을 우선했습니다.

## Hard Parts

### Memory

4.63M rows를 한 번에 export할 때 ClickHouse total memory 한도 2.70 GiB를 넘었습니다. GCS export를 streaming footprint 중심으로 바꾸고 scan thread·insert block을 줄였으며 max memory를 1.5 GB로 제한했습니다.

### Timezone

cron은 Asia/Seoul인데 스크립트와 Materialized View가 UTC 기준으로 동작해 적재 날짜가 어긋났습니다. export·Mart·MV 전 경로에 KST를 명시하고 GCS 행 수, RAW 직접 집계, Mart, BigQuery partition을 같은 날짜 기준으로 다시 대조했습니다.

### Gateway boundary

외부 도메인을 개통하는 과정에서 GCP backend service 생성이 멈춘 상황을 애플리케이션 설정 문제와 분리했습니다. ClickStack 자체는 정상임을 확인하고, 내부 운영은 port-forward 경로로 우회했습니다. 외부 endpoint가 열리지 않은 상태를 “전사 배포 완료”로 포장하지 않았습니다.

## Timeline

| 시기 | 작업 |
| --- | --- |
| 2026-06-25 ~ 06-27 | Docker 기반 ClickStack과 Claude Code OTLP 연결, 신호·대시보드 형태 검증 |
| 2026-06-30 ~ 07-03 | GKE ClickStack, daily MV, GCS Parquet, BigQuery Raw/Mart, CronJob 연결 |
| 2026-07-01 | export memory footprint 안정화, UTC→KST 기준 통일, end-to-end 재검증 |
| 2026-07-19 ~ 08-05 | Chat·Claude Code 집계, 채널 overlap, seat-fit 리포트 자동화와 기준 개정 |

## Validation & Guardrails

- ClickHouse HOT 조회, GCS COLD RAW, BigQuery Mart의 날짜·행 수를 교차 확인
- API 오류 지표의 의미 변경을 ADR로 기록하고, 변경 전후 시계열 비교에 경계 표시
- 원문·PII·Secret을 공유 산출물에서 제외
- 초기 로컬 PoC와 조직 GKE 운영 레이어를 구분
- HA와 전사 강제 배포는 근거가 없어 완료로 표현하지 않음

## Results

- Claude Code·Chat·Delivery 신호를 한 분석 경로로 연결
- 40일 HOT, GCS Parquet COLD, BigQuery Mart 구조로 탐색·재집계·의사결정 분리
- 좌석 상향 후보 기준을 19명에서 2명으로 좁혀 관리자 검토 가능한 신호로 정리
- 메모리·시간대·데이터 정의 문제를 재현 가능한 운영 이슈로 기록
- 익명 집계와 internal-only 결과를 분리해 공유 범위 통제

## Trade-offs

- 내부 비용 환산액은 실제 청구액과 다르므로 비용 절감 성과로 표현하지 않았습니다.
- 원문 로그를 풍부하게 남기는 대신, 개인정보·프롬프트·도구 본문은 기본 분석 범위에서 제외했습니다.
- 단일 노드 PoC와 GKE 운영 레이어를 구분했으며 HA·전사 강제 적용을 주장하지 않았습니다.
- 실제 사용자·시트·프로젝트 식별자는 일반화했습니다.

## Tech Stack

- **Observability**: OpenTelemetry, OTel Collector, ClickHouse, ClickStack, HyperDX
- **Data Lifecycle**: Materialized View, GCS Parquet, BigQuery Raw/Mart, Looker
- **Runtime**: Docker Compose, GKE, Kubernetes CronJob
- **Analysis**: Python, JSON aggregate, seat-fit rules, KST date grain

> 익명 집계와 운영 검증 기록을 기반으로 작성했으며, 원문 데이터·개인 식별자·접근 자격 증명은 포함하지 않았습니다.
