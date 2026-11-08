import os
import duckdb
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_HOST = os.getenv("PG_HOST")
DB_PORT = os.getenv("PG_PORT")
DB_NAME = os.getenv("PG_DB")
DB_USER = os.getenv("PG_USER")
DB_PASS = os.getenv("PG_PASS")

PARQUET_IN = "fitness_enriched.parquet"
TARGET_TABLE = "fitness_metrics"

# Tabla analitica: id + metricas calculadas en DuckDB + nivel de fitness
WRITEBACK_QUERY = f"""
    CREATE TABLE pg_db.public.{TARGET_TABLE} AS
    SELECT
        id,
        CAST(bmi AS DECIMAL(5,2))      AS bmi,
        CAST(vo2_max AS DECIMAL(5,2))  AS vo2_max,
        CAST(hrr AS DECIMAL(5,1))      AS hrr,
        CAST(rank_vo2_max AS INTEGER)  AS rank_vo2_max,
        CASE
            WHEN vo2_max < 30  THEN 'Low'
            WHEN vo2_max <= 40 THEN 'Average'
            ELSE 'High'
        END AS fitness_tier
    FROM read_parquet('{PARQUET_IN}')
"""

# Restricciones de la tabla analitica (se aplican en PostgreSQL tras la carga)
CONSTRAINTS_SQL = f"""
    ALTER TABLE {TARGET_TABLE}
        ADD PRIMARY KEY (id),
        ADD CONSTRAINT chk_fitness_tier CHECK (fitness_tier IN ('Low', 'Average', 'High')),
        ADD CONSTRAINT chk_rank_positive CHECK (rank_vo2_max >= 1);
"""

VERIFY_QUERY = f"""
    SELECT s.nombre, s.apellido, s.sexo, m.bmi, m.vo2_max, m.hrr, m.rank_vo2_max, m.fitness_tier
    FROM fitness_stats s
    JOIN {TARGET_TABLE} m USING (id)
    ORDER BY m.rank_vo2_max, s.sexo
    LIMIT 5
"""

# --- Paso 1: DuckDB escribe la tabla analitica en PostgreSQL ---
print("--- ELT: DuckDB -> PostgreSQL ---")
con = None
try:
    con = duckdb.connect()
    con.execute("INSTALL postgres_scanner;")
    con.execute("LOAD postgres_scanner;")
    pg_conn_string = (
        f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} "
        f"user={DB_USER} password={DB_PASS}"
    )
    # Sin READ_ONLY: ahora DuckDB necesita escribir
    con.execute(f"ATTACH '{pg_conn_string}' AS pg_db (TYPE POSTGRES);")

    con.execute(f"DROP TABLE IF EXISTS pg_db.public.{TARGET_TABLE};")
    con.execute(WRITEBACK_QUERY)
    n = con.execute(f"SELECT COUNT(*) FROM pg_db.public.{TARGET_TABLE}").fetchone()[0]
    print(f"✓ Tabla {TARGET_TABLE} creada en PostgreSQL con {n} registros.")
except Exception as e:
    print("✗ Error en DuckDB:", e)
    raise SystemExit(1)
finally:
    if con:
        con.close()

# --- Paso 2: restricciones y verificacion en PostgreSQL ---
conn = None
cur = None
try:
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS,
    )
    cur = conn.cursor()
    cur.execute(CONSTRAINTS_SQL)
    conn.commit()
    print("✓ Restricciones aplicadas (llave primaria y CHECK).")

    cur.execute(VERIFY_QUERY)
    print("\nVerificacion (fitness_stats + fitness_metrics), top 5 por ranking:")
    print(f"{'nombre':<9}{'apellido':<10}{'sexo':<8}{'bmi':>7}{'vo2_max':>9}{'hrr':>7}{'rank':>6}  tier")
    for nombre, apellido, sexo, bmi, vo2, hrr, rank, tier in cur.fetchall():
        hrr_txt = "NULL" if hrr is None else f"{float(hrr):.1f}"
        print(f"{nombre:<9}{apellido:<10}{sexo:<8}{float(bmi):>7.2f}{float(vo2):>9.2f}{hrr_txt:>7}{rank:>6}  {tier}")
except Exception as e:
    print("✗ Error en PostgreSQL:", e)
    if conn:
        conn.rollback()
finally:
    if cur:
        cur.close()
    if conn:
        conn.close()
