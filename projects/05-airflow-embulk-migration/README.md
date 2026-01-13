# Airflow + Embulk Migration (KubernetesPodOperator 기반)

## Overview

Airflow `KubernetesPodOperator(KPO)` 기반으로 **MySQL → BigQuery Embulk 배치 파이프라인**을 구성했습니다.  
DAG 로직과 작업 정의를 분리하고, **YAML 기반 Job 선언 + 공통 Factory 패턴**을 적용하여 **확장성과 운영 안정성**을 확보했습니다.

## Problem

### 기존 방식의 한계

- DAG 파일마다 SQL/리소스/테이블 로직이 중복되어 있었습니다.
- Job 추가 시 Python 코드 수정이 필요하여 배포 비용이 증가했습니다.
- DB/BQ Secret 관리 방식이 일관되지 않았습니다.
- 실패 알림 및 로그 추적 방식이 표준화되지 않았습니다.

## Architecture

```text
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
````

## Key Decisions

1. YAML 기반 Job 선언을 적용했습니다.
2. Factory 패턴으로 DAG를 생성하도록 구성했습니다.
3. Kubernetes Secret volume mount 방식을 사용했습니다.
4. Job 단위로 CPU/Memory를 조절할 수 있도록 구성했습니다.
5. 실패 시 Slack 알림과 로그 링크를 자동 전송하도록 구성했습니다.

## Implementation

### 디렉토리 구조

```text
airflow/dags/
├── daily_jobs.py
├── classes/
│   ├── task.py
│   └── embulk_k8s_task_factory.py
└── config/
    └── daily_jobs.yml
```

### [Job 정의 – config/daily_jobs.yml](./airflow/docs/embulk_job_definition.md)

```yaml
embulk_tasks:
  - source_table: users
    target_dataset: airflow_test
    mode: replace
    cpu: 1
    memory: 2
```

## Operations

* Job 추가는 YAML 수정으로 수행했습니다.
* 리소스 조절은 Job 단위 cpu/memory 값 조정으로 수행했습니다.
* 재실행은 Airflow UI에서 수행했습니다.
* 보안 측면에서 Secret은 Git에 커밋하지 않도록 운영했습니다.

## Results

**Before → After**

* DAG 수정 필요 → YAML 수정만으로 Job 추가가 가능해졌습니다.
* Secret ENV 노출 → Pod volume mount 방식으로 전환하여 노출을 제거했습니다.
* 리소스 고정 → Job 단위 튜닝이 가능해졌습니다.

## Tech Stack

* Airflow (KubernetesPodOperator)
* Kubernetes
* Embulk
* MySQL
* BigQuery

## Next Steps

* KEDA 기반 Embulk Pod Auto Scaling을 검토할 예정입니다.
* Jira MCP, GitHub MCP 연동을 통해 적재 티켓을 자동으로 읽고 YAML 내용을 추가한 뒤 브랜치를 push하는 자동화를 구현할 예정입니다.
