# BigQuery Management

## Overview
BigQuery 기반 데이터 적재·운영 환경에서 권한 과다 부여, 스키마 불일치로 인한 적재 오류,
운영 중 방치된 테이블 관리 이슈를 해결하기 위해 Custom IAM Role, 타입 가이드,
운영 관리 쿼리를 정리한 프로젝트이다.

## Problem
1. 예약 쿼리(Scheduled Query) 수정
- BigQuery 기본 정책상 예약 쿼리 편집 권한은 roles/bigquery.admin 필요
- 운영자에게 Admin 권한을 주는 것은 보안·컴플라이언스 리스크
2. MySQL ↔ BigQuery 타입 차이로 인한 적재 오류 반복
- 데이터 왜곡 발생
3. 운영 중 사용되지 않는 테이블 식별 불가
- 조회되지 않는 테이블, 샤딩 테이블 증가로 스토리지 비용 및 관리 복잡도 증가

## Architecture
MySQL → BigQuery → BigQuery Scheduled Query ( Transfrom ) → Analytics/BI ( Looker Studio, Redash )

## Key Decisions
1. BigQueryAdmin 권한 대신 Custom IAM Role 설계
- 예약 쿼리 편집에 필요한 최소 권한만 추출
- Admin 권한 제거로 보안 리스크 감소
2. MySQL → BigQuery 타입 매핑 문서화
- 경험 기반 이슈를 문서로 정리하여 재발 방지
- 신규 테이블 적재 시 기준 문서로 활용
3. 운영 관리 쿼리의 코드화
- 콘솔 수동 점검 → SQL 기반 정기 점검 가능 구조

## Implementation
1. [BigQuery Custom Role 생성](iam/generate_bq_custom_role.py)
- `bigquery.jobs.create`
- `bigquery.transfers.update`
- `bigquery.transfers.get`
- `bigquery.datasets.get`
등 예약 쿼리 수정에 필요한 최소 권한만 포함

2. [MySQL → BigQuery 타입 차이 대응](schema/MySQL_to_Bigquery.md)

> MySQL `FLOAT` 타입을 BigQuery로 적재할 때 정밀도 손실을 방지하기 위해 정수부·실수부 길이를 사전에 확인하고, `DECIMAL` 타입으로 명시적 캐스팅을 수행한다.

| 구분 | 목적 | 사용 쿼리 / 처리 방식 |
|-----|-----|----------------------|
| 정수부 길이 확인 | 정수부 최대 자릿수 확인 | `SUBSTRING_INDEX(CONVERT(col, CHAR), '.', 1)` 결과의 `LENGTH` 최대값 조회 |
| 실수부 길이 확인 | 실수부 최대 자릿수 확인 | `SUBSTRING_INDEX(CONVERT(col, CHAR), '.', -1)` 결과의 `LENGTH` 최대값 조회 |
| 타입 변환 기준 | 실수부 길이에 따른 정밀도 보존 | `CASE WHEN`으로 실수부 길이를 판단하여 `DECIMAL(p, s)`로 명시적 CAST |
| 적재 타입 | BigQuery 적재 안정성 확보 | 실수부 최대 길이에 맞춘 `DECIMAL` 타입으로 조회 후 적재 |

### DECIMAL 변환 규칙 예시
- 정수부 최대 길이: **3**
- 실수부 최대 길이: **5**
- 실수부 길이에 따라 `DECIMAL(p, s)`를 동적으로 적용

| 실수부 길이 | 적용 DECIMAL 타입 |
|------------|------------------|
| 0 | DECIMAL(4, 0) |
| 1 | DECIMAL(5, 1) |
| 2 | DECIMAL(6, 2) |
| 3 | DECIMAL(7, 3) |
| 4 | DECIMAL(8, 4) |
| 5 | DECIMAL(9, 5) |


## Operations
- 최소 권한 기반 IAM 운영
- 미사용 테이블 정기 점검
- 스키마 변경 시 타입 가이드 우선 검토

## Results
Before → After
- Admin 권한 필요 → Custom Role 기반 최소 권한 운영
- 반복적인 적재 오류 → 사전 가이드로 안정성 개선
- 수동 점검 → SQL 기반 관리 자동화

## Tech Stack
BigQuery, GCP IAM, MySQL, SQL, Python

## Next Steps
- 미사용 테이블 자동 알림
- 샤딩 → 파티션 마이그레이션 가이드 추가