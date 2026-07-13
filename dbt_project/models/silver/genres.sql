{{ config(location='s3://hidden-game/silver/genres.parquet', format='parquet') }}

with unnested as (
    select unnest(genres) as genre
    from {{ ref('stg_games') }}
    where genres is not null
)

select distinct
    genre.id as genre_id,
    genre.name as genre_name
from unnested
