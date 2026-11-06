import duckdb
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_HOST = os.getenv("PG_HOST")
DB_PORT = os.getenv("PG_PORT")
DB_NAME = os.getenv("PG_DB")
DB_USER = os.getenv("PG_USER")
DB_PASS = os.getenv("PG_PASS")

parquet_file = "fitness_stats.parquet"

print("--- DuckDB Analytics (OLAP) ---")
duck_con = duckdb.connect()

# ==========================================
# SCENARIO A: Querying the Parquet File
# ==========================================
print(f"\n1. Querying '{parquet_file}' directly with DuckDB:")
print("(Zero-ETL: DuckDB queries the columnar file directly from disk)")

parquet_query = f"""
    SELECT 
        sexo, 
        COUNT(*) AS total_records,
        ROUND(AVG(altura_cm), 2) AS avg_height_cm,
        ROUND(AVG(peso_kg), 2) AS avg_weight_kg,
        ROUND(AVG(prueba_cooper_km), 2) AS avg_cooper_km
    FROM read_parquet('{parquet_file}')
    GROUP BY sexo
"""
# .df() instantly converts the result to a Pandas DataFrame
print(duck_con.execute(parquet_query).df())


# ==========================================
# SCENARIO B: Querying Dockerized PostgreSQL
# ==========================================
print("\n2. Querying Dockerized PostgreSQL directly with DuckDB:")
print("(DuckDB acts as a compute engine, pulling data from Postgres on the fly)")

# Install and load the Postgres extension
duck_con.execute("INSTALL postgres_scanner;")
duck_con.execute("LOAD postgres_scanner;")

# Attach the Dockerized Postgres DB using the .env credentials
pg_conn_string = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASS}"
duck_con.execute(f"ATTACH '{pg_conn_string}' AS pg_db (TYPE POSTGRES);")

pg_query = """
    SELECT 
        sexo, 
        COUNT(*) AS total_records,
        ROUND(AVG(altura_cm), 2) AS avg_height_cm,
        ROUND(AVG(peso_kg), 2) AS avg_weight_kg,
        ROUND(AVG(prueba_cooper_km), 2) AS avg_cooper_km
    FROM pg_db.public.fitness_stats
    GROUP BY sexo
"""
print(duck_con.execute(pg_query).df())

# Clean up
duck_con.close()
print("\n✓ DuckDB connections closed.")