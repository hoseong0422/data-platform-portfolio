# AI Transformation (AX) · Claude Team Plan & Custom MCP

## Overview

사내 AX를 지원하며 Claude Team Plan을 사내 공식 AI 도구로 채택했습니다. 구성원이 실제로 사용하는 문서·분석 데이터를 하나의 업무 채널에서 연결하되, 원천 시스템의 권한과 보안 경계는 그대로 유지하기 위해 Custom MCP를 구축했습니다.

MCP와 LiteLLM은 모두 AX를 지원하지만 서로 다른 과제입니다. 이 문서는 Claude Team Plan과 Custom MCP를 다루며, 사내 서비스의 LLM API 호출·Key·비용을 통제한 LiteLLM은 [별도 프로젝트](../07-litellm-cloudsql-migration)로 분리했습니다.

## Problem

질문은 하나인데 데이터는 여러 시스템에 흩어져 있었습니다. 특히 비개발자가 BigQuery를 조회하거나 사내 문서를 편집하려면 시스템별 접근 방법과 권한 정책을 따로 알아야 했습니다.

Claude를 공통 업무 채널로 도입하더라도 에이전트가 원천 DB를 직접 읽거나 공유 문서를 모두 편집할 수 있어서는 안 됐습니다. 따라서 소스마다 허용 동작과 접근 범위를 다르게 정한 MCP가 필요했습니다.

## Key Decisions

### 1. Claude Team Plan을 공식 AI 도구로 채택

개발자와 비개발자가 동일한 업무 채널에서 Claude를 사용하도록 표준화했습니다. 데이터 연동은 MCP가 담당하고, 원천 시스템의 사용자 권한과 조직 정책은 각 MCP의 경계에서 다시 확인하도록 했습니다.

### 2. MCP마다 다른 권한 경계 적용

세 MCP를 같은 방식으로 열지 않았습니다.

| MCP | 해결한 업무 | 접근 경계 |
| --- | --- | --- |
| Google Sheets | 공유 문서 검색·조회·편집 | 특정 Shared Drive allowlist, 사용자 OAuth, 문서 ID 검증 |
| BigQuery | 승인된 분석 데이터 조회 | MCP 전용 프로젝트, Origin 프로젝트의 허용된 View, SELECT-only |
| Discovery | 자산·변환 흐름·Lineage 탐색 | 고정 조회, bounded graph, 원천·카탈로그 read-only |

## Architecture

```text
[개발자 / 비개발자]
          │
          ▼
 [Claude Team Plan]
          │
          ▼
 [Custom MCP layer]
    ┌─────┼──────────────┐
    ▼     ▼              ▼
[Sheets] [BigQuery] [Discovery]
 Shared   MCP 전용     catalog_* /
 Drive    project      Lineage / UI
 allowlist authorized
          views
```

MCP는 원천 데이터를 모두 복제하는 계층이 아닙니다. 사용자가 허용된 범위에서 필요한 동작을 호출하고, 결과를 Claude의 대화 흐름으로 되돌리는 연결 계층입니다.

## Custom MCP

### 1. Google Sheets MCP

Claude에 공식 Google Sheets MCP가 없어 직접 구축했습니다. 사내에서 많이 사용하는 문서 도구를 AX 채널에 연결하되, 특정 Shared Drive에 저장된 스프레드시트만 대상으로 삼았습니다.

- 특정 Shared Drive allowlist에 포함된 문서만 검색·노출
- 사용자 Google OAuth 권한과 문서 ID를 함께 확인
- 읽기뿐 아니라 허용된 스프레드시트의 range 편집·행 추가·서식 변경 지원
- GKE에 배포해 운영
- 허용 범위를 벗어난 문서 요청과 접근 검증 실패는 거절하고 감사 로그에 남김

### 2. BigQuery MCP

비개발자의 BigQuery 조회가 원천 프로젝트로 직접 향하지 않도록 MCP 전용 신규 프로젝트를 만들었습니다. 사내 비개발자 조회는 해당 프로젝트에서만 진행하도록 정책을 세웠습니다.

- Origin 프로젝트의 테이블을 그대로 공개하지 않고 허용된 View만 MCP 전용 프로젝트에 연결
- 사용자는 기존과 같은 분석 테이블을 조회하지만, MCP는 분리된 프로젝트에서 실행
- 프로젝트 allowlist·dataset IAM·SELECT-only 도구 계약으로 임의 변경을 차단
- 쿼리 실행 전 dry-run과 고정 조회 범위를 적용

### 3. Discovery MCP

BigQuery를 Data Lake·Warehouse·Mart로 활용하면서, 원천 DB·Log가 어떤 적재·변환 단계를 거쳐 소비되는지 확인할 수 있는 도구를 구축했습니다.

- Airflow·Embulk 설정, BigQuery Information Schema·Audit, BI 리소스를 카탈로그로 수집
- `catalog_*` 테이블에 자산·컬럼·변경 이력·테이블/컬럼 Lineage·감사 근거를 분리 저장
- 원천 소스와 BigQuery 예약 쿼리의 변환 흐름을 `asset_id` 축으로 연결
- 검색·자산 상세·최근 변경·비용·Staleness·PII 후보·소비자 탐색 제공
- MCP Apps(Prefab UI)로 필요한 데이터와 상호작용 화면을 함께 반환

## Discovery Data Contract

### Asset identity

자산 ID는 소스 family와 경로를 함께 담아 BigQuery·MySQL·Looker·파이프라인 자산을 같은 축으로 연결합니다. 날짜 샤드는 `orders_YYYYMMDD` 같은 물리 테이블을 `orders_*` 논리 자산으로 정규화해 그래프 노드가 불필요하게 늘어나지 않도록 했습니다.

