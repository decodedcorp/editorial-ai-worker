---
phase: quick-004
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - data/contents/0bd8e21f-2f81-4e3c-8741-0c0031b47c69.json
  - data/contents/1572212f-117c-4024-996e-f203447dad5c.json
  - data/contents/2f7378c0-bce9-4846-b7b8-01ca0a5f9a2c.json
  - data/contents/32ad44e2-78c0-4065-9dc9-a8731e3cf6ac.json
  - data/contents/78ba3006-8522-407f-ab66-061ddbb44305.json
  - data/contents/7a931ea5-ae89-4aa0-926d-f66b3baf4927.json
  - data/contents/7e738dce-53f0-44fb-9fa2-8d5f5cdff430.json
  - data/contents/aa919445-b899-422f-9a51-4654a478d7c4.json
  - data/contents/c7b37e70-10ac-4394-8872-e9a58f0003f3.json
  - data/contents/c911625d-43d2-4384-859f-df8d9cb25b88.json
  - data/contents/dee6ec30-aad8-4cde-b265-54dd540d9a0a.json
  - data/contents/e4fb3776-dc75-4a5c-851d-34e2ccee32a8.json
autonomous: true

must_haves:
  truths:
    - "12개 루트 JSON 파일의 날짜가 Feb 24-26에 고르게 분산된다"
    - "created_at < updated_at < published_at 순서가 모든 파일에서 유지된다"
    - "pending 상태 파일 5개의 published_at은 null로 유지된다"
    - "published 상태 파일 7개 모두 published_at 값을 가진다"
    - "subdirectory 파일(v2-diverse, v3-diverse-deduped, v4-prev)은 변경되지 않는다"
  artifacts:
    - path: "data/contents/*.json (root level, 12 files)"
      provides: "다양한 시간대로 재배정된 날짜 필드"
  key_links:
    - from: "status field"
      to: "published_at field"
      via: "pending -> null, published -> datetime"
---

<objective>
12개 루트 에디토리얼 JSON 파일의 날짜 필드(created_at, updated_at, published_at)를 2026-02-24~26 범위 내에서 더 다양하고 자연스럽게 재배정한다.

Purpose: 관리자 UI에서 콘텐츠 목록 조회 시 시간 분포가 현실적으로 보이도록 하기 위함. 현재 Feb 24에 published 파일이 3개 몰려 있고, 시간 간격이 불균일하다.
Output: 각 파일의 날짜가 3일 전체에 자연스럽게 분산된 12개의 업데이트된 JSON 파일
</objective>

<execution_context>
@/Users/kiyeol/.claude-pers/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
Target directory: /Users/kiyeol/development/decoded/editorial-ai-worker/data/contents/
Only modify files directly in this directory (12 root JSON files).
Do NOT touch subdirectories: v2-diverse/, v3-diverse-deduped/, v4-prev/

Current date distribution (for reference):
- 0bd8e21f: published, created 2026-02-24T09:43
- 1572212f: pending,   created 2026-02-24T11:08
- 2f7378c0: published, created 2026-02-24T18:07
- 32ad44e2: published, created 2026-02-24T19:17
- 78ba3006: pending,   created 2026-02-25T08:05
- 7a931ea5: published, created 2026-02-25T11:32
- 7e738dce: pending,   created 2026-02-25T17:27
- aa919445: pending,   created 2026-02-25T22:34
- c7b37e70: published, created 2026-02-26T08:35
- c911625d: published, created 2026-02-26T15:37
- dee6ec30: published, created 2026-02-26T16:26  <- too close to c911625d
- e4fb3776: pending,   created 2026-02-26T19:41

Problems to fix:
1. Feb 24에 published 3개(09:43, 18:07, 19:17) 집중 - 저녁 시간대 2개가 매우 근접
2. dee6ec30과 c911625d가 Feb 26 오후에 49분 차이로 너무 가깝게 붙어있음
3. 전체적으로 오전/오후/저녁 시간대 분포가 불균일
</context>

<tasks>

<task type="auto">
  <name>Task 1: 날짜 재배정 Python 스크립트 실행으로 12개 파일 업데이트</name>
  <files>data/contents/0bd8e21f-2f81-4e3c-8741-0c0031b47c69.json
