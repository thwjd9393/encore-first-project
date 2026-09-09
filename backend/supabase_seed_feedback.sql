-- 유저반응(feedback) 시드
-- 기존 스키마 + supabase_schema_prd_extend.sql 실행 후 사용한다.
--
-- 먼저 할 일:
--   Supabase Dashboard → Authentication → Users → Add user
--   Email: playeat-test@example.com
--   Password: 8자 이상
--   Auto Confirm User 켜기
-- 그다음 이 SQL을 SQL Editor에서 Run

insert into profiles (
    id,
    profile_nickname,
    profile_type
)
select
    id,
    'playeat_test',
    '0'
from auth.users
order by created_at
limit 1
on conflict (id) do nothing;

insert into conversations (user_id, title)
select
    p.id,
    '유저반응 시드 대화'
from profiles p
where p.profile_nickname = 'playeat_test'
  and not exists (
      select 1
      from conversations c
      where c.user_id = p.id
        and c.title = '유저반응 시드 대화'
  );

with seed_rows as (
    select
        p.id as profile_id,
        c.id as conversation_id,
        r.id as restaurant_id,
        v.feedback_value,
        r.rn
    from profiles p
    join conversations c
        on c.user_id = p.id
       and c.title = '유저반응 시드 대화'
    join (
        select
            id,
            row_number() over (order by name) as rn
        from restaurants
        limit 6
    ) r
        on true
    join (
        values
            (1, '3'),
            (2, '3'),
            (3, '2'),
            (4, '2'),
            (5, '1'),
            (6, '1')
    ) as v(rn, feedback_value)
        on v.rn = r.rn
    where p.profile_nickname = 'playeat_test'
),
inserted_recommendations as (
    insert into recommendations (
        request_id,
        profile_id,
        conversation_id,
        restaurant_id,
        conditions,
        reason_source
    )
    select
        gen_random_uuid(),
        seed_rows.profile_id,
        seed_rows.conversation_id,
        seed_rows.restaurant_id,
        '{}'::jsonb,
        'db_fallback'
    from seed_rows
    where not exists (
        select 1
        from feedback f
        where f.conversation_id = seed_rows.conversation_id
    )
    returning id, profile_id, conversation_id, restaurant_id
)
insert into feedback (
    profile_id,
    conversation_id,
    restaurant_id,
    recommendation_id,
    feedback_value
)
select
    seed_rows.profile_id,
    seed_rows.conversation_id,
    seed_rows.restaurant_id,
    inserted_recommendations.id,
    seed_rows.feedback_value
from seed_rows
join inserted_recommendations
    on inserted_recommendations.profile_id = seed_rows.profile_id
   and inserted_recommendations.conversation_id = seed_rows.conversation_id
   and inserted_recommendations.restaurant_id = seed_rows.restaurant_id;

select
    f.feedback_value,
    r.name,
    f.created_at
from feedback f
join restaurants r on r.id = f.restaurant_id
order by f.created_at;
