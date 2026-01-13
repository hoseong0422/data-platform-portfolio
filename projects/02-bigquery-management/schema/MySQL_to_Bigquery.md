# MySQL -> BigQuery 적재하기
## Float 타입 적재하기
### 정수부, 실수부 길이 확인
```SQL
# 정수부 길이 확인
SELECT MAX(LENGTH(
SUBSTRING_INDEX((CONVERT(target_column, CHAR)), '.', 1)))
FROM target_table
LIMIT 1;

# 실수부 길이 확인
SELECT MAX(LENGTH(
SUBSTRING_INDEX((CONVERT(target_column, CHAR)), '.', -1)))
FROM target_table
LIMIT 1;
```

### 적재 쿼리 예시
- 정수부 최대길이 3, 실수부 최대길이 5인 경우
- CASE WHEN 표현식을 사용하여 실수부 길이에 따라 실수부의 길이를 명시적으로 제한하는 DECIMAL TYPE으로 조회
```SQL
SELECT 
    column_1
    column_2,
    (CASE
        WHEN LENGTH(SUBSTRING_INDEX((CONVERT(target_float_column, CHAR)), '.', -1)) = 0
        THEN CAST(target_float_column AS DECIMAL(4, 0))
        WHEN LENGTH(SUBSTRING_INDEX((CONVERT(target_float_column, CHAR)), '.', -1)) = 1
        THEN CAST(target_float_column AS DECIMAL(5, 1))
        WHEN LENGTH(SUBSTRING_INDEX((CONVERT(target_float_column, CHAR)), '.', -1)) = 2
        THEN CAST(target_float_column AS DECIMAL(6, 2))
        WHEN LENGTH(SUBSTRING_INDEX((CONVERT(target_float_column, CHAR)), '.', -1)) = 3
        THEN CAST(target_float_column AS DECIMAL(7, 3))
        WHEN LENGTH(SUBSTRING_INDEX((CONVERT(target_float_column, CHAR)), '.', -1)) = 4
        THEN CAST(target_float_column AS DECIMAL(8, 4))
        WHEN LENGTH(SUBSTRING_INDEX((CONVERT(target_float_column, CHAR)), '.', -1)) = 5
        THEN CAST(target_float_column AS DECIMAL(9, 5))
        ELSE target_float_column
    END) AS target_float_column
FROM target_table
```
