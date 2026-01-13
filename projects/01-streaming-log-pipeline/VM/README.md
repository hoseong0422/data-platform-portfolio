# [NBT] 데이터 파이프라인 마이그레이션

## 개요

- GCP 초기에는 서울 리전이 제공되지 않아 도쿄 리전에 데이터 파이프라인이 구축되어 있었고, 이로 인해 불필요한 리전 간 통신 비용이 발생했습니다.
- 개발 환경에는 데이터 파이프라인이 구성되지 않은 서비스도 존재하여 로그 확인이 불가능한 환경을 개선할 필요가 있었습니다.

## 데이터 파이프라인 구조

![image.png](img/image.png)

- 서버에서 생성된 로그는 Logstash를 통해 Kafka Cluster로 메시지를 전송했고, 웹/앱에서 생성된 로그는 Lumberjack을 통해 Kafka REST로 메시지를 Producing하는 파이프라인으로 구성되어 있었습니다.
- Kafka Topic으로 구분된 메시지는 ELK Stack을 활용해 로그를 조회하고, 백업 및 분석을 위해 파일로 저장한 뒤 GCS 또는 BigQuery로 적재되는 구조였습니다.

## 파이프라인 개선

### Kafka Cluster

- Kafka Cluster 브로커를 3대에서 5대로 증설했습니다.
  - Confluent Platform : 3.2.x, Kafka : 0.10.2.x  
    → Confluent Platform : 7.3.x, Kafka : 3.3.x 로 업그레이드했습니다.
  - partition 3, replication factor 2 설정으로 토픽을 운영하던 중 특정 시간대에 원인 미상의 로그 유실이 발생했습니다.
  - 브로커 증설 이후 해당 로그 유실 문제가 해소되었습니다.

### Kafka UI 도입

- Kafka Cluster 관리를 위해 Kafdrop과 Kafka UI를 비교 테스트한 후 Kafka UI를 도입했습니다.
  - Kafka UI는 UI가 직관적이었고 토픽 read-only 기능을 제공하여 UI 상에서 토픽 삭제를 방지할 수 있었습니다.
  - 이러한 이유로 Kafka UI 도입을 결정했습니다.

### Consumer Logstash

- 약 50여 대로 운영 중이던 Logstash 서버를 5대로 통합하여 재구성했습니다.
  - ES Stream 적재용 Logstash 2대
  - 파일 저장(GCS 적재 및 BigQuery 배치 적재 목적) 및 BigQuery Stream 적재용 Logstash 3대
- 서버 통합을 통해 운영 및 관리 포인트를 크게 감소시켰습니다.

### 적재 스크립트 개선

- Jenkins를 이용해 시간별 파일로 저장된 로그를 GCS로 적재하는 배치 잡에서 사용하던 스크립트를 템플릿화하여 개선했습니다.
  - 개선 전: 배치 잡 생성 시마다 개별 스크립트를 추가해야 했습니다.
  - 개선 후: 스크립트 실행 시 아규먼트를 전달받아 공통 템플릿 스크립트를 실행하도록 개선했습니다.

```bash
#!/bin/bash
set -xe

. /etc/environment

target_year=$(date +%Y --date="1hour ago")
target_month=$(date +%m --date="1hour ago")
target_day=$(date +%d --date="1hour ago")
target_date=$(date +%Y-%m-%d:%H --date="1hour ago")

file_location="$1"
log_type="$2"
gcs_bucket="$3"
gcs_log_type="$4"

file_dir="${file_location}"
file_gcs_dir="${file_dir}/to_gcs"
file_name="${log_type}-${target_date}.log"
file_path="${file_dir}/${file_name}"
echo $file_path

# 해당 시간대에 생성된 로그가 없을경우 실패얼럿이 오지 않도록 종료
if [ ! -f "${file_path}" ]; then
  echo "${file_path} is not exist."
  exit 0
fi

gcs_prefix="gs://${gcs_bucket}/${gcs_log_type}"
gcs_path="${gcs_prefix}/${target_year}/${target_month}/${target_day}"

echo "Copy to GCS ( ${gcs_path}/${file_name} )"
gzip -c $file_path > $file_gcs_dir/${file_name}.gz && gsutil -m cp $file_gcs_dir/${file_name}.gz $gcs_path/${file_name}.gz
rm $file_gcs_dir/${file_name}.gz
rm $file_path
```

### Logstash Kafka Output Compression 옵션 적용

* Kafka Cluster 디스크 사용량 절감을 위해 Logstash Kafka Output Compression 옵션을 테스트 후 적용했습니다.

  * Gzip, Snappy, Lz4, Zstd를 지원했으며 CPU 사용량이 가장 적고 압축 속도가 가장 빠른 **Lz4**를 선택했습니다.
  * 테스트 결과, Lz4 옵션 적용 시 압축하지 않은 토픽 대비 **약 24% 크기 감소**를 확인했습니다.

### ES Cluster 구조 변경

* 기존

  * 서비스별 ES Cluster를 개별적으로 구축하여 운영했습니다.
* 개선

  * 개발팀별 ES Cluster 구조로 변경했습니다.
  * ES Cluster 수를 6개에서 3개로 축소했습니다.
  * 관리 포인트를 감소시키고 개발팀의 Kibana 접근성을 개선했습니다.

## 기존 파이프라인 문제 해결

### 로그 유실 원인 파악

* Kafka Cluster를 3대에서 5대로 증설한 이후에도 특정 시간대에 로그 유실이 발생하는 현상을 확인했습니다.

#### 유실 Case 1

* 서버에서 Logrotate 수행 시 Logstash가 파일을 읽기 전에 Rotate가 발생하여,

  * 서버에는 로그 파일이 남아 있으나 Kafka로 적재되지 못하는 케이스를 확인했습니다.
* Logstash의 `stat_interval` 옵션을 조정하여 문제를 완화했습니다.
* 유실 상황 검증

  * 임의로 100개의 로그를 발생시키는 동안 Logrotate를 수행하여 유실 여부를 검증했습니다.

| stat_interval (second) | **1**   | **2**   | **3**   | **4**   | **5**   | **평균 유실** |
| ---------------------- | ------- | ------- | ------- | ------- | ------- | --------- |
| 1 (default)            | 92/100  | 93/100  | 97/100  | 88/100  | 91/100  | 7.8개      |
| 0.5                    | 99/100  | 95/100  | 100/100 | 95/100  | 96/100  | 2.8개      |
| 0.1                    | 100/100 | 100/100 | 99/100  | 100/100 | 100/100 | 0.2개      |

#### 유실 Case 2

* CopyTruncate 옵션을 사용해 Logrotate를 수행할 경우,

  * Copy 이후 Truncate 사이에 생성된 로그가 유실되어 서버에도 로그가 남지 않는 실제 유실 케이스를 확인했습니다.
* `stat_interval` 옵션 조정으로 발생 빈도를 크게 줄였으나,

  * 완전한 해결을 위해 CopyTruncate 옵션을 제거하고
  * Copy 후 신규 로그 파일 생성 → Logger에 Reopen 시그널을 전달하는 방식으로 개선이 필요하다고 판단했습니다.

## 파이프라인 마이그레이션 과정

1. 각 서버의 Logstash가 기존 데이터 파이프라인과 신규 데이터 파이프라인에 동시에 로그를 적재하도록 구성했습니다.
2. Kibana, BigQuery, GCS에 적재된 로그를 상호 비교하여 데이터 정합성을 검증했습니다.
3. 검증이 완료된 파이프라인부터 순차적으로 마이그레이션을 진행했습니다.
