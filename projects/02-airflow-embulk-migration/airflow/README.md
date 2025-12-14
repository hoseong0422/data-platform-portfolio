# Airflow KPO + Embulk 보안 구조 개선 (DB Secret 마운트)

## Overview

MySQL → BigQuery 적재를 위해 Airflow `KubernetesPodOperator(KPO)` 기반 Embulk 작업을 운영하고 있다. 초기에는 Airflow Connection / env_vars를 통해 DB 접속 정보를 전달했으나, **Pod 생성 시 환경변수로 민감정보가 그대로 노출되는 문제**가 있어 Kubernetes Secret을 **볼륨 마운트 방식으로 읽도록 구조를 개선**하였다.

## Problem

### 기존 구조의 한계

* Airflow Connection에 DB 접속 정보 저장
* KPO `env_vars`로 DB_HOST, DB_USER, DB_PASSWORD 등을 전달
* Pod 생성 시점에 `kubectl describe pod` / 이벤트 / 메타데이터에서 **환경변수 값이 그대로 노출**
* 운영/보안 관점에서 Secret 관리 기준에 부적합

## Architecture

```
[Airflow DAG]
   |
   | (KubernetesPodOperator)
   v
[K8s Pod]
   |- ConfigMap (Embulk job.yml.liquid)
   |- Secret Volume (/var/secrets/mysql)
   |- Secret Volume (/var/secrets/bq)
   |
   |- entrypoint shell
       |- cat secret files
       |- export (process-local env)
       |- embulk run
```

## Key Decisions

1. **DB 접속 정보는 env_vars에서 완전히 제거**
2. Kubernetes Secret을 `deploy_type="volume"`으로 마운트
3. Secret 파일을 **컨테이너 내부에서 읽어 프로세스 로컬 env로만 export**
4. BigQuery Service Account 역시 Secret volume으로 관리

## Implementation

### 1) Kubernetes Secret 정의

> 실제 운영 환경에서는 `stringData`가 아닌 **base64 인코딩된 `data` 필드**를 사용하여 Secret을 생성하였다.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mysql-credentials
type: Opaque
data:
  host: bXlzcWwuaW50ZXJuYWw=
  port: MzMwNg==
  user: cmVhZG9ubHk=
  password: KioqKg==
  database: YXBwX2Ri
```

* base64 인코딩 값은 예시이며, 실제 값은 노출되지 않도록 관리
* Git 저장소에는 Secret YAML을 커밋하지 않음

### 2) Airflow DAG – Secret 마운트

```python
from airflow.kubernetes.secret import Secret

MYSQL = Secret(
  deploy_type="volume",
  deploy_target="/var/secrets/mysql",
  secret="mysql-credentials"
)
```

### 3) Entrypoint Shell – Secret 파일 읽기

```bash
set -eu

export DB_HOST="$(cat /var/secrets/mysql/host)"
export DB_PORT="$(cat /var/secrets/mysql/port)"
export DB_USER="$(cat /var/secrets/mysql/user)"
export DB_PASSWORD="$(cat /var/secrets/mysql/password)"
export DB_DATABASE="$(cat /var/secrets/mysql/database)"

embulk run /app/config/job.yml.liquid
```

* `export`는 **해당 쉘 프로세스에만 적용**
* Pod ENV, Airflow UI, K8s 메타데이터에 값이 남지 않음

### 4) env_vars에는 비민감 정보만 유지

```python
env_vars={
  "DB_QUERY": "SELECT ...",
  "BQ_DATASET": "airflow_test",
  "BQ_TABLE": "table_{{ ds_nodash }}",
  "BQ_KEY_PATH": "/var/secrets/bq/key.json"
}
```

## Results

**Before → After**

* DB 접속 정보 노출 위험 → **Pod ENV 미노출 구조로 개선**
* Airflow Connection 의존 → **K8s Secret 단일 관리**
* 보안 감사 대응 어려움 → **Secret 기반 표준 패턴 정립**

## Tech Stack

* Airflow (KubernetesPodOperator)
* Kubernetes Secret / ConfigMap
* Embulk
* MySQL
* BigQuery
