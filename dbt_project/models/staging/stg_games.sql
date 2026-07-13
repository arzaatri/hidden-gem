-- Bronze is append-only across daily incremental runs: the same game can
-- appear in multiple batch files if it was updated and re-pulled. Keep only
-- the most recent record per game.
select
    id as game_id,
    name,
    rating,
    aggregated_rating,
    aggregated_rating_count,
    follows,
    hypes,
    genres,
    themes,
    keywords,
    summary,
    storyline,
    screenshots,
    to_timestamp(updated_at) as updated_at
from {{ source('bronze', 'raw_games') }}
qualify row_number() over (partition by id order by updated_at desc) = 1