data/contents/1572212f-117c-4024-996e-f203447dad5c.json
data/contents/2f7378c0-bce9-4846-b7b8-01ca0a5f9a2c.json
data/contents/32ad44e2-78c0-4065-9dc9-a8731e3cf6ac.json
data/contents/78ba3006-8522-407f-ab66-061ddbb44305.json
data/contents/7a931ea5-ae89-4aa0-926d-f66b3baf4927.json
data/contents/7e738dce-53f0-44fb-9fa2-8d5f5cdff430.json
data/contents/aa919445-b899-422f-9a51-4654a478d7c4.json
data/contents/c7b37e70-10ac-4394-8872-e9a58f0003f3.json
data/contents/c911625d-43d2-4384-859f-df8d9cb25b88.json
data/contents/dee6ec30-aad8-4cde-b265-54dd540d9a0a.json
data/contents/e4fb3776-dc75-4a5c-851d-34e2ccee32a8.json</files>
  <action>
Python 스크립트를 인라인으로 실행하여 12개 파일의 날짜를 재배정한다.

목표 날짜 배정표 (아래 값으로 정확히 설정):

| 파일 | status | created_at | updated_at | published_at |
|------|--------|------------|------------|--------------|
| 0bd8e21f | published | 2026-02-24T08:12:33+00:00 | 2026-02-24T08:25:14+00:00 | 2026-02-24T09:47:52+00:00 |
| 1572212f | pending   | 2026-02-24T14:33:07+00:00 | 2026-02-24T14:41:22+00:00 | null |
| 2f7378c0 | published | 2026-02-24T17:05:44+00:00 | 2026-02-24T17:18:09+00:00 | 2026-02-24T17:52:31+00:00 |
| 32ad44e2 | published | 2026-02-24T21:48:19+00:00 | 2026-02-24T22:03:55+00:00 | 2026-02-24T22:37:44+00:00 |
| 78ba3006 | pending   | 2026-02-25T07:22:41+00:00 | 2026-02-25T07:35:18+00:00 | null |
| 7a931ea5 | published | 2026-02-25T10:14:26+00:00 | 2026-02-25T10:19:53+00:00 | 2026-02-25T10:48:07+00:00 |
| 7e738dce | pending   | 2026-02-25T15:56:02+00:00 | 2026-02-25T16:04:37+00:00 | null |
| aa919445 | pending   | 2026-02-25T20:11:38+00:00 | 2026-02-25T20:18:44+00:00 | null |
| c7b37e70 | published | 2026-02-26T09:03:15+00:00 | 2026-02-26T09:14:28+00:00 | 2026-02-26T09:51:03+00:00 |
| c911625d | published | 2026-02-26T13:27:49+00:00 | 2026-02-26T13:39:22+00:00 | 2026-02-26T14:15:58+00:00 |
| dee6ec30 | published | 2026-02-26T17:44:06+00:00 | 2026-02-26T17:55:31+00:00 | 2026-02-26T18:28:19+00:00 |
| e4fb3776 | pending   | 2026-02-26T22:09:53+00:00 | 2026-02-26T22:19:47+00:00 | null |

실행할 Python 코드:

```python
import json

CONTENT_DIR = "/Users/kiyeol/development/decoded/editorial-ai-worker/data/contents"

updates = {
    "0bd8e21f-2f81-4e3c-8741-0c0031b47c69": {
        "created_at": "2026-02-24T08:12:33+00:00",
        "updated_at": "2026-02-24T08:25:14+00:00",
        "published_at": "2026-02-24T09:47:52+00:00",
    },
    "1572212f-117c-4024-996e-f203447dad5c": {
        "created_at": "2026-02-24T14:33:07+00:00",
        "updated_at": "2026-02-24T14:41:22+00:00",
        "published_at": None,
    },
    "2f7378c0-bce9-4846-b7b8-01ca0a5f9a2c": {
        "created_at": "2026-02-24T17:05:44+00:00",
        "updated_at": "2026-02-24T17:18:09+00:00",
        "published_at": "2026-02-24T17:52:31+00:00",
    },
    "32ad44e2-78c0-4065-9dc9-a8731e3cf6ac": {
        "created_at": "2026-02-24T21:48:19+00:00",
        "updated_at": "2026-02-24T22:03:55+00:00",
        "published_at": "2026-02-24T22:37:44+00:00",
    },
    "78ba3006-8522-407f-ab66-061ddbb44305": {
        "created_at": "2026-02-25T07:22:41+00:00",
        "updated_at": "2026-02-25T07:35:18+00:00",
        "published_at": None,
    },
    "7a931ea5-ae89-4aa0-926d-f66b3baf4927": {
        "created_at": "2026-02-25T10:14:26+00:00",
        "updated_at": "2026-02-25T10:19:53+00:00",
        "published_at": "2026-02-25T10:48:07+00:00",
    },
    "7e738dce-53f0-44fb-9fa2-8d5f5cdff430": {
        "created_at": "2026-02-25T15:56:02+00:00",
        "updated_at": "2026-02-25T16:04:37+00:00",
        "published_at": None,
    },
    "aa919445-b899-422f-9a51-4654a478d7c4": {
        "created_at": "2026-02-25T20:11:38+00:00",
        "updated_at": "2026-02-25T20:18:44+00:00",
        "published_at": None,
    },
    "c7b37e70-10ac-4394-8872-e9a58f0003f3": {
        "created_at": "2026-02-26T09:03:15+00:00",
        "updated_at": "2026-02-26T09:14:28+00:00",
        "published_at": "2026-02-26T09:51:03+00:00",
    },
    "c911625d-43d2-4384-859f-df8d9cb25b88": {
        "created_at": "2026-02-26T13:27:49+00:00",
        "updated_at": "2026-02-26T13:39:22+00:00",
        "published_at": "2026-02-26T14:15:58+00:00",
    },
    "dee6ec30-aad8-4cde-b265-54dd540d9a0a": {
        "created_at": "2026-02-26T17:44:06+00:00",
        "updated_at": "2026-02-26T17:55:31+00:00",
        "published_at": "2026-02-26T18:28:19+00:00",
    },
    "e4fb3776-dc75-4a5c-851d-34e2ccee32a8": {
        "created_at": "2026-02-26T22:09:53+00:00",
        "updated_at": "2026-02-26T22:19:47+00:00",
        "published_at": None,
    },
}

for file_id, dates in updates.items():
    path = f"{CONTENT_DIR}/{file_id}.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["created_at"] = dates["created_at"]
    data["updated_at"] = dates["updated_at"]
    data["published_at"] = dates["published_at"]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Updated: {file_id}.json")

print("Done. 12 files updated.")
```

