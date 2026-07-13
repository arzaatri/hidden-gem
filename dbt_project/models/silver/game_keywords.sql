{{ config(location='s3://hidden-game/silver/game_keywords.parquet', format='parquet') }}

with unnested as (
    select game_id, unnest(keywords) as keyword
    from {{ ref('stg_games') }}
    where keywords is not null
)

select distinct
    game_id,
    keyword.id as keyword_id
from unnested
