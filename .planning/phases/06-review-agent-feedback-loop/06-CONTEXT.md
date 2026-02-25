# Phase 6: Review Agent + Feedback Loop - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

생성된 에디토리얼 초안을 LLM-as-a-Judge로 자동 품질 평가하고, 실패 시 구조화된 피드백으로 재생성을 요청하며, 최대 재시도 제한이 동작하는 피드백 루프를 구현한다. Admin 승인/반려는 Phase 7 범위.

</domain>

<decisions>
## Implementation Decisions

### 평가 기준 설계
- 할루시네이션, 포맷(Layout JSON 스키마), 팩트 정확성 3가지 기본 기준
- **컨텐츠 완성도** 추가 — 셀럽/인플루언서, 상품/브랜드 참조가 충분히 포함되었는지 평가
- 총 4가지 평가 기준: 할루시네이션, 포맷, 팩트, 컨텐츠 완성도

### 피드백 구조와 재생성
- 재생성 루프 범위는 Claude 재량 (실패 유형에 따라 Editorial만 또는 Curation부터 전체 재실행 가능)
- 사용자는 Curation 재실행도 가능한 옵션으로 원함 — 필요 시 전체 파이프라인 재실행 허용
- 피드백 전달 방식, 이전 초안 포함 여부는 Claude 재량

### Claude's Discretion
- 각 평가 기준의 가중치/중요도 설계
- 평가 결과 형식 (점수형 vs pass/fail)
- 검증 범위 (LLM 평가만 vs LLM + Pydantic 스키마 병행)
- 전체 통과 기준 (필수/선택 구분 여부)
- 평가 시 컨텍스트 범위 (Layout JSON만 vs 원본 입력 포함)
- 평가 LLM 모델 선택 (같은 Gemini vs 다른 모델)
- 평가 결과 GraphState 저장 여부
- 피드백 전달 방식 (프롬프트 주입 vs state 필드)
- 재생성 시 이전 초안 포함 여부
- 재시도 횟수 (로드맵 기준 3회, 조정 가능)
- 에스컬레이션 시 콘텐츠 처리 방식
- 에스컬레이션 알림 방식
- 에스컬레이션 후 수동 재시도 가능 여부

</decisions>

<specifics>
## Specific Ideas

- 로드맵 Success Criteria에서 "Review → Editorial 피드백 루프가 LangGraph conditional edge로 구현"을 명시 — 그래프 토폴로지에서 확인 가능해야 함
- 재시도 시 이전 피드백이 Editorial Agent에 주입되어 동일 문제 반복 방지

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-review-agent-feedback-loop*
*Context gathered: 2026-02-25*
