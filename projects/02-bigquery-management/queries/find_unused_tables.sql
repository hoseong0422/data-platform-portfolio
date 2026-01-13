-- 미사용 테이블 찾기
-- INFORMATION_SCHEMA 테이블을 사용하면 최근 6개월 데이터만 조회 가능
SELECT
   user_email,
   job_id,
   query,
   referenced_tables.table_id,
   creation_time
FROM
   `project`.`region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT, UNNEST(referenced_tables) AS referenced_tables
WHERE
   creation_time BETWEEN '2025-03-01' AND '2025-03-31'
   AND total_bytes_billed > 0 -- 비용이 발생한 쿼리만 필터링
   AND statement_type = 'SELECT' -- 데이터 조회 쿼리만 필터링
   AND referenced_tables.table_id LIKE "table_name%"
   AND referenced_tables.dataset_id = "dataset"
LIMIT 10; -- 상위 10개 쿼리 조회


-- 6개월 이전 데이터 조회시 data_access audit log 활용
WITH base AS (
  SELECT
    protopayload_auditlog.authenticationInfo.principalEmail as principalEmail,
    protopayload_auditlog.servicedata_v1_bigquery.jobCompletedEvent AS jobCompletedEvent,  -- (query_job_completed, load_job_completed, table_copy_job_completed, extract_job_completed)
    protopayload_auditlog.servicedata_v1_bigquery.jobCompletedEvent.job.jobStatistics.createTime AS create_time,
    protopayload_auditlog.servicedata_v1_bigquery.jobCompletedEvent.job.jobConfiguration.query.query AS query
  FROM `project.dataset.cloudaudit_googleapis_com_data_access_*`
  WHERE
    _TABLE_SUFFIX BETWEEN "20250301" AND "20250901"
)

SELECT
  principalEmail,
  refereced_tables.projectId AS project_id,
  refereced_tables.datasetId AS dataset_id,
  refereced_tables.tableId AS table_id,
  create_time,
  query
FROM
  base, UNNEST(jobCompletedEvent.job.jobStatistics.referencedTables) AS refereced_tables
WHERE
  jobCompletedEvent.eventName IS NOT NULL -- "query_job_completed"
  AND refereced_tables.datasetId = "dataset"
  AND refereced_tables.tableId LIKE "table_name%"
ORDER BY create_time ASC;
