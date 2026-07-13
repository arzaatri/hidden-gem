{{ config(location='s3://hidden-game/silver/keywords.parquet', format='parquet') }}

with unnested as (
    select unnest(keywords) as keyword
    from {{ ref('stg_games') }}
    where keywords is not null
)

select distinct
    keyword.id as keyword_id,
    keyword.name as keyword_name
from unnested
