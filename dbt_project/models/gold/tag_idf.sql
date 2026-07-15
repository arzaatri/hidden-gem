{{ config(database='gold_db', schema='gold', alias='tag_idf') }}

-- IDF per (tag_category, tag_value), used to weight Jaccard similarity so a
-- shared rare keyword counts for more than a shared common genre.
with total_games as (
    select count(*) as n from {{ ref('games') }}
),

genre_df as (
    select 'genre' as tag_category, g.genre_name as tag_value, count(distinct gg.game_id) as df
    from {{ ref('game_genres') }} gg
    join {{ ref('genres') }} g using (genre_id)
    group by g.genre_name
),

theme_df as (
    select 'theme' as tag_category, t.theme_name as tag_value, count(distinct gt.game_id) as df
    from {{ ref('game_themes') }} gt
    join {{ ref('themes') }} t using (theme_id)
    group by t.theme_name
),

keyword_df as (
    select 'keyword' as tag_category, k.keyword_name as tag_value, count(distinct gk.game_id) as df
    from {{ ref('game_keywords') }} gk
    join {{ ref('keywords') }} k using (keyword_id)
    group by k.keyword_name
),

tags as (
    select * from genre_df
    union all
    select * from theme_df
    union all
    select * from keyword_df
)

select
    tags.tag_category,
    tags.tag_value,
    ln(total_games.n::double / tags.df) as idf
from tags
cross join total_games
