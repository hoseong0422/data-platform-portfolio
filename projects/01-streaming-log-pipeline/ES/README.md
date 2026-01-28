# Elasticsearch 인덱스 생명주기(ILM) 최적화

## Overview

Elasticsearch 클러스터의 데이터 노드 증설 없이, **Index Lifecycle Management(ILM) 정책 재설계와 Warm Phase 도입**을 통해 리소스 사용량을 대폭 절감하고 클러스터 안정성을 확보한 프로젝트입니다.

데이터 노드의 Heap 메모리 부족 및 디스크 사용률 급증 문제를 해결하기 위해, 검색 빈도가 낮은 과거 데이터에 대해 Segment Merge와 압축을 수행하는 정책을 적용했습니다. 그 결과, JVM 안정성이 개선되고 디스크 공간을 효율적으로 확보하여 구조적인 비용 절감 효과를 거두었습니다.

## Problem

### 기존 상황 및 한계

- **인덱스 관리 부재**: 별도의 롤링 설정이나 Warm Phase 없이, 생성 후 일정 기간이 지나면 바로 삭제되는 단순한 정책만 존재했습니다.
- **메모리(Heap) 압박**: 파편화된 다수의 Segment가 Heap 메모리를 상시 점검하고 있어, JVM 가비지 컬렉션(GC) 부하 및 클러스터 불안정성이 초래되었습니다.
- **디스크 부족**: 데이터 증가 속도에 비해 디스크 확보 속도가 늦어, 수시로 디스크 얼럿이 발생하고 데이터 노드 증설이 검토되는 상황이었습니다.
- **비용 최적화 필요**: 단순 노드 증설은 인프라 비용의 지속적인 증가를 의미하므로, 소프트웨어적인 최적화가 시급했습니다.

## Strategy & Key Actions

### 1. ILM 정책 재설계 및 Warm Phase 도입

- **정책 수립**: 생성 후 3일이 지난 인덱스를 대상으로 **Warm Phase** 진입을 설정했습니다.
- **Segment Merge (Force Merge)**: Warm Phase 진입 시 Segment 개수를 1개로 병합하여 Heap 메모리 점유율을 최소화했습니다.
- **데이터 압축 (Compression)**: 검색 빈도가 낮은 Warm Phase 인덱스에 대해 압축 옵션을 활성화하여 디스크 사용량을 절감했습니다.

### 2. 마스터 노드 부하 분산 적용 (Phase-in)

- **문제 인식**: 60일 분량의 대규모 인덱스에 한 번에 정책을 적용할 경우, 대량의 Segment Merge 작업으로 인해 마스터 노드 및 클러스터 전체에 과도한 부하가 가해질 위험이 있었습니다.
- **단계적 적용**: 50일 → 40일 → 30일 → 20일 → 10일 → 3일 순으로 대상을 좁혀가며 **점진적으로 정책을 적용**했습니다.
- **모니터링**: 각 단계마다 마스터 노드의 CPU 사용량과 Task Queue 상태를 모니터링하며 작업 속도를 조절했습니다.

## Architecture & Implementation

### ILM Policy 구조

```json
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {}
      },
      "warm": {
        "min_age": "3d",
        "actions": {
          "forcemerge": {
            "max_num_segments": 1,
            "index_codec" : "best_compression"
          }
        }
      },
      "delete": {
        "min_age": "60d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

*참고: 실제 환경에 따라 샤드 수 최적화(Shrink)와 노드 할당 정책을 병행하여 적용했습니다.*

## Results

### Before → After

| 항목 | Before | After | 기대 효과 |
| :--- | :--- | :--- | :--- |
| **인덱스 관리** | Hot - Delete (단순) | Hot - Warm - Delete | 데이터 생명주기에 따른 리소스 차등 배분 |
| **Heap 메모리** | 노드별 사용률 임계점 육박 | 가용 Heap 공간 확보 및 GC 안정화 | Segment 수 감소로 인한 오버헤드 제거 |
| **디스크 사용량** | 지속적 증가 및 얼럿 빈발 | 약 20~30% 이상 공간 절감 | 데이터 압축 및 병합을 통한 저장 효율 증대 |
| **인프라 비용** | 노드 증설 필요 (비용 증가) | **노드 증설 없이 해결** | 운영 비용 절감 |

### 정성적 성과

- **클러스터 안정성**: 메모리 부족으로 인한 노드 다운 현상을 근본적으로 해결했습니다.
- **검색 성능 최적화**: 다수의 Segment를 하나로 병합함으로써, 과거 데이터에 대한 검색 효율이 개선되었습니다.
- **운영 프로세스 확보**: 대규모 클러스터에 부하를 주지 않고 운영 정책을 안전하게 업데이트하는 노하우(단계적 적용 전략)를 확보했습니다.

## Technical Skills

- **Storage**: Elasticsearch (ILM, Force Merge, Segment Management)
- **Monitoring**: Kibana, Prometheus/Grafana (Node Metrics, Task Queue)
- **Strategy**: Phase-in Deployment, Infrastructure Cost Optimization
