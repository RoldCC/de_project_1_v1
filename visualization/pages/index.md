---
title: RAWG Games Dashboard
---

# RAWG Games Analytics

A star-schema view of **{kpis[0].total_games}** video games from the RAWG public database.

---

## Filters

```sql year_options
SELECT DISTINCT CAST(DATE_PART('year', released)::INTEGER AS VARCHAR) AS release_year
FROM gold_data.gold_games
WHERE released IS NOT NULL
ORDER BY release_year DESC
```

```sql genre_options
SELECT DISTINCT genre_name FROM gold_data.gold_game_genres ORDER BY genre_name
```

```sql platform_options
SELECT DISTINCT platform_name FROM gold_data.gold_game_platforms ORDER BY platform_name
```

```sql esrb_options
SELECT DISTINCT esrb_name FROM gold_data.gold_games ORDER BY esrb_name
```

<Dropdown name=year_release data={year_options} value=release_year label=release_year title="Release Year">
    <DropdownOption value="%" valueLabel="All Years"/>
</Dropdown>

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
    COUNT(DISTINCT g.game_id)                                            AS total_games,
    ROUND(MEDIAN(CASE WHEN g.rating   > 0 THEN g.rating   END), 2)      AS median_rating,
    ROUND(MEDIAN(CASE WHEN g.playtime > 0 THEN g.playtime END), 1)      AS median_playtime_hrs,
    COUNT(DISTINCT gg.genre_name)                                        AS total_genres,
    COUNT(DISTINCT gp.platform_name)                                     AS total_platforms
FROM gold_data.gold_games g
LEFT JOIN gold_data.gold_game_genres    gg ON g.game_id = gg.game_id
LEFT JOIN gold_data.gold_game_platforms gp ON g.game_id = gp.game_id
WHERE g.game_id IN (SELECT game_id FROM gold_data.gold_game_genres    WHERE genre_name    LIKE '${inputs.genre.value}')
AND   g.game_id IN (SELECT game_id FROM gold_data.gold_game_platforms WHERE platform_name LIKE '${inputs.platform.value}')
AND   g.esrb_name LIKE '${inputs.esrb.value}'
AND   COALESCE(CAST(DATE_PART('year', g.released)::INTEGER AS VARCHAR), '%') LIKE '${inputs.year_release.value}'
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
-- filtered by platform + esrb + year (genre chart is not self-filtered)
SELECT
    gg.genre_name,
    COUNT(DISTINCT gg.game_id) AS game_count
FROM gold_data.gold_game_genres gg
WHERE gg.game_id IN (SELECT game_id FROM gold_data.gold_game_platforms WHERE platform_name LIKE '${inputs.platform.value}')
AND   gg.game_id IN (
    SELECT g.game_id FROM gold_data.gold_games g
    WHERE g.esrb_name LIKE '${inputs.esrb.value}'
    AND COALESCE(CAST(DATE_PART('year', g.released)::INTEGER AS VARCHAR), '%') LIKE '${inputs.year_release.value}'
)
GROUP BY gg.genre_name
ORDER BY game_count DESC
LIMIT 10
```

```sql top_platforms
-- filtered by genre + esrb + year (platform chart is not self-filtered)
SELECT
    gp.platform_name,
    COUNT(DISTINCT gp.game_id) AS game_count
FROM gold_data.gold_game_platforms gp
WHERE gp.game_id IN (SELECT game_id FROM gold_data.gold_game_genres WHERE genre_name LIKE '${inputs.genre.value}')
AND   gp.game_id IN (
    SELECT g.game_id FROM gold_data.gold_games g
    WHERE g.esrb_name LIKE '${inputs.esrb.value}'
    AND COALESCE(CAST(DATE_PART('year', g.released)::INTEGER AS VARCHAR), '%') LIKE '${inputs.year_release.value}'
)
GROUP BY gp.platform_name
ORDER BY game_count DESC
LIMIT 10
```

<Grid cols=2>

<BarChart
    data={top_genres}
    x=genre_name
    y=game_count
    swapXY=true
    name=genre
    title="Top 10 Genres"
    xAxisTitle="Games"
    colorPalette={['#236aa4']}
/>

<BarChart
    data={top_platforms}
    x=platform_name
    y=game_count
    swapXY=true
    name=platform
    title="Top 10 Platforms"
    xAxisTitle="Games"
    colorPalette={['#45a1bf']}
/>

</Grid>

---

## Platform vs Genre

```sql genre_platform_matrix
SELECT
    gg.genre_name,
    gp.platform_name,
    COUNT(DISTINCT gg.game_id) AS game_count
