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

-- Per-release-year, not a single global cutoff: the industry's audience (and
-- so review/follow/hype volume) has grown enormously over time, so an old
-- game would look artificially "hidden" against a cutoff dominated by
-- modern releases. Comparing each game only to others from its own release
-- year controls for that. Games with no release date are bucketed together
-- (a null partition key groups them, same as any other value) rather than
-- dropped.
--
-- Rank-based, not percentile_cont: these signals are null/0 for a large
-- share of games (IGDB only populates them when a game has enough
-- engagement), so many release years have a huge mass of games tied at the
-- floor value. percentile_cont picks a boundary *value* (often just 0) and
-- `<=` then matches the entire tied mass — e.g. year 2000 had 217/301 games
-- tied at aggregated_rating_count=0, so a "10th percentile" cutoff of 0
-- flagged 72% of that year's games, not 10%. Ranking with a deterministic
-- tiebreak (game_id) and comparing rank-in-year against a row-count quota
-- guarantees exactly the bottom N% per year get flagged on each signal,
-- regardless of how many games tie at the floor.
signal_ranks as (
    select
        game_id,
        row_number() over (
            partition by extract(year from first_release_date)
            order by coalesce(aggregated_rating_count, 0), game_id
        ) as rating_count_rank,
        row_number() over (
            partition by extract(year from first_release_date)
            order by coalesce(follows, 0), game_id
        ) as follows_rank,
        row_number() over (
            partition by extract(year from first_release_date)
            order by coalesce(hypes, 0), game_id
        ) as hypes_rank,
        count(*) over (partition by extract(year from first_release_date)) as year_total
    from {{ ref('games') }}
),

-- Each signal becomes its own obscure/not-obscure flag (bottom N% for its
-- release year, threshold from etl.hidden_gem.thresholds), then blended
-- into one score via etl.hidden_gem.weights (sums to 1). hidden_gem is
-- true once that weighted score clears etl.hidden_gem.obscurity_score_cutoff
-- — e.g. at the default 0.5, a weighted majority of the configured signals
-- must call the game obscure.
obscurity as (
    select
        game_id,
        (case when rating_count_rank <= ceil(year_total * {{ var('hidden_gem')['thresholds']['aggregated_rating_count_percentile'] }} / 100.0)
              then {{ var('hidden_gem')['weights']['aggregated_rating_count'] }} else 0 end)
      + (case when follows_rank <= ceil(year_total * {{ var('hidden_gem')['thresholds']['follows_percentile'] }} / 100.0)
              then {{ var('hidden_gem')['weights']['follows'] }} else 0 end)
      + (case when hypes_rank <= ceil(year_total * {{ var('hidden_gem')['thresholds']['hypes_percentile'] }} / 100.0)
              then {{ var('hidden_gem')['weights']['hypes'] }} else 0 end)
        as obscurity_score
    from signal_ranks
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
    obscurity.obscurity_score >= {{ var('hidden_gem')['obscurity_score_cutoff'] }} as hidden_gem
from {{ ref('games') }} as games
left join genre_agg on genre_agg.game_id = games.game_id
left join theme_agg on theme_agg.game_id = games.game_id
left join keyword_agg on keyword_agg.game_id = games.game_id
left join obscurity on obscurity.game_id = games.game_id
