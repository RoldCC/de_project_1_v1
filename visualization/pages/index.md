---
title: RAWG Games Dashboard
---

# RAWG Games Analytics

A star-schema view of **{kpis[0].total_games}** video games from the RAWG public database.

---

## Filters

```sql genre_options
SELECT DISTINCT genre_name FROM gold_data.dim_genre ORDER BY genre_name
```

```sql platform_options
SELECT DISTINCT platform_name FROM gold_data.dim_platform ORDER BY platform_name
```

```sql esrb_options
SELECT DISTINCT COALESCE(esrb_name, 'Not Rated') AS esrb_name
FROM gold_data.dim_game
ORDER BY esrb_name
```

<Dropdown name=genre data={genre_options} value=genre_name label=genre_name title="Genre">
    <DropdownOption value="%" valueLabel="All Genres"/>
</Dropdown>

<Dropdown name=platform data={platform_options} value=platform_name label=platform_name title="Platform">
    <DropdownOption value="%" valueLabel="All Platforms"/>
</Dropdown>

<Dropdown name=esrb data={esrb_options} value=esrb_name label=esrb_name title="ESRB Rating">
    <DropdownOption value="%" valueLabel="All ESRB Ratings"/>
</Dropdown>

---

## Overview

```sql kpis
SELECT
    COUNT(DISTINCT fgm.game_id)                                           AS total_games,
    ROUND(MEDIAN(CASE WHEN fgm.rating   > 0 THEN fgm.rating   END), 2)   AS median_rating,
    ROUND(MEDIAN(CASE WHEN fgm.playtime > 0 THEN fgm.playtime END), 1)   AS median_playtime_hrs,
    COUNT(DISTINCT fgg.genre_id)                                          AS total_genres,
    COUNT(DISTINCT fgp.platform_id)                                       AS total_platforms
FROM gold_data.fact_game_metrics   fgm
JOIN gold_data.dim_game            dg  ON fgm.game_id    = dg.game_id
LEFT JOIN gold_data.fact_game_genre    fgg ON fgm.game_id = fgg.game_id
LEFT JOIN gold_data.fact_game_platform fgp ON fgm.game_id = fgp.game_id
WHERE fgm.game_id IN (
    SELECT fgg2.game_id FROM gold_data.fact_game_genre fgg2
    JOIN gold_data.dim_genre dgn ON fgg2.genre_id = dgn.genre_id
    WHERE dgn.genre_name LIKE '${inputs.genre.value}'
)
AND fgm.game_id IN (
    SELECT fgp2.game_id FROM gold_data.fact_game_platform fgp2
    JOIN gold_data.dim_platform dp ON fgp2.platform_id = dp.platform_id
    WHERE dp.platform_name LIKE '${inputs.platform.value}'
)
AND COALESCE(dg.esrb_name, 'Not Rated') LIKE '${inputs.esrb.value}'
```

<Grid cols=5>
    <BigValue data={kpis} value=total_games        title="Total Games"        fmt="num0"/>
    <BigValue data={kpis} value=median_rating       title="Median Rating (0–5)"/>
    <BigValue data={kpis} value=median_playtime_hrs title="Median Playtime (hrs)"/>
    <BigValue data={kpis} value=total_genres        title="Genres"            fmt="num0"/>
    <BigValue data={kpis} value=total_platforms     title="Platforms"         fmt="num0"/>
</Grid>

> **Why median?** Rating and playtime distributions are right-skewed — median is more representative than mean for these metrics.

---

## Genre & Platform Breakdown

```sql top_genres
-- filtered by platform + esrb (genre chart is not self-filtered)
SELECT
    dgn.genre_name,
    COUNT(DISTINCT fgg.game_id) AS game_count
FROM gold_data.fact_game_genre fgg
JOIN gold_data.dim_genre dgn ON fgg.genre_id = dgn.genre_id
WHERE fgg.game_id IN (
    SELECT fgp2.game_id FROM gold_data.fact_game_platform fgp2
    JOIN gold_data.dim_platform dp ON fgp2.platform_id = dp.platform_id
    WHERE dp.platform_name LIKE '${inputs.platform.value}'
)
AND fgg.game_id IN (
    SELECT fgm.game_id FROM gold_data.fact_game_metrics fgm
    JOIN gold_data.dim_game dg ON fgm.game_id = dg.game_id
    WHERE COALESCE(dg.esrb_name, 'Not Rated') LIKE '${inputs.esrb.value}'
)
GROUP BY dgn.genre_name
ORDER BY game_count DESC
LIMIT 10
```

