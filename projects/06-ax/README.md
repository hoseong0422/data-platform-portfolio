# AI Transformation (AX)

## Overview

사내 구성원(개발자 및 비개발자)의 업무 생산성을 극대화하기 위해 **Claude Team Plan을 도입하고 Custom MCP(Model Context Protocol) 서버를 구축**하여 안전한 데이터 연동 환경을 마련했습니다. 이와 동시에, 사내 서비스 및 업무 자동화 도구에서 사용되는 LLM API 호출을 효율적으로 통제하고 비용을 모니터링하기 위해 **LiteLLM Proxy 기반의 API Gateway 체계**를 설계·구축했습니다.

## Problem

1. **AI 에이전트의 데이터 접근 제어 및 보안 가이드라인 부재**
   - 사내에서 AI 에이전트(LLM) 활용이 증가함에 따라 데이터베이스(DB) 및 공유 자산에 무제한 접근할 시 발생할 수 있는 보안 및 컴플라이언스 위험이 존재했습니다.
   - AI 에이전트가 접근할 수 있는 범위를 명확히 제한하고 데이터셋 단위로 권한을 엄격히 통제할 방안이 필요했습니다.

2. **Gemini API 사용량 및 비용 집계의 투명성 부족 (사내 서비스 호출 시)**
   - 사내 서비스 및 업무 자동화 도구가 Gemini API Key를 직접 연동해 호출할 경우, GCP 프로젝트 단위로만 사용량과 비용이 집계되어 개별 Key 단위의 사용량 모니터링이 불가능했습니다.
   - 이로 인해 비용 예측 및 미사용 Key 식별/회수가 어려웠습니다.

## Key Decisions

1. **AI 활용 보안 환경 정책 수립 및 Claude Team Plan 도입**
   - 개발자와 비개발자 모두의 생산성 향상을 위해 Claude Team Plan을 도입했습니다.
   - 안전한 AI 활용을 위해 **에이전트의 실 서비스 데이터베이스(DB) 직접 접근을 원천 금지**하는 정책을 설계했습니다.
   - 데이터 노출 최소화를 위해 분석 전용의 격리된 프로젝트 내 BigQuery만 제한적으로 조회하도록 설계하고, 승인된 구글 공유 드라이브의 Google Sheets에만 접근 가능하도록 규정을 제한했습니다.

2. **Custom MCP (Google Sheets, BigQuery) 서버 구축**
   - 사내 사용자가 Claude Team Plan UI에서 내부 데이터(BigQuery, Google Sheets)를 실시간으로 안전하게 조회하며 연동할 수 있도록 Custom MCP 서버를 구축했습니다.
   - Google OAuth 인증 방식을 적용해 보안 신뢰성을 강화하고, BigQuery 데이터셋 단위로 접근 권한을 관리하여 필요 이상의 내부 데이터 유출을 원천 방지했습니다.

## Architecture

### 1) 사내 사용자의 Claude UI 직접 활용 흐름
```
[사용자 / 개발자] ──> [Claude Team Plan (Web/App UI)]
                             │
                             ▼ (Custom MCP Server / Google OAuth 인증)
                  ┌──────────┴──────────┐
                  ▼                     ▼
       [BigQuery (격리 프로젝트)]   [Google Sheets (지정 공유 드라이브)]
```

### 2) 사내 서비스 및 자동화 도구의 LLM API 호출 흐름
```
[업무 자동화 (Apps Script) / 사내 서비스] ──(IAP)──> [LiteLLM Proxy] ──> [Gemini / LLM APIs]
```

## LiteLLM Proxy

### 1. 도입 배경

사내 서비스와 업무 자동화 도구가 Gemini API Key를 직접 사용하면 GCP 프로젝트 단위로만 사용량과 비용을 확인할 수 있었습니다. 개별 Key의 사용량을 파악할 수 없어 비용을 예측하거나 미사용 Key를 식별·회수하기 어려웠습니다.

### 2. 선택 이유

