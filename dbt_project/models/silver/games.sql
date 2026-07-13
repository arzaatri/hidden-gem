{{ config(location='s3://hidden-game/silver/games.parquet', format='parquet') }}

select
    game_id,
    name,
    rating,
    aggregated_rating,
    aggregated_rating_count,
    follows,
    hypes,
    summary,
    storyline,
    updated_at
from {{ ref('stg_games') }}