주의: data/contents/ 바로 아래 12개 파일만 수정. v2-diverse/, v3-diverse-deduped/, v4-prev/ 디렉토리는 절대 건드리지 않음.
  </action>
  <verify>
```bash
python3 -c "
import json, os
CONTENT_DIR = '/Users/kiyeol/development/decoded/editorial-ai-worker/data/contents'
files = sorted([f for f in os.listdir(CONTENT_DIR) if f.endswith('.json') and os.path.isfile(os.path.join(CONTENT_DIR, f))])
print(f'Root JSON files: {len(files)}')
for fname in files:
    d = json.load(open(os.path.join(CONTENT_DIR, fname)))
    status = d.get('status')
    ca = d.get('created_at')
    ua = d.get('updated_at')
    pa = d.get('published_at')
    ok = ca < ua
    if pa:
        ok = ok and ua < pa
    if status == 'pending':
        ok = ok and pa is None
    print(f'{fname[:8]}: {status:9} created={ca[11:16]} updated={ua[11:16]} published={pa[11:16] if pa else \"null\":5} ordering_ok={ok}')
"
```
모든 파일이 `ordering_ok=True`이고, pending 파일은 published=null이어야 한다.
  </verify>
  <done>
- 12개 루트 파일 모두 업데이트 완료
- ordering_ok=True (created_at < updated_at, published_at이 있는 경우 updated_at < published_at)
- pending 5개 파일: published_at = null
- published 7개 파일: published_at 값 존재
- 날짜 분포: Feb 24 (4개: 08시/14시/17시/21시), Feb 25 (4개: 07시/10시/15시/20시), Feb 26 (4개: 09시/13시/17시/22시)로 균일하게 분산
  </done>
</task>

</tasks>

<verification>
1. `python3 -c "import os; files = [f for f in os.listdir('/Users/kiyeol/development/decoded/editorial-ai-worker/data/contents') if f.endswith('.json') and os.path.isfile('/Users/kiyeol/development/decoded/editorial-ai-worker/data/contents/' + f)]; print(len(files))"` 결과가 12여야 함
2. 위 verify 블록 실행 시 모든 파일 ordering_ok=True
3. v2-diverse/, v3-diverse-deduped/, v4-prev/ 내부 파일은 변경 없음 (git diff로 확인)
</verification>

<success_criteria>
- 12개 루트 JSON 파일의 날짜가 Feb 24-26에 각 4개씩 균등 분산
- 각 날짜별로 오전/오후/저녁/밤 시간대를 커버
- 모든 파일에서 created_at < updated_at 보장
- published 파일 7개 모두 updated_at < published_at 보장
- pending 파일 5개 모두 published_at = null 유지
- 서브디렉토리 파일 미변경
</success_criteria>

<output>
완료 후 `.planning/quick/004-fix-editorial-dates/004-SUMMARY.md` 생성 불필요 (quick task).
변경된 파일 목록과 최종 날짜 분포를 응답으로 출력.
</output>
