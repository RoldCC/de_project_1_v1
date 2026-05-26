# RAWG Games Data Pipeline

A local end-to-end data engineering project built with **Azurite**, **PySpark**, **DuckDB**, and **Evidence.dev**.  
The pipeline ingests 16,000 video games from the RAWG public API, transforms them through a medallion architecture, and serves an interactive analytics dashboard deployed to GitHub Pages.

**Live dashboard →** https://roldcc.github.io/de_project_1_v2/

---

## Architecture

```
RAWG API
   │
   ▼
Bronze Layer (Azurite)          raw JSON-serialized parquet — 16,000 games, 19 MB
   │  bronze_to_silver.py
   ▼
Silver Layer (Azurite)          8 normalized 3NF tables (dim + fact) — genre × platform × store exploded
   │  silver_to_gold.py
   ▼
Gold Layer (Azurite)            4 denormalized tables (names pre-joined, dashboard-ready)
   │  export_gold.py
   ▼
visualization/sources/gold_data/    committed parquet files read by Evidence at build time
   │  GitHub Actions (deploy.yml)
   ▼
GitHub Pages                    static Evidence.dev dashboard
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| Local blob storage | Azurite (Azure Blob emulator) via Docker |
| Ingestion | Python + requests + Azurite |
| Transformation | PySpark 4.x (native functions only — no UDFs) |
| Parquet I/O | PyArrow |
| Analytical queries | DuckDB 1.5 |
| Dashboard | Evidence.dev v40 (SvelteKit + adapter-static) |
| CI/CD | GitHub Actions → GitHub Pages |

---

## Project Structure

```
de_project_1_v3/
├── data_environment_structure/
│   ├── docker-compose.yml          Azurite container
│   └── utils.py                    Blob client helpers
├── data_playground/
│   ├── data_ingestion.py           RAWG API → bronze layer
│   ├── bronze_to_silver.py         Raw serialized-JSON → 1NF silver
│   └── silver_to_gold.py           Silver → star-schema Gold
├── visualization/
│   ├── export_gold.py              Azurite Gold → committed parquet files
│   ├── evidence.config.yaml        Evidence datasource config
│   ├── package.json
│   ├── pages/
│   │   └── index.md                Dashboard (SQL + Evidence components)
│   └── sources/
│       └── gold_data/              Committed parquet files + DuckDB source
├── .github/
│   └── workflows/
│       └── deploy.yml              Build + deploy to GitHub Pages
├── .env.example
├── requirements.txt
└── claude_notes.md
```

---

## Gold Schema (denormalized — dashboard-ready)

Silver holds 8 normalized 3NF tables (dim_games, dim_genre, dim_platform, dim_store + 4 fact bridge tables).  
Gold joins names in at the silver→gold step so dashboard queries need no extra lookups.

| Table | Rows | Columns |
|-------|------|---------|
| `gold_games` | 15,072 | game_id, name, released, esrb_name, rating, playtime, ratings_count, reviews_text_count, reviews_count, added |
| `gold_game_genres` | 39,988 | game_id, genre_name |
| `gold_game_platforms` | 40,650 | game_id, platform_name |
| `gold_game_stores` | 31,017 | game_id, store_name |

---

## Dashboard Features

- **Filters:** Release Year, Genre, Platform, ESRB Rating — all fully cross-filtering
- **KPIs:** total games, median rating, median playtime, genre count, platform count
- **Charts:** Genre breakdown, Platform breakdown, Platform × Genre matrix, Release timeline, Rating distribution, Rating by Genre & Platform, Rating vs Playtime scatter, Store coverage
- **Table:** Top-rated games (searchable, 100 rows)

---

## Local Setup

### Prerequisites
- Docker
- Python 3.10+
- Node.js 20+

### 1 — Start Azurite

```bash
cd data_environment_structure
docker compose up -d
```

### 2 — Python environment

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3 — Environment variables

```bash
cp .env.example .env
# Fill in RAWG_API_KEY (free at rawg.io)
# Azurite connection string is pre-filled
```

### 4 — Run the pipeline

```bash
python data_playground/data_ingestion.py
python data_playground/bronze_to_silver.py
python data_playground/silver_to_gold.py
python visualization/export_gold.py
```

### 5 — Preview the dashboard locally

```bash
cd visualization
npm install
npm run sources
npm run dev
```

### 6 — Update the live dashboard

After regenerating gold data, commit the updated parquet files and push to `main` — GitHub Actions rebuilds and deploys automatically.

```bash
git add visualization/sources/gold_data/
git commit -m "Refresh gold data"
git push
```