### Catalog tables

| 영역 | 책임 |
| --- | --- |
| `catalog_assets` | 자산의 현재 상태·owner·tag·metadata·last_seen |
| `catalog_columns` | 현재 컬럼 스냅샷 |
| `catalog_columns_history` | 추가·삭제·타입·nullable 변경 이력 |
| `catalog_lineage` | 테이블 단위 source → destination 관계 |
| `catalog_lineage_columns` | SQL/Embulk 기반 컬럼 매핑과 confidence |
| `catalog_audit_jobs` | Query·Scheduled Query·DDL 감사 근거 |

현재 상태는 빠르게 읽을 수 있도록 MERGE하고, 변경 이력은 append-only로 보존합니다. 테이블 Lineage와 컬럼 Lineage는 확실성이 다르므로 별도 저장하고, 컬럼 파싱 실패가 테이블 관계의 실패로 번지지 않게 했습니다.

## Lineage Engine

무제한 그래프를 반환하지 않고 root 중심 bounded BFS를 적용했습니다.

- upstream과 downstream frontier를 분리해 방향을 유지
- 기본 최근 변경 범위 90일, 탐색 깊이 1~5
- 최대 200개 노드·1,000개 엣지로 응답 크기 제한
- 상한에 도달하면 조용히 자르지 않고 `truncated=true`, `depth_reached`를 반환
- root와 관계없는 cross-branch가 섞이지 않도록 같은 방향의 frontier만 확장

테이블 Lineage와 컬럼 Lineage는 별도의 확실성을 가집니다.

- 테이블 관계: Audit Log의 `referenced_tables`와 destination으로 구성
- 컬럼 관계: SQL parser 결과와 Embulk mapping을 별도 저장
- 기본 confidence 0.70 미만의 매핑은 정확한 관계처럼 표시하지 않음
- 컬럼 파싱 실패가 테이블 관계 실패로 전파되지 않도록 분리

## MCP Apps

별도 프론트엔드와 API를 유지하는 대신 JSON helper tool과 App tool을 같은 MCP registry에 등록했습니다.

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

### Local

로컬 Claude Desktop은 stdio와 Application Default Credentials(ADC)로 연결했습니다. 개인 개발·디버깅과 실제 BigQuery smoke test에 적합한 단순한 경로입니다.

### Remote

다중 사용자 환경은 GKE의 FastAPI·FastMCP HTTP runtime으로 분리했습니다.

- OAuth metadata·Dynamic Client Registration·Authorization Code·PKCE(S256)
- access token 기본 1시간, refresh token 기본 7일 TTL
- replica 확장을 위해 Redis TokenStore와 key prefix 분리
- 사용자 email·IP·Google credentials를 요청 context에 전달
- 사용자가 임의 SQL을 넣지 않고 `catalog_*`에 대한 고정 SELECT만 실행
- 호출 사용자·시각·source·IP·target·tool·성공/오류 결과를 감사 로그로 기록

## Validation

“동작한다”를 한 경로로 판단하지 않고, 다음 검증 경계를 분리했습니다.

| 경로 | 확인한 것 |
| --- | --- |
| stdio registry | FastMCP tool registry 로드와 실제 BigQuery 조회 |
| HTTP smoke | `/health`, 무토큰 401, initialize, `tools/list`, 인증 middleware |
| MCP Apps E2E | 검색·상세·Lineage·비용·PII·Prefab/JSON 직렬화 |
| Security regression | PKCE, redirect URI, token TTL, OAuth client 검증 |
| Remote render | 원격 HTTP MCP Apps에서 Claude가 Prefab UI를 실제 렌더하는 경로 |

검증은 “화면이 그럴듯하다”보다 같은 `asset_id`가 검색 결과·상세·edge·감사 로그까지 이어지는지에 초점을 맞췄습니다. 그래프 overflow, 컬럼 파싱 실패, OAuth handshake 실패도 숨기지 않고 관찰 가능한 상태로 반환합니다.

## Results

- 문서 편집·승인 데이터 조회·자산 탐색을 하나의 Claude 업무 채널로 연결
- 소스별 allowlist·OAuth·프로젝트/IAM·SELECT-only·read-only 경계를 분리
- 같은 `asset_id`를 검색 결과·상세·Lineage·그래프·감사 로그까지 연결
- 그래프 범위, 컬럼 매핑 실패, OAuth handshake 실패를 숨기지 않고 관찰 가능한 상태로 표현
- bounded graph로 응답 크기와 화면 범위를 예측 가능하게 구성

## Trade-offs

- Discovery MCP는 catalog를 읽는 계층이며 원천 데이터와 카탈로그를 직접 변경하지 않습니다.
- 테이블 Lineage와 컬럼 Lineage를 같은 정확도로 표현하지 않고 confidence와 evidence를 분리했습니다.
- 초기 설계에 있던 상태 변경 UI는 구현 완료로 표현하지 않고, 현재는 read-only PII 후보 조회 범위로 한정했습니다.
- 실제 내부 프로젝트명·자산 ID·사용자 정보·자격증명은 이 문서에서 일반화했습니다.

## Tech Stack

- **AI / AX**: Claude Team Plan, MCP, MCP Apps, Prefab UI
- **Data / Catalog**: BigQuery, Information Schema, Audit Log, Airflow, Embulk, Looker metadata
- **Runtime / Security**: FastMCP, FastAPI, GKE, OAuth 2.0, PKCE, Redis TokenStore
- **Lineage / Query**: bounded BFS, SQL parser, `catalog_*`, BigQuery fixed SELECT

> 실제 업무 경험과 운영 검증을 바탕으로 작성했으며, 내부 식별자·원문 데이터·접근 자격 증명은 포함하지 않았습니다.
