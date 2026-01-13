# BigQuery Management

## Overview

BigQuery 기반 데이터 적재·운영 환경에서 발생하던 권한 과다 부여 문제,  
스키마 불일치로 인한 적재 오류,  
운영 중 방치된 테이블 관리 이슈를 해결하기 위해  
Custom IAM Role 설계, 타입 가이드 문서화, 운영 관리 쿼리를 정리한 프로젝트입니다.

## Problem

1. 예약 쿼리(Scheduled Query) 수정 권한 문제
   - BigQuery 기본 정책상 예약 쿼리 편집에는 `roles/bigquery.admin` 권한이 필요했습니다.
   - 운영자에게 Admin 권한을 부여하는 것은 보안 및 컴플라이언스 측면에서 리스크가 있었습니다.

2. MySQL ↔ BigQuery 타입 차이로 인한 적재 오류 반복
   - 타입 불일치로 인해 데이터 왜곡 및 적재 실패가 반복적으로 발생했습니다.

3. 운영 중 사용되지 않는 테이블 식별의 어려움
   - 조회되지 않는 테이블 및 샤딩 테이블이 증가하면서 스토리지 비용과 관리 복잡도가 증가했습니다.

## Architecture

MySQL → BigQuery → BigQuery Scheduled Query (Transform) → Analytics / BI  
(Looker Studio, Redash)

## Key Decisions

1. BigQuery Admin 권한 대신 Custom IAM Role 설계
   - 예약 쿼리 편집에 필요한 최소 권한만 추출하여 Custom Role로 구성했습니다.
   - Admin 권한 제거를 통해 보안 리스크를 감소시켰습니다.

2. MySQL → BigQuery 타입 매핑 문서화
   - 경험 기반으로 발생했던 타입 이슈를 문서화하여 재발을 방지했습니다.
   - 신규 테이블 적재 시 기준 문서로 활용할 수 있도록 정리했습니다.

3. 운영 관리 쿼리의 코드화
   - 콘솔 기반 수동 점검 방식을 제거하고 SQL 기반 정기 점검이 가능하도록 구성했습니다.

## Implementation

### 1. BigQuery Custom Role 생성  
[`iam/generate_bq_custom_role.py`](iam/generate_bq_custom_role.py)

- 예약 쿼리 수정에 필요한 최소 권한만 포함했습니다.
  - `bigquery.jobs.create`
  - `bigquery.transfers.update`
  - `bigquery.transfers.get`
  - `bigquery.datasets.get`

### 2. MySQL → BigQuery 타입 차이 대응  
[`schema/MySQL_to_Bigquery.md`](schema/MySQL_to_Bigquery.md)

> MySQL `FLOAT` 타입을 BigQuery로 적재할 때 정밀도 손실을 방지하기 위해  
> 정수부 및 실수부 길이를 사전에 확인하고,  
> `DECIMAL` 타입으로 명시적 캐스팅을 수행하도록 가이드를 정리했습니다.

| 구분 | 목적 | 사용 쿼리 / 처리 방식 |
|-----|-----|----------------------|
| 정수부 길이 확인 | 정수부 최대 자릿수 확인 | `SUBSTRING_INDEX(CONVERT(col, CHAR), '.', 1)` 결과의 `LENGTH` 최대값 조회 |
| 실수부 길이 확인 | 실수부 최대 자릿수 확인 | `SUBSTRING_INDEX(CONVERT(col, CHAR), '.', -1)` 결과의 `LENGTH` 최대값 조회 |
| 타입 변환 기준 | 실수부 길이에 따른 정밀도 보존 | `CASE WHEN`으로 실수부 길이를 판단하여 `DECIMAL(p, s)`로 명시적 CAST |
| 적재 타입 | BigQuery 적재 안정성 확보 | 실수부 최대 길이에 맞춘 `DECIMAL` 타입으로 조회 후 적재 |

#### DECIMAL 변환 규칙 예시

- 정수부 최대 길이: **3**
- 실수부 최대 길이: **5**
- 실수부 길이에 따라 `DECIMAL(p, s)`를 동적으로 적용했습니다.

| 실수부 길이 | 적용 DECIMAL 타입 |
|------------|------------------|
| 0 | DECIMAL(4, 0) |
| 1 | DECIMAL(5, 1) |
| 2 | DECIMAL(6, 2) |
| 3 | DECIMAL(7, 3) |
| 4 | DECIMAL(8, 4) |
| 5 | DECIMAL(9, 5) |

## Operations

- 최소 권한 기반 IAM 정책으로 운영했습니다.
- 미사용 테이블을 정기적으로 점검했습니다.
- 스키마 변경 시 타입 가이드를 우선 검토하는 운영 규칙을 적용했습니다.

## Results

**Before → After**

- Admin 권한 필요 → Custom Role 기반 최소 권한 운영으로 개선했습니다.
- 반복적인 적재 오류 → 사전 타입 가이드를 통해 적재 안정성을 확보했습니다.
- 콘솔 기반 수동 점검 → SQL 기반 운영 관리 자동화로 전환했습니다.

## Tech Stack

- **Data Warehouse**: BigQuery  
- **IAM**: GCP IAM  
- **Source DB**: MySQL  
- **Language / Query**: SQL, Python  

## Next Steps

- 미사용 테이블 자동 알림 기능 추가
- 샤딩 테이블 → 파티션 테이블 마이그레이션 가이드 확장
