# Discovery MCP · 대화형 데이터 카탈로그

## Overview

BigQuery를 Data Lake·Warehouse·Mart로 활용하면서, 데이터가 어디에서 와서 어떤 적재·변환 단계를 거치는지 확인하기 어려운 문제가 있었습니다. Discovery MCP는 원천 DB·Log, BigQuery 예약 쿼리, BI 소비 지점을 하나의 `asset_id`와 Lineage로 연결하고, Claude의 대화와 Prefab UI에서 탐색할 수 있게 만든 데이터 카탈로그입니다.

Google Sheets MCP와 BigQuery MCP가 각각 문서 편집과 승인 데이터 조회를 담당한다면, Discovery MCP는 “이 데이터는 어디에서 왔고 누가 쓰는가?”를 찾는 탐색 과제입니다.

## Problem

데이터를 찾는 일은 테이블 이름을 검색하는 것만으로 끝나지 않았습니다.

- 원천 DB·Log, BigQuery, 적재 설정, 예약 쿼리, BI 리포트가 서로 다른 시스템에 존재
- 날짜 샤드가 논리적으로 같은 자산을 여러 노드로 늘림
- 테이블 Lineage와 컬럼 매핑은 정확도가 다른데 같은 선으로 표현하기 쉬움
- 무제한 그래프와 임의 SQL은 응답 범위와 보안 경계를 예측하기 어려움
- MCP 응답을 Markdown으로만 반환하면 사용자가 자산을 다시 복사하고 다음 질문을 작성해야 함

## Architecture

```text
[Information Schema / Audit]
[Airflow·Embulk 설정 / BI metadata]
                │ daily collect
                ▼
        [BigQuery catalog_*]
   assets · columns · lineage · audit
                │ fixed SELECT
                ▼
          [Discovery MCP]
       search · detail · lineage
                │
        ┌───────┴────────┐
        ▼                ▼
 [Claude conversation] [Prefab UI / MCP Apps]
```

원천 시스템에 직접 질의하는 별도 UI를 만들지 않고, 수집·정규화·조회·표현 계층을 분리했습니다. 자연어 검색, 표, 그래프는 모두 같은 카탈로그 계약을 바라봅니다.

## Collection & Normalization

Airflow 일배치로 다음 정보를 수집합니다.

- BigQuery Information Schema와 Audit Log
- Airflow·Embulk 적재 설정
- Looker 등 BI 리소스 metadata

수집된 데이터는 현재 상태와 변경 이력을 나누어 `catalog_*` 테이블에 저장합니다.

| 테이블 | 책임 |
| --- | --- |
| `catalog_assets` | 자산의 현재 상태·owner·tag·metadata·last_seen |
| `catalog_columns` | 현재 컬럼 스냅샷 |
| `catalog_columns_history` | 컬럼 추가·삭제·타입·nullable 변경 |
| `catalog_lineage` | 테이블 단위 source → destination edge |
| `catalog_lineage_columns` | SQL/Embulk 컬럼 매핑과 confidence |
| `catalog_audit_jobs` | Query·Scheduled Query·DDL 감사 근거 |

### Asset ID

provider family와 원래 경로를 보존하는 `asset_id`를 사용해 BigQuery·MySQL·BI·파이프라인 자산을 같은 축으로 연결했습니다. 이름 충돌을 막기 위해 source family를 구분하고, 다음 provider를 추가할 수 있도록 asset type과 prefix를 확장 가능하게 두었습니다.

날짜 샤드는 `orders_YYYYMMDD` 같은 물리 테이블을 `orders_*` 논리 자산으로 정규화합니다. 카탈로그의 `shard_group_id`를 우선 사용하고, 메타데이터가 없을 때만 날짜 suffix 규칙으로 보완합니다.

## Lineage Engine

무제한으로 모든 연결을 반환하지 않고 root 중심 bounded BFS를 적용했습니다.

- upstream·downstream frontier를 분리해 방향을 유지
- 탐색 깊이 1~5, 최근 변경 범위 기본 90일
- 최대 200개 노드·1,000개 엣지로 응답 크기 제한
- 상한에 도달하면 `truncated=true`와 `depth_reached`를 함께 반환
- root와 관계없는 cross-branch가 섞이지 않도록 같은 방향의 frontier만 확장

테이블 Lineage와 컬럼 Lineage는 별도의 확실성을 가집니다.

- 테이블 관계: Audit Log의 `referenced_tables`와 destination으로 구성
- 컬럼 관계: SQL parser 결과와 Embulk mapping을 별도 저장
- 기본 confidence 0.70 미만의 매핑은 정확한 관계처럼 표시하지 않음
- 컬럼 파싱 실패가 테이블 관계 실패로 전파되지 않도록 분리

## MCP Tools & Prefab UI

