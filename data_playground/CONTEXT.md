# General context
Here youll create all the files to develop a proper ETL data process with a medallion architecture focus (bronze, silver and gold layers). 
- Always use logging package instead of print to give logs.
- Youll work with parquet files.
- The raw data will be obtain from RAWG public API.
- Use utils.py functions as needed.
- set a main() as usual in all files.
- move the parquet files into the respective data layer in azurite.
- Do not save parquet files in local, all save it in Azurite medallion layers.

## Extraction
Create a data_ingestion.py file to contain next functions:
- Raw data pull from RAWG public API.
- Parquet serialization (nested files to JSON strings).
- Extract 400 pages of 40 lines each from the API
- Include a retry/backoff logic to deal with the 20req/s.
The final file .parquet call it bronze_data.

## bronze to silver
Create a bronze_to_silver.py file to contain next functions:
- 1st, Explode the nested data in the bronze file (1NF) does not matter if it multiply the amount of lines of the final silver file.
- With pyspark do not use USDF only use pyspark native functions.
- Empty, NaN, none, turn it to null.
- Duplicate records verification, if duplicates exist, delete them.
- Some columns will be deleted, ask for which to delete (specially the ones in nested cells - dictionaries). Give recomendations and data metadata for better visualization.
- Create multiple normilized tables (fact and dim), with respective unique and fixed ids, the output of all files should be 1NF, 2NF and 3NF.
- The created files .parquet call them based on the table which represents (example: silver_dim_games.parquet).

## silver to gold
Create a silver_to_gold.py file to contain/execute next functions:
- Denormilized the data of the silver layer but just if its necessary to create a easy star schema for the dashboard/visualization step, for this, evaluate the context of visualization folder firts.
- Use pyspark native functions only.
- The final files .parquet call them based on the table which represents (example: gold_dim_games.parquet)

At the end add the created files into the claude.md file directory structure diagram (ONLY MAIN FILES, do not add subfiles).