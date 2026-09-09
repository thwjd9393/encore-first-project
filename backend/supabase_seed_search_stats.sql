-- dashboard_search_stats 시드 (검색정보 도넛 확인용)
-- stat_type: 0 음식 카테고리 / 1 가격대 / 2 상황 태그

insert into dashboard_search_stats (stat_date, stat_type, stat_key, count) values
    (current_date, '0', '한식', 18),
    (current_date, '0', '중식', 9),
    (current_date, '0', '일식', 12),
    (current_date, '0', '기타', 5),
    (current_date, '1', '상', 6),
    (current_date, '1', '중', 22),
    (current_date, '1', '하', 16),
    (current_date, '2', '매운거', 11),
    (current_date, '2', '든든한거', 14),
    (current_date, '2', '국물', 10);
