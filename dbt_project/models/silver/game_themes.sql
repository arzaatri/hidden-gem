{{ config(location='s3://hidden-game/silver/game_themes.parquet', format='parquet') }}

with unnested as (
    select game_id, unnest(themes) as theme
    from {{ ref('stg_games') }}
    where themes is not null
)

select distinct
    game_id,
    theme.id as theme_id
from unnested
