# ksqlDB & Kafka Connect 기반 실시간 이상 탐지 PoC

## Overview

GKE 환경에 Kafka Connect와 ksqlDB를 배포하여, 기존 분 단위 알림 한계를 극복하고 **초 단위 실시간 이상 탐지**가 가능한 스트리밍 기반 알림 파이프라인의 PoC를 수행하였다.

기존 Kibana OpenDistro Alert는 최소 알림 주기가 1분으로 제한되어 있어 짧은 시간 내 발생하는 이상 징후(spike, burst) 탐지에 한계가 있었으며, 이를 스트림 처리 기반으로 개선할 수 있는지 기술 검증을 목표로 하였다.

---

## Problem

### 기존 한계

* Kibana Alert의 최소 알림 주기 1분 제한
* 짧은 spike / burst 트래픽 탐지 불가
* 로그 기반 후처리 방식 → 실시간성 부족

### 요구사항

* 초 단위(Window 기반) 이상 탐지
* 실시간 스트림 처리
* 알림 시스템과의 유연한 연계

---

## Architecture

```text
[Mock Producer]
      |
      v
  Kafka Topic
      |
      v
  ksqlDB
  - WINDOW aggregation
  - Threshold detection
      |
      v
 Kafka Topic (alert)
      |
      v
 Kafka Connect
  - Sink Connector
      |
      v
 Alert Endpoint / Webhook
```

---

## Key Decisions

1. ksqlDB 기반 Stream Processing

   * 배치/후처리 제거
   * SQL 기반으로 PoC 생산성 확보

2. Kafka Connect 분리 배포

   * 알림 시스템 연계 책임 분리
   * Sink 확장성 확보

3. 공식 Helm Chart 미사용

   * Kafka Connect / ksqlDB Helm Chart 노후화
   * PoC 목적에 맞는 최소 구성 직접 작성

4. NetworkPolicy 포함

   * 단순 실험이 아닌 운영 가능성 검증
   * 보안 고려한 설계

---

## Implementation

### 디렉터리 구조

```text
├── README.md
├── helm/
│   ├── kafka-connect/
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   │       ├── deployment.yaml
│   │       ├── service.yaml
│   │       ├── ingress.yaml
│   │       ├── hpa.yaml
│   │       ├── networkpolicy.yaml
│   │       └── serviceaccount.yaml
│   └── ksqldb/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
│           ├── deployment.yaml
│           ├── service.yaml
│           ├── ingress.yaml
│           ├── hpa.yaml
│           ├── networkpolicy.yaml
│           └── serviceaccount.yaml
└── test/
    ├── MOCK_DATA.sql
    ├── WINDOW_TEST.sql
    └── alert_connector.sh
```

---

### Kafka Connect Helm Chart

* Deployment

  * REST API 기반 Connector 관리
  * 환경 변수 기반 설정 주입
* HPA

  * CPU 기준 autoscaling
* NetworkPolicy

  * 불필요한 Pod 간 통신 차단
* Ingress

  * 내부 테스트용 REST 접근

---

### ksqlDB Stream Processing

ksqlDB는 Kafka Topic에 유입되는 이벤트를 실시간으로 처리하여 Window 기반 이상 탐지 로직을 수행하는 핵심 컴포넌트로 사용되었다.

* 배치 처리 없이 스트림 기반 연산
* SQL 기반 정의 → 빠른 PoC 반복 가능
* Alert 기준 로직의 가시성 확보

---

### 테스트 스크립트

#### MOCK_DATA.sql

* 테스트용 Kafka Topic 데이터 생성
* 의도적으로 spike 패턴 포함

#### WINDOW_TEST.sql

```sql
CREATE TABLE anomaly_window AS
SELECT
  COUNT(*) AS event_count
FROM input_stream
WINDOW TUMBLING (SIZE 5 SECONDS)
HAVING COUNT(*) > threshold;
```

* 5초 단위 Tumbling Window
* 임계치 초과 시 Alert Topic으로 결과 전송

#### alert_connector.sh

* Kafka Connect REST API 사용
* Alert Sink Connector 등록 자동화

---

## Operations

* 배포

```bash
helm install kafka-connect ./helm/kafka-connect
helm install ksqldb ./helm/ksqldb
```

* 스케일링

  * HPA 자동 조정
  * spike 트래픽 시 Pod 수 증가 확인

* 롤백

```bash
helm rollback kafka-connect
helm rollback ksqldb
```

---

## Troubleshooting

| 이슈              | 원인             | 해결                  |
| --------------- | -------------- | ------------------- |
| Connector 등록 실패 | REST 접근 차단     | NetworkPolicy 수정    |
| Alert 중복 발생     | Window overlap | Tumbling window로 변경 |
| 과도한 scale-out   | CPU 기준 한계      | threshold 조정        |

---

## Results

Before → After

* 알림 지연: 최대 60초 → 평균 5초 이내
* 이상 탐지 해상도: 분 단위 → 초 단위
* 실시간 탐지 가능 여부: 불가 → 가능
* Alert 파이프라인 확장성: 제한적 → Sink 기반 확장 가능

*수치는 PoC 환경 기준이며 실제 운영 환경에서는 트래픽 규모에 따라 조정 필요*

---

## Tech Stack

* Streaming: Apache Kafka, ksqlDB
* Integration: Kafka Connect
* Infrastructure: GKE, Helm
* Alert: Webhook 기반 Sink

---

## Next Steps

* ksqlDB Helm Chart 정식화
* KEDA 기반 lag/metric autoscaling 검증
* Slack Incoming Webhook을 호출하는 Kafka Connect Sink Connector 직접 작성 및 배포
- connector.class 커스텀 구현 + Docker 이미지로 Connect에 플러그인 주입
- Alert Topic 이벤트를 Slack 메시지 포맷(Block Kit/Markdown)으로 변환
