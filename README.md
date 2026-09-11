# 🍴 PlayEAT

> 오늘의 한 끼, 좋은 기억이 되도록

PlayEAT는 사용자의 감정, 상황, 선호도와 예산을 바탕으로 **신대방 주변 음식점을 추천하는 AI 맛집 추천 서비스**입니다. 기존 맛집 서비스에서 충분히 제공하지 못했던 가격대, 음식 특징, 감정·상황 정보를 태그화하고, 사용자에게 더 개인화된 점심 메뉴를 제안합니다.

## 📌 프로젝트 소개

PlayEAT는 사용자가 자연어로 원하는 식사 상황을 입력하면 식당 데이터와 AI 추천을 결합해 적합한 음식점을 보여주는 서비스입니다. 추천 결과에 대한 사용자의 피드백과 서비스 이용 로그를 수집하여 추천 품질과 서비스 운영을 함께 개선할 수 있도록 설계했습니다.

## ✨ 주요 기능

- 회원가입 및 로그인
- 감정·상황·가격대·음식 특징 기반 맛집 추천
- AI 추천 챗봇을 통한 자연어 검색 및 대화
- 추천 음식점과 메뉴 정보 조회
- 추천 결과 피드백 및 대화 기록 관리
- 개인 프로필 및 마이페이지
- 관리자용 서비스 운영 대시보드
- 사용자 행동 및 AI 서비스 로그 분석

## 🛠 기술 스택

| 영역 | 기술 |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI, Python |
| Database | Supabase PostgreSQL |
| Cache / Session | Redis |
| AI | Gemini |
| Collaboration | GitHub, Figma, Notion, Google Seets|

## 🔄 서비스 플로우

![PlayEAT 서비스 플로우](docs/images/01_FLOWCHART.png)

사용자는 로그인 후 원하는 감정, 상황 또는 조건을 입력합니다. 시스템은 식당·메뉴·태그 데이터와 AI 분석 결과를 바탕으로 추천을 생성하고, 사용자의 피드백과 이용 로그를 저장합니다. 관리자는 대시보드에서 서비스 현황과 로그를 확인할 수 있습니다.

## 🎨 UI/UX 디자인

화면 설계와 UI 디자인은 Figma에서 관리합니다.

[👉 PlayEAT Figma 디자인 보기](https://www.figma.com/design/qWQHYXV8U8urintGWyRDj6/%EB%82%98%EB%A7%8C%EC%9D%98%EB%A7%9B%EC%A7%91%EB%B9%84%EC%84%9C?node-id=0-1)

주요 화면:

- 로그인 및 회원가입
- AI 추천 결과 및 챗봇
- 마이페이지
- 관리자 대시보드

## 📚 프로젝트 문서

| 문서 | 설명 |
|---|---|
| [PRD](docs/01_PRD.md) | 프로젝트 배경, 목표, 서비스 및 기능 요구사항 |
| [WBS](docs/02_WBS.html) | 일정, 작업 항목 및 역할 분담 |
| [Flowchart](docs/03_FLOWCHART.md) | 사용자 및 서비스 흐름 |
| [ERD](docs/04_ERD.md) | 서비스 데이터 모델 및 테이블 관계 |
| [DB Definition](docs/05_DB_DEFINITION.md) | 데이터베이스 테이블·컬럼 정의 |
| [API](docs/06_API.md) | Backend API 명세 |
| [Convention](docs/07_convention.html) | 코드 및 Git 협업 규칙 |

## 👥 팀 역할

| 팀원 | 역할 | 담당 |
|---|---|---|
| 배소정 | 팀장 · Backend | 챗봇, 메인 기능, Backend 총괄 |
| 윤수영 | Frontend | 디자인, 로그인, 회원 정보 수정 |
| 조권식 | Frontend | 마이페이지 |
| 백승주 | Frontend | 회원가입 |
| 김윤한 | Dashboard | 관리자 화면 및 Dashboard |



## 📂 프로젝트 구조

```text
.
├── README.md
├── docs/
│   ├── 01_PRD.md
│   ├── 02_WBS.html
│   ├── 03_FLOWCHART.md
│   ├── 04_ERD.md
│   ├── 05_DB_DEFINITION.md
│   ├── 06_API.md
│   ├── 07_convention.html
│   └── images/
├── backend/
├── frontend/
├── requirements.txt
└── .env
```

## 📊 기대 효과

- 사용자의 상황에 맞는 개인화된 맛집 탐색 시간 단축
- 정형화하기 어려운 감정·상황 정보를 활용한 추천 경험 제공
- 추천 결과와 사용자 피드백을 활용한 서비스 개선
- 관리자 로그 분석을 통한 서비스 운영 및 의사결정 지원

## 📄 License

This project is for educational and team-project purposes.
