# Claude Notes — de_project_1_v3

=========================================================
Task Log
=========================================================

| Task | Timestamp beginning | Timestamp ending | Claude notes |
|------|---------------------|------------------|--------------|
| Project scaffolding (venv, .env, .gitignore, requirements.txt) | 2026-05-24 17:28 | 2026-05-24 17:35 | — |
| Task 1 — data_environment_structure (docker-compose.yml, utils.py) | 2026-05-24 17:35 | 2026-05-24 17:44 | Challenge: Azurite `AuthorizationFailure` on first run — the well-known account key in .env was truncated (40 bytes vs. the correct 64 bytes). |
|  |  |  | Solution: Extracted the correct key from the SDK's own constants via `parse_connection_str('UseDevelopmentStorage=true')`, then updated .env and .env.example. |
|  |  |  | Improvement: Always derive the Azurite default key programmatically from the installed SDK rather than hardcoding it, since the key differs between SDK versions. |
| Task 2a — data_ingestion.py | 2026-05-24 17:55 | 2026-05-24 17:55 | — |
| Task 2b — bronze_to_silver.py | 2026-05-24 17:55 | 2026-05-24 18:16 | Challenge 1: Used Python UDFs for JSON parsing — violates CONTEXT.md constraint "no UDFs, only native PySpark functions". |
|  |  |  | Solution: Replaced all UDFs with `F.from_json` + `F.transform` + `F.get_json_object` native PySpark functions. |
|  |  |  | Challenge 2: Spark `[CANNOT_DETERMINE_TYPE]` error when creating DataFrame from pandas — caused by 100%-null columns (`user_game`, `clip`) with no inferable type. |
|  |  |  | Solution: Applied `pandas_df.dropna(axis=1, how='all')` before passing to Spark. |
|  |  |  | Improvement: Always read CONTEXT.md constraints (no UDF rule) before writing transformation code, not after a failed run. |
| Task 2c — silver_to_gold.py | 2026-05-24 18:16 | 2026-05-24 18:18 | Challenge: First silver design used array columns which violate 1NF. Required a redesign of bronze_to_silver to cross-explode genre × platform × store. |
|  |  |  | Solution: Exploded all 3 array columns creating 331,695 rows (20× multiplication from 16,000). Gold tables use DISTINCT selects to recover clean many-to-many relationships. |
|  |  |  | Improvement: For multi-dimensional 1NF explosion, document the expected row multiplication factor upfront so downstream queries know to use DISTINCT. |

=========================================================
System Improvement Points
=========================================================

Based on CLAUDE.md and CLAUDE_LAW.md review:

1. **Package version pinning:** CLAUDE.md lists packages without versions. Pinning exact versions in requirements.txt from the start avoids environment drift across machines — especially critical for PySpark/great-expectations which have tight inter-dependency constraints.

2. **Venv not in .gitignore by default:** The project has no .gitignore yet. Committing a venv is a common mistake; .gitignore should be the first file created.

3. **great-expectations + PySpark compatibility:** These two packages have known version conflicts depending on the Python version. Worth validating the installed combination works before building pipeline logic on top.

4. **Missing docker-compose / Azurite config reference in CLAUDE.md:** The identity says the stack uses Azurite and Docker, but CLAUDE.md has no mention of where docker-compose files live or how Azurite is configured. This should be tracked in `data_environment_structure/CONTEXT.md`.

5. **Date format yyyy-MMM-dd (e.g. 2026-May-24):** This is non-standard for most tooling (Spark, DuckDB, Parquet). Worth confirming this applies only to display/reporting columns and not to partition keys or filter columns, where ISO 8601 (yyyy-MM-dd) is strongly preferred.
