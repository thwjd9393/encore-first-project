# AI 개발용 문서의 GitHub 업로드 및 사용 가이드

> 대상 저장소: `https://github.com/encore-ai-campus/aio-01-p1-team1`  
> 기준 문서: `PRD-BASELINE-1.0`  
> 대상 도구: Codex, ChatGPT/GPT, Claude

## 1. 목적

이 저장소는 개발 코드와 함께 **확정된 PRD, 공통 디자인 규칙, API·DB 계약, 평가기준**을 관리한다. AI에게 페이지나 기능을 구현시킬 때 저장소의 문서를 같은 기준으로 읽게 하여 다음 두 목표를 달성한다.

1. 페이지마다 디자인과 코드 방식이 달라지는 문제를 방지한다.
2. 교과목 1 공식 평가기준 P1-1~P1-4와 필수과제 M0~M9를 구현 과정에서 계속 검증한다.

## 2. 문서 우선순위

AI는 아래 순서로 문서를 해석해야 한다. 충돌하면 위 문서의 규칙을 우선한다.

1. 교과목 1 공식 평가기준 P1-1~P1-4
2. 필수과제 M0~M9
3. 확정된 의사결정과 `PRD_개정본.md`
4. `design.md`, `API_설계서.md`, DB 정의서 및 코드 컨벤션
5. 변경추적·과거 기록

`PRD_개정본.md`는 `PRD-BASELINE-1.0`으로 고정한다. 변경이 필요하면 기준 문서를 조용히 덮어쓰지 말고, 변경 이유와 영향 범위를 먼저 기록한 뒤 새 버전으로 확정한다.

## 3. GitHub에 올릴 파일

### 3.1 저장소 루트에 둘 핵심 파일

| 파일 | 역할 | AI 사용 방식 |
|---|---|---|
| `AGENTS.md` | Codex용 저장소 작업 규칙과 문서 우선순위 | Codex가 작업 전 가장 먼저 확인 |
| `CLAUDE.md` | Claude용 작업 규칙과 문서 우선순위 | Claude가 작업 전 가장 먼저 확인 |
| `AI_IMPLEMENTATION_GUIDE.md` | 모든 AI가 따를 구현 절차와 검증 규칙 | 작업 요청과 함께 항상 참조 |
| `PRD_개정본.md` | 기능·데이터·API·업무 규칙의 확정 기준 | 구현 범위와 인수조건 판단 |
| `design.md` | 전 페이지 공통 디자인 시스템 | UI·상태·상호작용 구현 기준 |
| `API_설계서.md` | URL, HTTP Method, 요청·응답, 오류 계약 | 백엔드와 프런트엔드 연동 기준 |
| `encore_project.xlsx` | 핵심 DB 정의서. `정의서_new` 탭 우선 | 테이블·컬럼·제약조건 구현 기준 |
| `함수명_코드_컨벤션.md` | 팀 코드 작성 규칙 | 이름·구조·스타일 통일 |
| `약관.md` | 서비스 약관 원문 | 약관 화면 구현 기준 |
| `깃허브생성가이드.md` | 팀 저장소와 브랜치 운영 지침 | Git 작업 시 참고 |

`encore_project.xlsx`는 PRD가 직접 참조하는 원본이므로 함께 올린다. 이후 DB 정의를 Markdown으로 완전히 옮겨 단일 기준 문서를 만들기 전까지는 삭제하지 않는다.

### 3.2 `references/`에 둘 평가 근거

| 파일 | 역할 |
|---|---|
| `AI캠퍼스_단위프로젝트_산출물 제출 관리_v2(교과목별 팀)_업데이트-3.xlsx` | 교과목 1 공식 평가기준 원문 |
| `필수과제 10개.png` | M0~M9 원본 근거 |

평가 원본은 구현 지시서가 아니라 **요구사항의 근거 자료**다. AI는 원본을 읽은 뒤 PRD의 추적표와 대조해야 한다.

### 3.3 `docs/history/`에 둘 이력 문서

| 파일 | 역할 |
|---|---|
| `PRD_결정사항.md` | 확정된 선택과 제외 범위의 근거 |
| `PRD_변경추적.md` | 기존 내용, 문제점, 개정안, 변경 이유 추적 |
| `design_개정_담당자_전달사항.md` | 디자인 문서 개정 과정의 전달 기록 |

이력 문서는 현재 구현 기준을 대신하지 않는다. 기준이 모호할 때 결정 배경을 확인하는 용도로만 사용한다.

