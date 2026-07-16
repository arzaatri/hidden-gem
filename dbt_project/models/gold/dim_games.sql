{{ config(database='gold_db', schema='gold', alias='dim_games') }}

with genre_agg as (
    select gg.game_id, list(distinct g.genre_name) as genres
    from {{ ref('game_genres') }} gg
    join {{ ref('genres') }} g using (genre_id)
    group by gg.game_id
),

theme_agg as (
    select gt.game_id, list(distinct t.theme_name) as themes
    from {{ ref('game_themes') }} gt
    join {{ ref('themes') }} t using (theme_id)
    group by gt.game_id
),

keyword_agg as (
    select gk.game_id, list(distinct k.keyword_name) as keywords
    from {{ ref('game_keywords') }} gk
    join {{ ref('keywords') }} k using (keyword_id)
    group by gk.game_id
),

-- Recomputed from the full dataset every rebuild, so the hidden-gem cutoff
-- tracks the current dataset's rating-count distribution instead of a fixed
-- number that goes stale as the dataset grows.
threshold as (
    select percentile_cont({{ var('hidden_gem_rating_count_percentile') }} / 100.0)
        within group (order by coalesce(aggregated_rating_count, 0)) as rating_count_cutoff
    from {{ ref('games') }}
)

select
    games.game_id,
    games.name,
    games.rating,
    games.aggregated_rating,
    games.aggregated_rating_count,
    games.follows,
    games.hypes,
    games.summary,
    games.storyline,
    games.cover_image_id,
    games.first_release_date,
    games.updated_at,
    coalesce(genre_agg.genres, []) as genres,
    coalesce(theme_agg.themes, []) as themes,
    coalesce(keyword_agg.keywords, []) as keywords,
    coalesce(games.aggregated_rating_count, 0) <= threshold.rating_count_cutoff as hidden_gem
from {{ ref('games') }} as games
left join genre_agg on genre_agg.game_id = games.game_id
left join theme_agg on theme_agg.game_id = games.game_id
left join keyword_agg on keyword_agg.game_id = games.game_id
cross join threshold