FROM gold_data.gold_game_genres gg
JOIN gold_data.gold_game_platforms gp ON gg.game_id = gp.game_id
WHERE gg.game_id IN (SELECT game_id FROM gold_data.gold_game_genres    WHERE genre_name    LIKE '${inputs.genre.value}')
AND   gg.game_id IN (SELECT game_id FROM gold_data.gold_game_platforms WHERE platform_name LIKE '${inputs.platform.value}')
AND   gg.game_id IN (
    SELECT g.game_id FROM gold_data.gold_games g
    WHERE g.esrb_name LIKE '${inputs.esrb.value}'
    AND COALESCE(CAST(DATE_PART('year', g.released)::INTEGER AS VARCHAR), '%') LIKE '${inputs.year_release.value}'
)
AND gg.genre_name IN (
    SELECT genre_name FROM (
        SELECT genre_name, COUNT(DISTINCT game_id) AS cnt
        FROM gold_data.gold_game_genres
        GROUP BY genre_name ORDER BY cnt DESC LIMIT 10
    )
)
AND gp.platform_name IN (
    SELECT platform_name FROM (
        SELECT platform_name, COUNT(DISTINCT game_id) AS cnt
        FROM gold_data.gold_game_platforms
        GROUP BY platform_name ORDER BY cnt DESC LIMIT 8
    )
)
GROUP BY gg.genre_name, gp.platform_name
ORDER BY gg.genre_name, game_count DESC
```

<BarChart
    data={genre_platform_matrix}
    x=genre_name
    y=game_count
    series=platform_name
    swapXY=true
    type=stacked
    title="Games by Genre and Platform (Top 10 Genres × Top 8 Platforms)"
    xAxisTitle="Games"
/>

---

## Release Trends

```sql games_per_year
SELECT
    DATE_PART('year', g.released)::INTEGER AS release_year,
    COUNT(DISTINCT g.game_id)              AS game_count
FROM gold_data.gold_games g
WHERE g.released IS NOT NULL
AND DATE_PART('year', g.released) < 2029
AND g.game_id IN (SELECT game_id FROM gold_data.gold_game_genres    WHERE genre_name    LIKE '${inputs.genre.value}')
AND g.game_id IN (SELECT game_id FROM gold_data.gold_game_platforms WHERE platform_name LIKE '${inputs.platform.value}')
AND g.esrb_name LIKE '${inputs.esrb.value}'
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

## Rating Distribution

```sql rating_dist
SELECT
    (ROUND(g.rating * 2) / 2)::DECIMAL(3,1) AS rating_bucket,
    COUNT(DISTINCT g.game_id)               AS game_count
FROM gold_data.gold_games g
WHERE g.rating > 0
AND g.game_id IN (SELECT game_id FROM gold_data.gold_game_genres    WHERE genre_name    LIKE '${inputs.genre.value}')
AND g.game_id IN (SELECT game_id FROM gold_data.gold_game_platforms WHERE platform_name LIKE '${inputs.platform.value}')
AND g.esrb_name LIKE '${inputs.esrb.value}'
AND COALESCE(CAST(DATE_PART('year', g.released)::INTEGER AS VARCHAR), '%') LIKE '${inputs.year_release.value}'
GROUP BY rating_bucket
ORDER BY rating_bucket
```

<BarChart
    data={rating_dist}
    x=rating_bucket
    y=game_count
    title="Rating Distribution (0.5-step buckets)"
    xAxisTitle="Rating"
    yAxisTitle="Games"
    colorPalette={['#f4b548']}
/>

---

## Rating by Genre and Platform

