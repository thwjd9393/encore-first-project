# 코드 컨벤션

관련 문서: [https://app.notion.com/p/3d4a10b0a8e4804abfe1ed9cda0f734b?source=copy_link](https://app.notion.com/p/3d4a10b0a8e4804abfe1ed9cda0f734b?source=copy_link)

| 구분 | 규칙 | 설명 | 좋은 예 | 나쁜 예 |
|---|---|---|---|---|
| 구분 | 규칙 | 설명 | 좋은 예 | 나쁜 예 |
| 기본 규칙 | snake_case | 영어 소문자와 _ 사용 | get_user() | getUser(), GetUser() |
| 함수명 구조 | 동작 + 대상 | 무엇을 하는 함수인지 이름만 보고 알 수 있게 작성 | create_restaurant() | process() |
| 생성 | create_ | 새로운 데이터 생성 | create_user() | make_user() |
| 단건 조회 | get_ | 데이터 하나 조회 | get_user() | find_user() |
| 목록 조회 | list_ | 데이터 여러 개 조회 | list_users() | get_users() |
| 수정 | update_ | 기존 데이터 수정 | update_user() | change_user() |
| 삭제 | delete_ | 데이터 삭제 | delete_user() | remove_user() |
| 검색 | search_ | 검색어나 조건으로 데이터 검색 | search_restaurants() | find_restaurants() |
| 외부 API 조회 | fetch_ | 외부 API에서 데이터 가져오기 | fetch_kakao_places() | get_kakao() |
| 화면 출력 | render_ | Streamlit 화면에 UI 표시 | render_navbar() | show_nav() |
| 이벤트 처리 | handle_ | 버튼 클릭 등 사용자 동작 처리 | handle_login() | login_button() |
| 검증 | validate_ | 입력값이나 데이터 검사 | validate_email() | check_email() |
| 조건 조회 | _by_조건 | 특정 조건으로 데이터 조회 | get_user_by_email() | get_email_user() |
| 피해야 할 이름 | 의미 없는 이름 금지 | 무슨 일을 하는지 알 수 없는 이름은 사용하지 않음 | create_message() | data(), test(), func1(), abc() |
| 핵심 규칙 | 같은 기능은 같은 단어 사용 | 팀원마다 find, select, read 등을 섞지 않고 규칙 통일 | get_user() | find_user(), select_user(), read_user() |