## 4. 권장 저장소 구조

```text
aio-01-p1-team1/
├── AGENTS.md
├── CLAUDE.md
├── AI_IMPLEMENTATION_GUIDE.md
├── PRD_개정본.md
├── design.md
├── API_설계서.md
├── encore_project.xlsx
├── 함수명_코드_컨벤션.md
├── 약관.md
├── 깃허브생성가이드.md
├── references/
│   ├── AI캠퍼스_단위프로젝트_산출물_평가기준.xlsx
│   └── 필수과제_10개.png
├── docs/
│   └── history/
│       ├── PRD_결정사항.md
│       ├── PRD_변경추적.md
│       └── design_개정_담당자_전달사항.md
├── frontend/
├── backend/
├── database/
├── tests/
├── .env.example
└── .gitignore
```

파일명은 한 번 정한 뒤 바꾸지 않는 편이 좋다. AI 요청문, 문서 링크, 코드 리뷰에서 같은 경로를 계속 사용할 수 있기 때문이다.

## 5. Git에 올리면 안 되는 정보

공개 저장소에는 비밀값과 개인 데이터를 절대 커밋하지 않는다.

- 실제 `.env` 파일
- OpenAI 등 외부 API 키
- DB 접속 비밀번호와 운영 URL
- Redis 비밀번호
- 개인 식별이 가능한 실제 로그
- 세션, 쿠키, 인증 토큰
- 로컬 캐시와 임시 산출물

권장 `.gitignore` 예시는 다음과 같다.

```gitignore
.env
.env.*
!.env.example
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.venv/
venv/
.DS_Store
.streamlit/secrets.toml
*.log
tmp/
```

`.env.example`에는 값 없이 필요한 변수 이름만 적는다.

```dotenv
OPENAI_API_KEY=
DATABASE_URL=
REDIS_URL=
APP_ENV=development
```

## 6. 최초 업로드 방법

저장소가 비어 있다면 프로젝트 폴더에서 아래 순서로 실행한다.

```bash
git init
git branch -M main
git remote add origin https://github.com/encore-ai-campus/aio-01-p1-team1.git
git add .
git commit -m "docs: add PRD baseline and AI implementation guides"
git push -u origin main
```

원격 저장소에 이미 README나 다른 커밋이 있다면 먼저 원격 내용을 받아 충돌을 확인한다.

```bash
git init
git branch -M main
git remote add origin https://github.com/encore-ai-campus/aio-01-p1-team1.git
git pull origin main --rebase
git add .
git commit -m "docs: add PRD baseline and AI implementation guides"
git push -u origin main
```

업로드 전에는 `git status`와 `git diff --cached`로 비밀값, 불필요한 대용량 파일, 임시 파일이 포함되지 않았는지 확인한다.

## 7. Codex에 작업시키는 방법

Codex는 저장소를 프로젝트로 열고, 한 작업에는 한 페이지 또는 하나의 기능 단위를 맡기는 방식이 안정적이다. `AGENTS.md`의 지침과 실제로 접근 가능한 하위 폴더의 추가 지침을 작업 전에 확인하게 한다. OpenAI 공식 문서도 모델이 `AGENTS.md` 지침에 민감할 수 있으므로, 접근 가능한 지침 파일을 점검하고 우선순위를 명시하라고 안내한다.

### 7.1 Codex 요청 템플릿

```text
이 저장소에서 [구체적인 페이지/기능]을 구현해줘.

작업 전 반드시 다음 문서를 읽어라.
1. AGENTS.md
2. AI_IMPLEMENTATION_GUIDE.md
3. PRD_개정본.md의 해당 기능과 인수조건
4. design.md
5. API_설계서.md
6. encore_project.xlsx의 정의서_new 탭
7. 함수명_코드_컨벤션.md

문서 충돌 시 평가기준과 PRD의 확정 결정을 우선한다.
PRD에 없는 기능을 임의로 추가하지 말고, 거리 계산·회원 탈퇴·거절 이유 기능을 만들지 마라.
Streamlit에서 구현 가능한 범위로 design.md의 토큰과 공통 컴포넌트를 재사용하라.

완료 후 다음을 보고하라.
- 변경 파일과 핵심 동작
- 해당 PRD 인수조건
- P1-1~P1-4 및 M0~M9 중 이번 작업이 충족하는 항목
- 실행한 검증과 남은 제한사항
```

### 7.2 권장 작업 순서

