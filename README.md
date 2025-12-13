# data-platform-portfolio

이 레포지토리는 **데이터 파이프라인·플랫폼 엔지니어링 경험을 실제 구현 사례 중심으로 정리한 포트폴리오**입니다.
단순 기술 나열이 아닌, *문제 정의 → 구조 설계 → 실행 → 정량적 성과*의 흐름으로 구성되어 있으며,
운영 환경에서의 **안정성·확장성·비용 효율·컴플라이언스 개선 경험**을 재현 가능한 형태로 담았습니다.

---

## 🎯 포트폴리오 목표

* 대규모 로그·데이터 파이프라인을 **클라우드·Kubernetes 환경에서 설계·운영한 경험을 구조적으로 정리**
* 장애 대응, 성능 개선, 비용 절감 등 **비즈니스 임팩트가 있는 기술적 의사결정**을 명확히 전달
* 실제 업무에서 사용한 기술을 **재현 가능한 코드·설정·문서**로 정리

---

## 🧭 전체 구성 개요

본 레포는 **프로젝트(Project) 중심 구조**로 구성되어 있으며, 각 프로젝트는 독립적으로 이해할 수 있도록 README와 예제 설정을 포함합니다.

```
data-platform-portfolio/
├─ projects/        # 실제 구현 프로젝트 모음
└─ tools/           # 스크립트 및 보조 도구
```

---

## 📌 주요 프로젝트 목록

### 1️⃣ [Streaming Log Pipeline](/projects/01-streaming-log-pipeline/README.md)

**GKE → Pub/Sub → Vector → Kafka → Elasticsearch** 기반 스트리밍 로그 파이프라인

* 로그 유실 99% 이상 감소 (일간 1,000건 → 3건 이내)
* Consumer 서버 수 52대 → 5대 축소
* Inter-Region 네트워크 비용 약 80% 이상 절감

### 2️⃣ [Airflow + Embulk ETL Migration](/projects/02-airflow-embulk-migration/README.md)

Jenkins 기반 배치 작업을 **Airflow(KubernetesPodOperator)**로 마이그레이션

* 배치 파이프라인 표준화
* 운영 안정성 및 확장성 개선

### 3️⃣ [GitOps 기반 배포 자동화](/projects/03-gitops-helm-argocd/README.md)

**Helm + ArgoCD(Single / Multi-source)** 구조 설계 및 검증

* Vector ConfigMap 기반 배포 구조 개선
* 불필요한 이미지 재빌드 제거 (빌드 시간 약 30초 절감)
* 팀 단위 테스트·검증 리소스 절감

### 4️⃣ [Redash 오픈소스 커스터마이징](/projects/04-security-redash-export-control/README.md)

Redash Backend·Frontend 코드 수정

* 개인정보 테이블 Export 차단 기능 구현
* 보안·컴플라이언스 요구사항을 코드 레벨에서 해결

---

## 📊 정량적 성과 요약

| 구분                | Before       | After            | 성과               |
| ----------------- | ------------ | ---------------- | ---------------- |
| 로그 유실             | 일 1,000건 이상  | 일 3건 이내          | 99% 이상 감소        |
| Logstash Consumer | 52대          | 5대               | 컴퓨팅 리소스 약 60% 절감 |
| 네트워크 비용           | Cross-Region | Same Region      | 약 80% 이상 절감      |
| 자산 수집 공수          | 16시간         | 2시간              | 약 85% 절감         |
| BigQuery 비용       | 온디맨드 단가 인상   | Storage Model 전환 | 약 25% 비용 인상 방어   |

---

## 🛠️ 사용 기술 스택

* **Cloud**: GCP(GKE, Pub/Sub, BigQuery, GCS, Cloud Build), AWS
* **Streaming / Log**: Kafka, Vector, Fluent-Bit, Logstash, Elasticsearch, Kibana
* **Data / ETL**: Airflow, Embulk, BigQuery
* **Kubernetes / DevOps**: Helm, ArgoCD, KEDA, GitOps
* **Language**: Python, SQL, Shell

---

## ✨ 이 포트폴리오를 통해 전달하고 싶은 점

* 문제를 단순히 해결하는 것이 아니라 **재발하지 않도록 구조를 개선**합니다.
* 기술 도입의 목적을 항상 **운영 안정성·비용·조직 생산성** 관점에서 판단합니다.
* 성공과 실패를 모두 경험으로 축적하며, **다음 선택의 품질을 높이는 엔지니어링**을 지향합니다.

---

> 본 레포지토리는 실제 업무 경험을 기반으로 작성되었으며,
> 민감한 정보는 제거하거나 샘플 형태로 대체하였습니다.
