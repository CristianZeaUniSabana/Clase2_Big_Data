import os
import duckdb
from dotenv import load_dotenv

# Credenciales desde el .env
load_dotenv()
DB_HOST = os.getenv("PG_HOST")
DB_PORT = os.getenv("PG_PORT")
DB_NAME = os.getenv("PG_DB")
DB_USER = os.getenv("PG_USER")
DB_PASS = os.getenv("PG_PASS")

PARQUET_FILE = "fitness_stats.parquet"

QUERY_TEMPLATE = """
    SELECT
        sexo,
        ROUND(AVG(prueba_cooper_km), 2) AS promedio_cooper_km,
        ROUND(AVG(peso_kg / POWER(altura_cm / 100, 2)), 2) AS promedio_imc
    FROM {source}
    GROUP BY sexo
    ORDER BY sexo
"""

con = duckdb.connect()  # base de datos en memoria

# ==========================================
# SCENARIO A: Querying the Parquet File
# ==========================================
print("--- A. DuckDB sobre el archivo Parquet ---")
query_parquet = QUERY_TEMPLATE.format(source=f"read_parquet('{PARQUET_FILE}')")
df_parquet = con.execute(query_parquet).df()
print(df_parquet)

# ==========================================
# SCENARIO B: Querying Dockerized PostgreSQL
# ==========================================
print("\n--- B. DuckDB sobre PostgreSQL (Docker) ---")
con.execute("INSTALL postgres_scanner;")
con.execute("LOAD postgres_scanner;")

pg_conn_string = (
    f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} "
    f"user={DB_USER} password={DB_PASS}"
)
con.execute(f"ATTACH '{pg_conn_string}' AS pg_db (TYPE POSTGRES, READ_ONLY);")

query_pg = QUERY_TEMPLATE.format(source="pg_db.public.fitness_stats")
df_pg = con.execute(query_pg).df()
print(df_pg)

con.close()