```sql top_platforms
-- filtered by genre + esrb (platform chart is not self-filtered)
SELECT
    dp.platform_name,
    COUNT(DISTINCT fgp.game_id) AS game_count
FROM gold_data.fact_game_platform fgp
JOIN gold_data.dim_platform dp ON fgp.platform_id = dp.platform_id
WHERE fgp.game_id IN (
    SELECT fgg2.game_id FROM gold_data.fact_game_genre fgg2
    JOIN gold_data.dim_genre dgn ON fgg2.genre_id = dgn.genre_id
    WHERE dgn.genre_name LIKE '${inputs.genre.value}'
)
AND fgp.game_id IN (
    SELECT fgm.game_id FROM gold_data.fact_game_metrics fgm
    JOIN gold_data.dim_game dg ON fgm.game_id = dg.game_id
    WHERE COALESCE(dg.esrb_name, 'Not Rated') LIKE '${inputs.esrb.value}'
)
GROUP BY dp.platform_name
ORDER BY game_count DESC
LIMIT 10
```

<Grid cols=2>

<BarChart
    data={top_genres}
    x=genre_name
    y=game_count
    swapXY=true
    title="Top 10 Genres"
    xAxisTitle="Games"
    colorPalette={['#236aa4']}
/>

<BarChart
    data={top_platforms}
    x=platform_name
    y=game_count
    swapXY=true
    title="Top 10 Platforms"
    xAxisTitle="Games"
    colorPalette={['#45a1bf']}
/>

</Grid>

---

## Release Trends

```sql games_per_year
SELECT
    DATE_PART('year', dg.released)::INTEGER AS release_year,
    COUNT(DISTINCT fgm.game_id)             AS game_count
FROM gold_data.fact_game_metrics fgm
JOIN gold_data.dim_game dg ON fgm.game_id = dg.game_id
WHERE dg.released IS NOT NULL
AND DATE_PART('year', dg.released) >= 1980
AND fgm.game_id IN (
    SELECT fgg2.game_id FROM gold_data.fact_game_genre fgg2
    JOIN gold_data.dim_genre dgn ON fgg2.genre_id = dgn.genre_id
    WHERE dgn.genre_name LIKE '${inputs.genre.value}'
)
AND fgm.game_id IN (
    SELECT fgp2.game_id FROM gold_data.fact_game_platform fgp2
    JOIN gold_data.dim_platform dp ON fgp2.platform_id = dp.platform_id
    WHERE dp.platform_name LIKE '${inputs.platform.value}'
)
AND COALESCE(dg.esrb_name, 'Not Rated') LIKE '${inputs.esrb.value}'
GROUP BY release_year
ORDER BY release_year
```

<AreaChart
    data={games_per_year}
    x=release_year
    y=game_count
    title="Games Released Per Year"
    xAxisTitle="Year"
    yAxisTitle="Games"
    colorPalette={['#236aa4']}
/>

---

## Rating & ESRB Distribution

```sql rating_dist
SELECT
    (ROUND(fgm.rating * 2) / 2)::DECIMAL(3,1) AS rating_bucket,
    COUNT(DISTINCT fgm.game_id)               AS game_count
FROM gold_data.fact_game_metrics fgm
JOIN gold_data.dim_game dg ON fgm.game_id = dg.game_id
WHERE fgm.rating > 0
AND fgm.game_id IN (
    SELECT fgg2.game_id FROM gold_data.fact_game_genre fgg2
    JOIN gold_data.dim_genre dgn ON fgg2.genre_id = dgn.genre_id
    WHERE dgn.genre_name LIKE '${inputs.genre.value}'
)
AND fgm.game_id IN (
    SELECT fgp2.game_id FROM gold_data.fact_game_platform fgp2
    JOIN gold_data.dim_platform dp ON fgp2.platform_id = dp.platform_id
    WHERE dp.platform_name LIKE '${inputs.platform.value}'
)
AND COALESCE(dg.esrb_name, 'Not Rated') LIKE '${inputs.esrb.value}'
GROUP BY rating_bucket
ORDER BY rating_bucket
```

