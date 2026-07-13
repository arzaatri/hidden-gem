{{ config(location='s3://hidden-game/silver/themes.parquet', format='parquet') }}

with unnested as (
    select unnest(themes) as theme
    from {{ ref('stg_games') }}
    where themes is not null
)

select distinct
    theme.id as theme_id,
    theme.name as theme_name
from unnested
