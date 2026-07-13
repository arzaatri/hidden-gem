{{ config(location='s3://hidden-game/silver/screenshots.parquet', format='parquet') }}

with unnested as (
    select game_id, unnest(screenshots) as screenshot
    from {{ ref('stg_games') }}
    where screenshots is not null
)

select
    screenshot.id as screenshot_id,
    game_id,
    screenshot.url as url
from unnested
