-- 사용자 클릭 이벤트를 위한 스트림 생성
CREATE STREAM user_clicks (
  user_id VARCHAR KEY,
  action VARCHAR,
  event_ts BIGINT
) WITH (
  KAFKA_TOPIC = 'user_clicks',
  PARTITIONS = 1,
  VALUE_FORMAT = 'JSON',
  TIMESTAMP = 'event_ts'
);

-- 테스트 데이터 생성
-- user_1: 짧은 간격으로 연속 클릭 (첫 번째 세션)
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_1', 'click', 1672531200000); -- 2023-01-01 00:00:00
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_1', 'view', 1672531205000);  -- 00:00:05
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_1', 'scroll', 1672531210000);-- 00:00:10

-- user_2: 활동 시작 (첫 번째 세션)
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_2', 'click', 1672531220000); -- 00:00:20
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_2', 'click', 1672531225000); -- 00:00:25

-- 30초의 공백 후 user_1의 두 번째 활동 (두 번째 세션)
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_1', 'search', 1672531250000); -- 00:00:50
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_1', 'click', 1672531255000);  -- 00:00:55

-- 1분대 데이터
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_3', 'view', 1672531265000);   -- 00:01:05
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_2', 'view', 1672531270000);   -- 00:01:10 (user_2의 두 번째 세션)
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_2', 'scroll', 1672531275000); -- 00:01:15
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_3', 'click', 1672531280000);  -- 00:01:20
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_1', 'view', 1672531285000);   -- 00:01:25 (user_1의 세 번째 세션)
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_2', 'click', 1672531295000);  -- 00:01:35
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_3', 'search', 1672531300000); -- 00:01:40
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_1', 'click', 1672531310000);  -- 00:01:50
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_3', 'click', 1672531315000);  -- 00:01:55

-- 2분대 데이터
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_4', 'login', 1672531320000);  -- 00:02:00
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_2', 'logout', 1672531325000); -- 00:02:05
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_4', 'view', 1672531330000);   -- 00:02:10
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_1', 'view', 1672531340000);   -- 00:02:20 (user_1의 네 번째 세션)
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_4', 'click', 1672531345000);  -- 00:02:25
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_3', 'view', 1672531350000);   -- 00:02:30
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_1', 'click', 1672531360000);  -- 00:02:40
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_4', 'search', 1672531370000); -- 00:02:50
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_2', 'login', 1672531375000);  -- 00:02:55 (user_2의 세 번째 세션)

-- 나머지 데이터 (총 50건을 채우기 위한 추가 데이터)
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_5', 'click', 1672531202000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_5', 'view', 1672531208000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_6', 'click', 1672531222000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_5', 'scroll', 1672531268000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_6', 'view', 1672531272000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_5', 'search', 1672531288000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_6', 'click', 1672531292000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_7', 'login', 1672531323000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_7', 'view', 1672531333000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_8', 'click', 1672531348000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_7', 'click', 1672531358000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_8', 'view', 1672531368000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_9', 'click', 1672531215000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_9', 'view', 1672531230000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_10', 'click', 1672531240000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_10', 'view', 1672531245000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_9', 'scroll', 1672531290000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_10', 'search', 1672531305000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_1', 'logout', 1672531380000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_3', 'logout', 1672531385000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_5', 'logout', 1672531390000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_7', 'logout', 1672531395000);
INSERT INTO user_clicks (user_id, action, event_ts) VALUES ('user_9', 'logout', 1672531400000);


-- 30초 단위로 겹치지 않게 나누어 사용자별 이벤트 수 집계
SELECT
  user_id,
  COUNT(*) AS event_count,
  TIMESTAMPTOSTRING(WINDOWSTART, 'yyyy-MM-dd HH:mm:ss') AS window_start,
  TIMESTAMPTOSTRING(WINDOWEND, 'yyyy-MM-dd HH:mm:ss') AS window_end
FROM user_clicks
WINDOW TUMBLING (SIZE 30 SECONDS)
GROUP BY user_id
EMIT CHANGES;

-- 60초 크기의 윈도우를 30초 간격으로 이동시키며 사용자별 이벤트 수 집계
-- 최초 인입 시간의 -30초 부터 시작하여 60초 단위 집계
SELECT
  user_id,
  COUNT(*) AS event_count,
  TIMESTAMPTOSTRING(WINDOWSTART, 'yyyy-MM-dd HH:mm:ss') AS window_start,
  TIMESTAMPTOSTRING(WINDOWEND, 'yyyy-MM-dd HH:mm:ss') AS window_end
FROM user_clicks
WINDOW HOPPING (SIZE 60 SECONDS, ADVANCE BY 30 SECONDS)
GROUP BY user_id
EMIT CHANGES;

-- 20초의 비활성 기간이 발생하면 세션을 분리하여 집계
SELECT
  user_id,
  COUNT(*) AS event_count,
  TIMESTAMPTOSTRING(WINDOWEND - WINDOWSTART, 'ss') AS session_duration_ms -- 세션 지속 시간 계산
FROM user_clicks
WINDOW SESSION (20 SECONDS)
GROUP BY user_id
EMIT CHANGES;