JSON helper tool과 App tool을 같은 MCP registry에 등록했습니다.

```text
소스 선택
  → discovery_list_containers
  → discovery_list_tables
  → discovery_asset_detail
  → Lineage / cost / stale / PII 결과 표시
  → 선택한 asset_id를 SendMessage로 Claude 대화에 전달
```

### User-facing surfaces

- Overview: 소스·컨테이너·테이블 드릴다운
- Search Assets: Search Index 기반 자산 검색
- Asset Detail: metadata·컬럼·변경 이력·최근 edge
- Lineage Graph: graph·edge 표·컬럼 매핑
- Recent Changes / Cost / Staleness
- Who Uses / PII Candidates

Prefab UI는 MCP tool의 실행 결과입니다. 별도 프론트엔드와 API를 유지하는 대신 `PrefabApp`, `CallTool`, `SetState`, `SendMessage`로 서버 조회·화면 상태·대화 컨텍스트를 연결했습니다.

그래프는 외부 graph runtime에 의존하지 않는 self-contained SVG·CSS·JS로 반환합니다. hover·pin·zoom·키보드 포커스를 지원하고, node에는 `tabindex`, `role=button`, `aria-pressed`를 적용했습니다.

## Runtime & Trust

### Local stdio

로컬 Claude Desktop은 stdio와 Application Default Credentials(ADC)로 연결했습니다. 개인 개발·디버깅과 실제 BigQuery smoke test에 적합한 단순한 경로입니다.

### Remote HTTP on GKE

다중 사용자 환경은 FastAPI·FastMCP HTTP runtime으로 분리했습니다.

- OAuth metadata·Dynamic Client Registration·Authorization Code·PKCE(S256)
- access token 기본 1시간, refresh token 기본 7일 TTL
- replica 확장을 위한 Redis TokenStore와 key prefix 분리
- 사용자 email·IP·Google credentials를 요청 context로 전달

### Fixed reads & audit

사용자 입력으로 임의 SQL을 실행하지 않고 `catalog_*`에 대한 도구별 고정 SELECT만 허용합니다. 모든 도구 호출은 중앙 middleware에서 다음 정보를 기록합니다.

```text
account / user_email
timestamp / time
source / client IP
target / tool arguments
action / tool name
result / success or error
```

## Validation

| 경로 | 검증 범위 |
| --- | --- |
| stdio registry | FastMCP tool registry 로드 |
| HTTP smoke | `/health`, 무토큰 401, initialize, `tools/list`, 인증 middleware |
| BigQuery E2E | 검색·상세·Lineage·비용·PII·적재·예약 쿼리 조회 |
| MCP Apps | Prefab/JSON 직렬화와 원격 화면 렌더 |
| Security regression | PKCE, redirect URI, token TTL, OAuth client validation |

검증은 “화면이 그럴듯하다”보다 같은 `asset_id`가 검색 결과·상세·edge·감사 로그까지 이어지는지에 초점을 맞췄습니다. 그래프 overflow, 컬럼 파싱 실패, OAuth handshake 실패도 숨기지 않고 관찰 가능한 상태로 반환합니다.

## Results

- 데이터 검색을 테이블명 확인에서 원천·변환·소비 맥락 탐색으로 확장
- BigQuery·MySQL·BI·파이프라인 자산을 하나의 `asset_id` 축으로 연결
- bounded graph로 응답 크기와 화면 범위를 예측 가능하게 구성
- Prefab UI에서 검색·드릴다운·그래프·채팅 컨텍스트를 한 흐름으로 제공
- 고정 조회·OAuth·PKCE·토큰 TTL·감사 로그로 다중 사용자 운영 경계 구성

## Trade-offs

- Discovery MCP는 catalog를 읽는 계층이며 원천 데이터와 카탈로그를 직접 변경하지 않습니다.
- 테이블 Lineage와 컬럼 Lineage를 같은 정확도로 표현하지 않고 confidence와 evidence를 분리했습니다.
- PII 후보 화면은 현재 read-only 조회 범위이며, 상태 변경 UI를 구현 완료로 표현하지 않았습니다.
- 실제 내부 프로젝트명·자산 ID·사용자 정보·자격증명은 일반화했습니다.

## Tech Stack

- **AI / AX**: Claude Team Plan, MCP, MCP Apps, Prefab UI
- **Data / Catalog**: BigQuery, Information Schema, Audit Log, Airflow, Embulk, Looker metadata
- **Runtime / Security**: FastMCP, FastAPI, GKE, OAuth 2.0, PKCE, Redis
- **Lineage / Query**: bounded BFS, SQL parser, `catalog_*`, BigQuery fixed SELECT

> 실제 업무 경험과 운영 검증을 바탕으로 작성했으며, 내부 식별자·원문 데이터·접근 자격 증명은 포함하지 않았습니다.
