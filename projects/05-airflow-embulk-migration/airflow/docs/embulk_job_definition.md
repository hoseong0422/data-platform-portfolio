
# Embulk Job 정의 가이드 (`daily_jobs.yml`)

이 문서는 `config/daily_jobs.yml`에서 정의하는 **Embulk Job 옵션 전체 목록과 동작 방식**을 설명한다.  
DAG / Python 코드 수정 없이 Job을 확장하기 위한 **선언적 설정 가이드**이다.

---

## 기본 구조

```yaml
embulk_tasks:
  - source_table: users
    target_dataset: airflow_test
    mode: replace
    cpu: 1
    memory: 2
```

각 항목은 하나의 Embulk 실행 단위(Job)를 의미한다.

---

## 필수 옵션

| 옵션 | 타입 | 설명 |
|---|---|---|
| `source_table` | string | 원본 DB 테이블명 |

---

## 테이블 / 적재 옵션

| 옵션 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `target_dataset` | string | `airflow_test` | BigQuery Dataset |
| `target_table` | string | `null` | BigQuery 테이블명 직접 지정 |
| `single_table` | boolean | `false` | 날짜 suffix 없는 단일 테이블 적재 |
| `mode` | string | `replace` | `replace` / `append` |

### 테이블명 결정 규칙

1. `target_table` 지정 시 해당 값 사용  
2. `single_table: true` → `{source_table}`  
3. 기본 → `{source_table}_{{ ds_nodash }}`

---

## 쿼리 옵션

| 옵션 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `query` | string | `null` | SQL 직접 지정 |
| `full_scan` | boolean | `false` | 전체 테이블 스캔 |

### SQL 생성 로직

- `query`가 있으면 그대로 사용
- `query` 없음 + `full_scan: false`

```sql
SELECT *
FROM {source_table}
WHERE created_at >= '{{ data_interval_start | ds }} 00:00:00'
  AND created_at <  '{{ data_interval_end   | ds }} 00:00:00'
```

- `full_scan: true`

```sql
SELECT * FROM {source_table}
```

---

## 리소스 옵션 (Kubernetes)

| 옵션 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `cpu` | float | `1.0` | Pod CPU limit |
| `memory` | float | `1.0` | Pod Memory limit (Gi) |

```yaml
cpu: 2
memory: 4
```

---

## BigQuery 파티셔닝

| 옵션 | 타입 | 설명 |
|---|---|---|
| `partitioning` | object | 파티션 테이블 설정 |

```yaml
partitioning:
  partitioning_type: DAY
  partitioning_field: created_at
```

- 파티셔닝 설정 시 `partitioning_job.yml.liquid` 사용

---

## 전체 예시

```yaml
embulk_tasks:
  - source_table: orders
    target_dataset: analytics
    mode: append
    cpu: 2
    memory: 4
    single_table: true
    partitioning:
      partitioning_type: DAY
      partitioning_field: created_at

  - source_table: users
    full_scan: true
    target_table: users_snapshot
```

---

## 설계 의도

- Job 추가 시 DAG 코드 수정 불필요
- YAML 변경만으로 확장 가능
- 테이블별 리소스 튜닝 지원
- 표준 쿼리 + 커스텀 SQL 공존
