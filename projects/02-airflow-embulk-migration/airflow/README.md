
# Airflow + Embulk Migration (KubernetesPodOperator 기반)

## Overview

Airflow `KubernetesPodOperator(KPO)` 기반으로 **MySQL → BigQuery Embulk 배치 파이프라인**을 구성하였다.  
DAG 로직과 작업 정의를 분리하고, **YAML 기반 Job 선언 + 공통 Factory 패턴**을 적용해 **확장성과 운영 안정성**을 확보했다.

## Problem

### 기존 방식의 한계

- DAG 파일마다 SQL/리소스/테이블 로직이 중복
- Job 추가 시 Python 코드 수정 필요 → 배포 비용 증가
- DB / BQ Secret 관리가 일관되지 않음
- 실패 알림 및 로그 추적이 표준화되지 않음

## Architecture

```
[daily_jobs.py (DAG)]
        |
        v
[Task(Config Loader)]
        |
        v
[daily_jobs.yml]
        |
        v
[EmbulkDagFactory]
        |
        v
[KubernetesPodOperator]
        |
        |- ConfigMap (job.yml.liquid)
        |- Secret Volume (DB, BQ)
        |- Embulk Container
```

## Key Decisions

1. YAML 기반 Job 선언
2. Factory 패턴으로 DAG 생성
3. Kubernetes Secret volume mount 사용
4. Job 단위 CPU / Memory 조절
5. 실패 시 Slack + 로그 링크 자동 전송

## Implementation

### 디렉토리 구조

```
airflow/dags/
├── daily_jobs.py
├── classes/
│   ├── task.py
│   └── embulk_k8s_task_factory.py
└── config/
    └── daily_jobs.yml
```

### [Job 정의 – config/daily_jobs.yml](./docs/embulk_job_definition.md)

```yaml
embulk_tasks:
  - source_table: users
    target_dataset: airflow_test
    mode: replace
    cpu: 1
    memory: 2
```

## Operations

- Job 추가: YAML 수정
- 리소스 조절: Job 단위 cpu/memory
- 재실행: Airflow UI
- 보안: Secret Git 미커밋

## Results

**Before → After**

- DAG 수정 필요 → YAML 수정만으로 Job 추가
- Secret ENV 노출 → Pod volume mount 제거
- 리소스 고정 → Job 단위 튜닝

## Tech Stack

- Airflow (KubernetesPodOperator)
- Kubernetes
- Embulk
- MySQL
- BigQuery

## Next Steps

- KEDA 기반 Embulk Pod Auto Scaling
- Jira MCP, GitHub MCP 연동을 통해 적재 티켓을 자동으로 읽어서 YAML 내용 추가 후 브랜치 push 구현