1. 기준 문서 읽기와 구현 범위 요약
2. DB·API 계약 확인
3. 해당 페이지의 UI 및 상태 구현
4. 로딩·빈 데이터·오류·성공 상태 구현
5. 실제 API·DB 연결
6. 테스트 또는 실행 검증
7. 평가기준 추적 결과 보고

큰 요청 하나로 전체 서비스를 한 번에 만들기보다 로그인, 추천, 로그 목록, 로그 상세, 통계 대시보드처럼 검증 가능한 단위로 나눈다.

## 8. ChatGPT/GPT에 작업시키는 방법

ChatGPT가 저장소에 직접 접근할 수 없는 환경이면, 아래 파일을 대화에 직접 첨부한다.

### 8.1 기본 첨부 세트

- `PRD_개정본.md`
- `design.md`
- `API_설계서.md`
- `AI_IMPLEMENTATION_GUIDE.md`
- `함수명_코드_컨벤션.md`
- `encore_project.xlsx`

평가기준을 직접 점검하는 작업에는 `references/`의 두 원본도 추가한다. 결정 배경이 필요한 경우에만 `PRD_결정사항.md`와 `PRD_변경추적.md`를 첨부한다.

### 8.2 ChatGPT/GPT 요청 템플릿

```text
첨부한 PRD와 design.md를 함께 기준으로 [페이지/기능]을 개발해줘.

PRD는 기능·데이터·API·업무 규칙과 인수조건의 기준이고,
design.md는 공통 레이아웃·토큰·컴포넌트·상태 표현의 기준이다.
API_설계서.md와 encore_project.xlsx의 정의서_new 탭을 계약으로 사용해라.

문서에 없는 기능과 UI를 임의로 추가하지 마라.
구현 결과가 P1-1~P1-4와 M0~M9 중 어떤 항목을 충족하는지 명시하고,
코드와 함께 실행 방법, 검증 결과, 남은 제한사항을 제공해라.
```

첨부 파일의 일부만 전달하면 AI가 누락된 규칙을 추정할 수 있다. 특히 UI 작업에서 `design.md`, 데이터 작업에서 `encore_project.xlsx`, API 작업에서 `API_설계서.md`를 빼지 않는다.

## 9. Claude에 작업시키는 방법

Claude Code에서는 저장소 루트의 `CLAUDE.md`를 시작 지침으로 사용한다. 요청할 때는 구현 대상과 관련 PRD 절을 구체적으로 지정한다.

```text
CLAUDE.md와 거기에 지정된 기준 문서를 먼저 읽고 [페이지/기능]을 구현해줘.
PRD-BASELINE-1.0의 범위를 바꾸지 말고 design.md의 디자인 토큰과 상태 규칙을 적용해라.
API와 DB는 API_설계서.md 및 encore_project.xlsx의 정의서_new 탭과 일치시켜라.
완료 후 변경 파일, 인수조건 충족 여부, P1/M 추적 결과와 검증 내용을 보고해라.
```

## 10. 작업 유형별 필수 참조 파일

| 작업 | 반드시 읽을 파일 |
|---|---|
| Streamlit 페이지·컴포넌트 | `PRD_개정본.md`, `design.md`, `AI_IMPLEMENTATION_GUIDE.md` |
| FastAPI 엔드포인트 | `PRD_개정본.md`, `API_설계서.md`, `encore_project.xlsx` |
| DB 모델·마이그레이션 | `encore_project.xlsx`의 `정의서_new`, `PRD_개정본.md` |
| 로그 수집·정제·통계 | `PRD_개정본.md`, `API_설계서.md`, 평가 원본 |
| LLM 요약·품질 확인 | `PRD_개정본.md`, M5·M6 인수조건, 로그 스키마 |
| 전체 평가 검증 | 핵심 문서 전체와 `references/` 원본 |
| 코드 리뷰·리팩터링 | `AGENTS.md` 또는 `CLAUDE.md`, 코드 컨벤션, 해당 설계 문서 |

## 11. PRD와 디자인의 역할 구분

- `PRD_개정본.md`: 페이지의 목적, 기능, 데이터, API, 업무 규칙, 예외, 인수조건을 정의한다.
- `design.md`: 모든 페이지가 공유하는 레이아웃, 색상, 폰트, 간격, 컴포넌트, 상태와 상호작용 표현을 정의한다.
- 구현 코드는 두 문서를 함께 만족해야 한다.
- 디자인 판단으로 PRD에 없는 기능을 추가하지 않는다.
- PRD가 상태를 요구하지만 표현 방식이 없으면 `design.md`의 공통 상태 규칙을 적용한다.
- 문서 간 실제 충돌을 발견하면 임의 해석으로 진행하지 말고 충돌 위치와 선택지를 먼저 기록한다.

