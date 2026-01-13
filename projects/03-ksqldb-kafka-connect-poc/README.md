# ksqlDB & Kafka Connect 기반 실시간 이상 탐지 PoC

## Overview

GKE 환경에 Kafka Connect와 ksqlDB를 배포하여, 기존 분 단위 알림 한계를 극복하고  
**초 단위 실시간 이상 탐지**가 가능한 스트리밍 기반 알림 파이프라인에 대한 PoC를 수행했습니다.

기존 Kibana OpenDistro Alert는 최소 알림 주기가 1분으로 제한되어 있어  
짧은 시간 내 발생하는 이상 징후(spike, burst) 탐지에 한계가 있었으며,  
이를 스트림 처리 기반으로 개선할 수 있는지에 대한 기술 검증을 목표로 했습니다.

---

## Problem

### 기존 한계

- Kibana Alert의 최소 알림 주기 1분 제한
- 짧은 spike / burst 트래픽 탐지 불가
- 로그 기반 후처리 방식으로 인한 실시간성 부족

### 요구사항

- 초 단위(Window 기반) 이상 탐지
- 실시간 스트림 처리
- 알림 시스템과의 유연한 연계

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
````

---

## Key Decisions

1. **ksqlDB 기반 Stream Processing**

   * 배치 및 후처리 단계를 제거했습니다.
   * SQL 기반 정의를 통해 PoC 생산성을 확보했습니다.

2. **Kafka Connect 분리 배포**

   * 알림 시스템 연계 책임을 Stream Processing과 분리했습니다.
   * Sink 확장성을 고려한 구조로 설계했습니다.

3. **공식 Helm Chart 미사용**

   * Kafka Connect 및 ksqlDB 공식 Helm Chart가 노후화되어 있음을 확인했습니다.
   * PoC 목적에 맞는 최소 구성의 Helm Chart를 직접 작성하여 사용했습니다.

4. **NetworkPolicy 포함**

   * 단순 실험이 아닌 운영 가능성 검증을 목표로 했습니다.
   * 보안을 고려한 네트워크 접근 제어를 포함했습니다.

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

* **Deployment**

  * REST API 기반 Connector 관리를 지원하도록 구성했습니다.
  * 환경 변수 기반으로 설정을 주입했습니다.
* **HPA**

  * CPU 사용량 기준 autoscaling을 적용했습니다.
* **NetworkPolicy**

  * 불필요한 Pod 간 통신을 차단했습니다.
* **Ingress**

  * 내부 테스트를 위한 REST 접근을 허용했습니다.

---

### ksqlDB Stream Processing

ksqlDB는 Kafka Topic으로 유입되는 이벤트를 실시간으로 처리하여
Window 기반 이상 탐지 로직을 수행하는 핵심 컴포넌트로 사용했습니다.

* 배치 처리 없이 스트림 기반 연산을 수행했습니다.
* SQL 기반 정의를 통해 빠른 PoC 반복이 가능했습니다.
* Alert 기준 로직을 명확하게 가시화할 수 있었습니다.

---

### 테스트 스크립트

#### MOCK_DATA.sql

* 테스트용 Kafka Topic 데이터를 생성했습니다.
* 의도적으로 spike 패턴을 포함시켜 이상 탐지 동작을 검증했습니다.

#### WINDOW_TEST.sql

```sql
CREATE TABLE anomaly_window AS
SELECT
  COUNT(*) AS event_count
FROM input_stream
WINDOW TUMBLING (SIZE 5 SECONDS)
HAVING COUNT(*) > threshold;
```

* 5초 단위 Tumbling Window를 적용했습니다.
* 임계치 초과 시 Alert Topic으로 결과를 전송하도록 구성했습니다.

#### alert_connector.sh

* Kafka Connect REST API를 사용했습니다.
* Alert Sink Connector 등록 과정을 자동화했습니다.

---

## Operations

### 배포

```bash
helm install kafka-connect ./helm/kafka-connect
helm install ksqldb ./helm/ksqldb
```

### 스케일링

* HPA를 통해 자동 스케일링이 이루어지도록 구성했습니다.
* spike 트래픽 발생 시 Pod 수가 증가하는 것을 확인했습니다.

### 롤백

```bash
helm rollback kafka-connect
helm rollback ksqldb
```

---

## Troubleshooting

| 이슈              | 원인             | 해결                  |
| --------------- | -------------- | ------------------- |
| Connector 등록 실패 | REST 접근 차단     | NetworkPolicy 수정    |
| Alert 중복 발생     | Window overlap | Tumbling Window로 변경 |

---

## Results

**Before → After**

* 알림 지연: 최대 60초 → 평균 **5초 이내**
* 이상 탐지 해상도: 분 단위 → **초 단위**
* 실시간 탐지 가능 여부: 불가 → **가능**
* Alert 파이프라인 확장성: 제한적 → **Sink 기반 확장 가능**

*본 수치는 PoC 환경 기준이며, 실제 운영 환경에서는 트래픽 규모에 따라 조정이 필요합니다.*

---

## Tech Stack

* **Streaming**: Apache Kafka, ksqlDB
* **Integration**: Kafka Connect
* **Infrastructure**: GKE, Helm
* **Alert**: Webhook 기반 Sink

---

## Next Steps

* ksqlDB Helm Chart 정식화
* KEDA 기반 lag 및 metric autoscaling 검증
* Slack Incoming Webhook을 호출하는 Kafka Connect Sink Connector 직접 작성 및 배포

  * `connector.class` 커스텀 구현 및 Docker 이미지로 Connect 플러그인 주입
  * Alert Topic 이벤트를 Slack 메시지 포맷(Block Kit / Markdown)으로 변환
