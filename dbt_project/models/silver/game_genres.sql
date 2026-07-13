{{ config(location='s3://hidden-game/silver/game_genres.parquet', format='parquet') }}

with unnested as (
    select game_id, unnest(genres) as genre
    from {{ ref('stg_games') }}
    where genres is not null
)

select distinct
    game_id,
    genre.id as genre_id
from unnested