## 12. 고정된 주요 범위

AI 요청에 다음 결정이 빠지지 않도록 한다.

- 거리 계산과 거리 기반 정렬·필터는 구현하지 않는다.
- 회원 탈퇴 기능은 구현하지 않는다.
- 추천 거절 이유는 수집하지 않는다.
- 재추천은 현재 후보 중 다음 식당을 제시한다.
- 가격대는 DB의 `하/중/상` 판정을 우선 사용한다.
- 금액 기준 설명은 `12,000원 이하`, `12,000원 초과~20,000원 이하`, `20,000원 초과`다.
- 카테고리는 서비스 화면에서 `한식/일식/중식/양식/기타`를 사용하며, 원본의 `분식/카페`는 `기타`로 매핑한다.
- Redis 도입 여부와 M0~M9 담당자는 후속 결정 사항이다.

## 13. 브랜치와 변경 관리

- `main`: 검증을 통과한 기준 문서와 동작 코드
- 기능 브랜치: `feature/<기능명>`
- 문서 브랜치: `docs/<문서명>`
- 수정 브랜치: `fix/<문제명>`

PR 제목은 변경 결과가 드러나게 작성한다.

```text
feat: implement restaurant recommendation page
docs: freeze PRD baseline 1.0
fix: align error response with API specification
```

PR 설명에는 변경 동작, 관련 PRD 절, 평가기준, 검증 결과를 포함한다. PRD 변경 PR에는 반드시 기존 내용, 문제점 또는 변경 필요사항, 개정안, 변경 이유를 남긴다.

## 14. 업로드 전 최종 체크리스트

- [ ] `PRD_개정본.md`가 `PRD-BASELINE-1.0`으로 표시되어 있다.
- [ ] `AGENTS.md`, `CLAUDE.md`, `AI_IMPLEMENTATION_GUIDE.md`의 우선순위가 서로 일치한다.
- [ ] `design.md`와 PRD의 화면·상태 명칭이 충돌하지 않는다.
- [ ] `API_설계서.md`가 P1-1의 URL, Method, 오류, Pydantic 요구를 다룬다.
- [ ] `encore_project.xlsx`의 `정의서_new` 탭을 핵심 DB 기준으로 명시했다.
- [ ] P1-2의 메인·상세·입력·설정·에러 및 사용자 액션 반응을 추적할 수 있다.
- [ ] P1-3의 3NF, 논리·물리 ERD, 컬럼 상세를 추적할 수 있다.
- [ ] P1-4의 배포 환경 로그 수집→조회→시각화 시연 흐름이 문서에 있다.
- [ ] M0~M9가 PRD의 인수조건 또는 추적표와 연결되어 있다.
- [ ] 거리 계산, 탈퇴, 거절 이유 관련 잔여 요구가 없다.
- [ ] `.env`, API 키, 비밀번호, 실제 개인정보 로그가 포함되지 않았다.
- [ ] `.env.example`에는 변수 이름만 있다.
- [ ] AI에게 한 번에 맡길 구현 범위와 완료조건을 구체적으로 적었다.
- [ ] 업로드 전 변경 목록과 커밋 내용을 검토했다.

## 15. 권장 운영 방식

1. 현재 문서 세트를 먼저 저장소에 올리고 기준 태그를 만든다.
2. AI에게 기능 단위로 작업시키고 각 작업에서 PRD·디자인·API·DB 계약을 함께 참조시킨다.
3. 결과를 실행해 확인한 뒤 PR을 통해 `main`에 반영한다.
4. 기준 문서가 바뀌면 코드보다 먼저 문서 버전과 변경추적을 갱신한다.
5. 시연 전 P1-1~P1-4와 M0~M9를 저장소의 실제 구현과 다시 대조한다.

기준 태그 예시는 `prd-baseline-1.0`이다. 태그를 사용하면 이후 AI가 어느 시점의 PRD로 구현했는지 명확히 확인할 수 있다.

## 참고

- OpenAI, [Using GPT-5.4](https://developers.openai.com/api/docs/guides/latest-model): Codex 작업에서 `AGENTS.md` 지침을 점검하고 우선순위를 명확히 하는 방법을 안내한다.

