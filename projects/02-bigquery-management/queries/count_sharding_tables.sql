-- 전체 테이블 찾기 (샤딩 포함)
WITH sharded AS (
  SELECT
    table_schema AS dataset_name,
    table_name,
    -- 샤딩 테이블이면 prefix 추출, 아니면 table_name 전체를 prefix로 사용
    IF(REGEXP_CONTAINS(table_name, r'.*_\d{8}$'),
       REGEXP_EXTRACT(table_name, r'^(.*)_\d{8}$'),
       table_name
    ) AS prefix,
    IF(REGEXP_CONTAINS(table_name, r'.*_\d{8}$'),
       REGEXP_EXTRACT(table_name, r'(\d{8})$'),
       NULL
    ) AS date_suffix
  FROM `project`.`region-us`.INFORMATION_SCHEMA.TABLES
)
SELECT
  dataset_name,
  prefix,
  COUNT(*) AS table_count,
  COUNT(DISTINCT date_suffix) AS sharded_days,
  MIN(date_suffix) AS min_day,
  MAX(date_suffix) AS max_day
FROM sharded
GROUP BY dataset_name, prefix
ORDER BY table_count DESC;
