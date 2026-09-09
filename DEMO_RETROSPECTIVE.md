# PlayEAT 시연·회고 (M9)

관련: `OPS-DEMO-001`, PRD §29.1·§29.2, P1-4, M9. 기준선 `PRD-BASELINE-1.0`.

## 담당·배포

| 항목 | 값 |
| --- | --- |
| 시연 담당자 | |
| 로그·요약 담당자 | |
| Streamlit 배포 URL | |
| FastAPI 배포 URL | |
| 시연 계정(관리자) | |
| 시연 기간(UTC) | |

배포 URL과 담당자는 시연 직전에 채운다.

## 사전 준비

1. Supabase SQL Editor에서 `backend/supabase_seed_api_logs_m0.sql`과 `backend/supabase_seed_evaluation_cases.sql`을 Run 한다.
2. `backend/.env`에 `GEMINI_API_KEY`를 넣는다. 키가 없거나 Gemini가 실패하면 요약은 `db_stats_v1` 집계 문장으로 대체한다. 대체 요약은 실제 배포 연결 시연을 건너뛰는 용도가 아니다.
3. 관리자(`profile_type = '0'`)로 Streamlit에 로그인한다.

## 시연 대본 (PRD §29.1 8단계)

1. **성공 로그**  
   배포 Streamlit에서 추천 요청을 보내 200 로그를 만든다. 응답 헤더 `X-Request-ID`와 `api_request_logs.request_id`가 같다.

2. **4xx·5xx**  
   검증 실패 요청으로 4xx를 만들고, 준비된 장애 또는 M0 시드 5xx 행으로 서버 오류 처리를 보여준다.

3. **원본 로그 확인**  
   Supabase `api_request_logs`에서 request ID, endpoint, status, latency를 확인한다. `/health`·`/docs`·`/favicon.ico`·`/static*`·`/assets*`는 없다.

4. **정제**  
   관리자 → 로그분석 → **통계분석 및 요약**에서 기간을 고른 뒤 **정제 실행**을 누른다. 실행 ID, 규칙 버전, 포함·제외 건수를 읽고, 최근요청로그에서 행을 눌러 `MISSING_FIELD` / `DUPLICATE` / `TEST_TRAFFIC`과 정규화 경로를 확인한다.

5. **통계**  
   같은 화면에서 사용량·응답시간·에러율 KPI와 차트를 확인한다. 정제를 실행했으면 캡션에 `cleaning_run_id` 기준 집계가 보인다.

6. **LLM 요약**  
   같은 화면에서 **요약 실행**을 누른다. 현황·문제·조치와 근거 로그 표를 연다. Gemini 장애 시 `model: db_stats_v1`과 집계 문장을 보여 주고, 근거 없는 내용을 사실처럼 말하지 않는다.

7. **품질평가·개선 실험**  
   품질평가 탭에서 먼저 **개선 실험 저장**(before `v1` / after `v2`)을 한 뒤 **품질평가 실행**을 누른다. 활성 사례 10건을 사실 60% / 완전 30% / 근거 10%로 채점하고, 같은 사례로 before 다음 after를 저장한다. 총점 5점 미달이어도 성공으로 과장하지 않고 `notes`의 전후 총점을 읽는다.

8. **상태 처리**  
   새로고침, 기간에 로그가 없는 Empty, 조회 실패 Error, 재시도 중 대표 하나를 보여 준다.

## 회고

### 계획 대비 결과

- 계획: 
- 결과: 

### 수치로 확인한 문제

- 포함 로그 건수 / 제외 건수: 
- 품질평가 평균 총점·사실 일치도: 
- 합격 여부(총점 80·사실 80): 

### M7 개선 실험 결과

- 가설: 현황에 포함 로그·에러·응답시간이 빠지면 완전성이 낮다.
- 변경: 모델 유지, v2 후처리 한 줄.
- before 평균 총점: 
- after 평균 총점: 
- 사실 일치도 하락 여부: 
- 판정: 5점 이상 상승이고 사실 일치도가 하락하지 않으면 성공. 아니면 실패로 기록하고 다음 개선만 적는다.

### 남은 위험과 다음 행동

- 
- 