```sql rating_by_genre_platform
SELECT
    gg.genre_name,
    gp.platform_name,
    ROUND(MEDIAN(CASE WHEN g.rating > 0 THEN g.rating END), 2) AS median_rating
FROM gold_data.gold_games g
JOIN gold_data.gold_game_genres    gg ON g.game_id = gg.game_id
JOIN gold_data.gold_game_platforms gp ON g.game_id = gp.game_id
WHERE g.game_id IN (SELECT game_id FROM gold_data.gold_game_genres    WHERE genre_name    LIKE '${inputs.genre.value}')
AND   g.game_id IN (SELECT game_id FROM gold_data.gold_game_platforms WHERE platform_name LIKE '${inputs.platform.value}')
AND   g.esrb_name LIKE '${inputs.esrb.value}'
AND   COALESCE(CAST(DATE_PART('year', g.released)::INTEGER AS VARCHAR), '%') LIKE '${inputs.year_release.value}'
AND gg.genre_name IN (
    SELECT genre_name FROM (
        SELECT genre_name, COUNT(DISTINCT game_id) AS cnt
        FROM gold_data.gold_game_genres
        GROUP BY genre_name ORDER BY cnt DESC LIMIT 8
    )
)
AND gp.platform_name IN (
    SELECT platform_name FROM (
        SELECT platform_name, COUNT(DISTINCT game_id) AS cnt
        FROM gold_data.gold_game_platforms
        GROUP BY platform_name ORDER BY cnt DESC LIMIT 5
    )
)
GROUP BY gg.genre_name, gp.platform_name
HAVING MEDIAN(CASE WHEN g.rating > 0 THEN g.rating END) IS NOT NULL
ORDER BY gg.genre_name, gp.platform_name
```

<BarChart
    data={rating_by_genre_platform}
    x=genre_name
    y=median_rating
    series=platform_name
    swapXY=true
    type=grouped
    title="Median Rating by Genre and Platform (Top 8 Genres × Top 5 Platforms)"
    xAxisTitle="Median Rating"
    colorPalette={['#236aa4','#45a1bf','#46a485','#f4b548','#8f3d56']}
/>

---

## Rating vs Playtime

```sql rating_vs_playtime
SELECT
    ROUND(g.rating, 2)  AS rating,
    g.playtime          AS playtime_hrs,
    g.esrb_name         AS esrb
FROM gold_data.gold_games g
WHERE g.rating > 0
AND g.playtime > 0
AND g.game_id IN (SELECT game_id FROM gold_data.gold_game_genres    WHERE genre_name    LIKE '${inputs.genre.value}')
AND g.game_id IN (SELECT game_id FROM gold_data.gold_game_platforms WHERE platform_name LIKE '${inputs.platform.value}')
AND g.esrb_name LIKE '${inputs.esrb.value}'
AND COALESCE(CAST(DATE_PART('year', g.released)::INTEGER AS VARCHAR), '%') LIKE '${inputs.year_release.value}'
```

<ScatterPlot
    data={rating_vs_playtime}
    x=playtime_hrs
    y=rating
    series=esrb
    title="Rating vs Playtime by ESRB"
    xAxisTitle="Playtime (hrs)"
    yAxisTitle="Rating"
/>

---

## Store Coverage

```sql top_stores
SELECT
    gs.store_name,
    COUNT(DISTINCT gs.game_id) AS game_count
FROM gold_data.gold_game_stores gs
WHERE gs.game_id IN (SELECT game_id FROM gold_data.gold_game_genres    WHERE genre_name    LIKE '${inputs.genre.value}')
AND   gs.game_id IN (SELECT game_id FROM gold_data.gold_game_platforms WHERE platform_name LIKE '${inputs.platform.value}')
AND   gs.game_id IN (
    SELECT g.game_id FROM gold_data.gold_games g
    WHERE g.esrb_name LIKE '${inputs.esrb.value}'
    AND COALESCE(CAST(DATE_PART('year', g.released)::INTEGER AS VARCHAR), '%') LIKE '${inputs.year_release.value}'
)
GROUP BY gs.store_name
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
    g.name                                         AS game,
    DATE_PART('year', g.released)::INTEGER         AS year,
    g.esrb_name                                    AS esrb,
    ROUND(g.rating, 2)                             AS rating,
    g.playtime                                     AS playtime_hrs,
    g.ratings_count,
    g.reviews_count
FROM gold_data.gold_games g
WHERE g.rating > 0
AND g.game_id IN (SELECT game_id FROM gold_data.gold_game_genres    WHERE genre_name    LIKE '${inputs.genre.value}')
AND g.game_id IN (SELECT game_id FROM gold_data.gold_game_platforms WHERE platform_name LIKE '${inputs.platform.value}')
AND g.esrb_name LIKE '${inputs.esrb.value}'
AND COALESCE(CAST(DATE_PART('year', g.released)::INTEGER AS VARCHAR), '%') LIKE '${inputs.year_release.value}'
ORDER BY g.rating DESC, g.ratings_count DESC
LIMIT 100
```

<DataTable data={top_games} search=true rows=20/>