```sql esrb_dist
-- filtered by genre + platform (esrb chart is not self-filtered)
SELECT
    COALESCE(dg.esrb_name, 'Not Rated') AS esrb_rating,
    COUNT(DISTINCT fgm.game_id)         AS game_count
FROM gold_data.fact_game_metrics fgm
JOIN gold_data.dim_game dg ON fgm.game_id = dg.game_id
WHERE fgm.game_id IN (
    SELECT fgg2.game_id FROM gold_data.fact_game_genre fgg2
    JOIN gold_data.dim_genre dgn ON fgg2.genre_id = dgn.genre_id
    WHERE dgn.genre_name LIKE '${inputs.genre.value}'
)
AND fgm.game_id IN (
    SELECT fgp2.game_id FROM gold_data.fact_game_platform fgp2
    JOIN gold_data.dim_platform dp ON fgp2.platform_id = dp.platform_id
    WHERE dp.platform_name LIKE '${inputs.platform.value}'
)
GROUP BY esrb_rating
ORDER BY game_count DESC
```

<Grid cols=2>

<BarChart
    data={rating_dist}
    x=rating_bucket
    y=game_count
    title="Rating Distribution (0.5-step buckets)"
    xAxisTitle="Rating"
    yAxisTitle="Games"
    colorPalette={['#f4b548']}
/>

<BarChart
    data={esrb_dist}
    x=esrb_rating
    y=game_count
    title="ESRB Rating Distribution"
    xAxisTitle="ESRB"
    yAxisTitle="Games"
    colorPalette={['#8f3d56']}
/>

</Grid>

---

## Store Coverage

```sql top_stores
SELECT
    ds.store_name,
    COUNT(DISTINCT fgs.game_id) AS game_count
FROM gold_data.fact_game_store fgs
JOIN gold_data.dim_store ds ON fgs.store_id = ds.store_id
WHERE fgs.game_id IN (
    SELECT fgg2.game_id FROM gold_data.fact_game_genre fgg2
    JOIN gold_data.dim_genre dgn ON fgg2.genre_id = dgn.genre_id
    WHERE dgn.genre_name LIKE '${inputs.genre.value}'
)
AND fgs.game_id IN (
    SELECT fgp2.game_id FROM gold_data.fact_game_platform fgp2
    JOIN gold_data.dim_platform dp ON fgp2.platform_id = dp.platform_id
    WHERE dp.platform_name LIKE '${inputs.platform.value}'
)
AND fgs.game_id IN (
    SELECT fgm.game_id FROM gold_data.fact_game_metrics fgm
    JOIN gold_data.dim_game dg ON fgm.game_id = dg.game_id
    WHERE COALESCE(dg.esrb_name, 'Not Rated') LIKE '${inputs.esrb.value}'
)
GROUP BY ds.store_name
ORDER BY game_count DESC
LIMIT 10
```

<BarChart
    data={top_stores}
    x=store_name
    y=game_count
    swapXY=true
    title="Top 10 Stores by Game Count"
    xAxisTitle="Games"
    colorPalette={['#46a485']}
/>

---

## Top-Rated Games

```sql top_games
SELECT
    dg.name                                       AS game,
    DATE_PART('year', dg.released)::INTEGER       AS year,
    COALESCE(dg.esrb_name, 'Not Rated')           AS esrb,
    ROUND(fgm.rating,        2)                   AS rating,
    fgm.playtime                                  AS playtime_hrs,
    fgm.ratings_count,
    fgm.reviews_count
FROM gold_data.fact_game_metrics fgm
JOIN gold_data.dim_game dg ON fgm.game_id = dg.game_id
WHERE fgm.rating > 0
AND fgm.game_id IN (
    SELECT fgg2.game_id FROM gold_data.fact_game_genre fgg2
    JOIN gold_data.dim_genre dgn ON fgg2.genre_id = dgn.genre_id
    WHERE dgn.genre_name LIKE '${inputs.genre.value}'
)
AND fgm.game_id IN (
    SELECT fgp2.game_id FROM gold_data.fact_game_platform fgp2
    JOIN gold_data.dim_platform dp ON fgp2.platform_id = dp.platform_id
    WHERE dp.platform_name LIKE '${inputs.platform.value}'
)
AND COALESCE(dg.esrb_name, 'Not Rated') LIKE '${inputs.esrb.value}'
ORDER BY fgm.rating DESC, fgm.ratings_count DESC
LIMIT 100
```

<DataTable data={top_games} search=true rows=20/>