LiteLLM Proxy를 단일 게이트웨이로 두고 호출을 Key 단위로 관리하는 구조를 선택했습니다. 이를 통해 API Key별 사용량과 비용을 확인하고, 일·월별 사용 한도(Budget Limit)를 적용할 수 있도록 했습니다.

### 3. 운영 구조

사내 서비스와 Google Apps Script 등 업무 자동화 도구의 LLM API 호출을 LiteLLM Proxy로 단일화했습니다. 호출은 GCP IAP(Identity-Aware Proxy)를 거치도록 구성해, Google Workspace 내 서비스가 별도 VPN 노출 없이 사내 인프라의 Proxy에 접근하게 했습니다.

LiteLLM은 Key별 실시간 사용 통계를 수집하고, Rate Limit 초과나 비용 급증을 감지해 알림을 전송합니다. 일정 기간 사용하지 않은 API Key는 점검해 만료 및 권한 회수 대상으로 관리합니다.

Claude Team Plan은 모델 API를 직접 호출하고, 내부 데이터 연동이 필요할 때만 Custom MCP를 사용하도록 분리했습니다.

### 4. 운영 DB 마이그레이션

LiteLLM 운영 DB를 Kubernetes 내부 PostgreSQL에서 Cloud SQL PostgreSQL 17로 이전했습니다. 이후 발생한 Connection Full 문제에는 PgBouncer를 도입해 Cloud SQL의 최대 100개 연결을 40개 미만으로 유지하고 있습니다.

자세한 설계와 검증 과정은 [LiteLLM Cloud SQL 마이그레이션과 DB Connection 안정화](../07-litellm-cloudsql-migration)에서 확인할 수 있습니다.

## Implementation

### 1. AI 활용 환경 및 보안 정책 수립
- AI 에이전트에 대한 최소 권한 원칙(Principle of Least Privilege) 적용 가이드 수립.
- 보안이 확보된 임시 또는 격리된 데이터 분석 환경(Sandboxed BigQuery Dataset)만 LLM의 Context에 연동할 수 있도록 제한.

### 2. Custom MCP Server 개발 및 배포 (Claude Team Plan 연동용)
- **Google OAuth 인증 연동**: OAuth 2.0 프로토콜을 사용해 사용자와 에이전트의 인증 정보를 명확히 식별 및 관리.
- **BigQuery MCP**: 특정 권한이 부여된 데이터셋 내에서만 Query Execution 및 Schema Search가 동작하도록 제한 모듈 구현.
- **Google Sheets MCP**: 공유 드라이브(Shared Drive) 내 사전에 지정된 특정 Spreadsheet ID 범위에서만 셀 데이터를 Read할 수 있도록 수집 리더 모듈 구현.

## Operations

- **OAuth 권한 정기 감사**: Custom MCP에 등록된 Google Cloud 서비스 어카운트의 접근 이력 및 공유 드라이브 소유권을 정기 점검.

## Results

**Before → After**

- **보안 가이드라인**: 정책 부재로 인한 데이터 유출 우려 → 에이전트 DB 직접 접근 금지 정책 및 Custom MCP 접근 제어로 안전한 개발 환경 마련.
- **비용 모니터링 (사내 서비스)**: GCP 프로젝트 단위의 누적 과금만 확인 가능 → API Key별 실시간 사용량 추적 및 비정상 비용 발생 시 차단 가능.
- **사내 연동 편의성**: 보안 리스크로 인한 클라우드 외부 AI API 호출 불가 → IAP 터널을 이용한 Google Apps Script 및 내부 서비스들과의 안전한 사내 LLM 연결 지원.

## Tech Stack

- **AI/AX Suite**: Claude Team Plan, MCP (Model Context Protocol), LiteLLM Proxy
- **Cloud / Security**: GCP BigQuery, Cloud SQL, Google Drive, Google Sheets, IAP (Identity-Aware Proxy), Google OAuth
- **Database**: PostgreSQL, PgBouncer
- **Language / Script**: Python, Google Apps Script
