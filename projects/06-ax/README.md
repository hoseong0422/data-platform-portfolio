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

3. **LiteLLM Proxy 도입을 통한 서비스 API 관리 및 모니터링 구축**
   - 사내 서비스 및 업무 자동화 도구(Google Apps Script 등)가 사용하는 LLM API 호출을 단일 게이트웨이(LiteLLM)로 단일화했습니다.
   - 이를 통해 API Key별 사용량 및 비용을 실시간 모니터링하고, GCP IAP(Identity-Aware Proxy)를 통해 사내 인프라 내에 배포된 LiteLLM Proxy에 안전하게 접근하는 환경을 조성했습니다. (※ Claude Team Plan은 최적의 속도와 사용성을 위해 모델 API를 직접 호출하되, 데이터 연동 시에만 Custom MCP를 활용하는 구조로 이원화했습니다.)

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

## Implementation

### 1. AI 활용 환경 및 보안 정책 수립
- AI 에이전트에 대한 최소 권한 원칙(Principle of Least Privilege) 적용 가이드 수립.
- 보안이 확보된 임시 또는 격리된 데이터 분석 환경(Sandboxed BigQuery Dataset)만 LLM의 Context에 연동할 수 있도록 제한.

### 2. Custom MCP Server 개발 및 배포 (Claude Team Plan 연동용)
- **Google OAuth 인증 연동**: OAuth 2.0 프로토콜을 사용해 사용자와 에이전트의 인증 정보를 명확히 식별 및 관리.
- **BigQuery MCP**: 특정 권한이 부여된 데이터셋 내에서만 Query Execution 및 Schema Search가 동작하도록 제한 모듈 구현.
- **Google Sheets MCP**: 공유 드라이브(Shared Drive) 내 사전에 지정된 특정 Spreadsheet ID 범위에서만 셀 데이터를 Read할 수 있도록 수집 리더 모듈 구현.

### 3. LiteLLM Proxy 기반 관리 체계 구축 (내부 서비스/스크립트 연동용)
- **API Key 단위 비용 및 할당량 관리**: 개별 API Key에 대한 일/월별 사용 한도(Budget Limit)를 설정하고 실시간 사용 통계를 수집 및 관리.
- **Google Apps Script 연동용 IAP 터널**: IAP(Identity-Aware Proxy)를 경유하도록 설정하여 별도의 VPN 노출 없이 Google Workspace 내 서비스들이 안전하게 API를 호출하도록 인증 체계 완비.

## Operations

- **이상 징후 실시간 감지**: API Key별 비정상적인 호출 횟수(Rate Limit 초과)나 비용 급증(Cost Spike) 발생 시 Slack 채널 등으로 즉시 알림 전송.
- **미사용 API Key 자동 점검**: 일정 기간(예: 30일) 사용되지 않은 API Key를 모니터링하여 자동 만료 및 권한 회수 처리.
- **OAuth 권한 정기 감사**: Custom MCP에 등록된 Google Cloud 서비스 어카운트의 접근 이력 및 공유 드라이브 소유권을 정기 점검.

## Results

**Before → After**

- **보안 가이드라인**: 정책 부재로 인한 데이터 유출 우려 → 에이전트 DB 직접 접근 금지 정책 및 Custom MCP 접근 제어로 안전한 개발 환경 마련.
- **비용 모니터링 (사내 서비스)**: GCP 프로젝트 단위의 누적 과금만 확인 가능 → API Key별 실시간 사용량 추적 및 비정상 비용 발생 시 차단 가능.
- **사내 연동 편의성**: 보안 리스크로 인한 클라우드 외부 AI API 호출 불가 → IAP 터널을 이용한 Google Apps Script 및 내부 서비스들과의 안전한 사내 LLM 연결 지원.

## Tech Stack

- **AI/AX Suite**: Claude Team Plan, MCP (Model Context Protocol), LiteLLM Proxy
- **Cloud / Security**: GCP BigQuery, Google Drive, Google Sheets, IAP (Identity-Aware Proxy), Google OAuth
- **Language / Script**: Python, Google Apps Script
