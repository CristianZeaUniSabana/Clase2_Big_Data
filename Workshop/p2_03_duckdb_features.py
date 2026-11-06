import os
import duckdb
from dotenv import load_dotenv

load_dotenv()
DB_HOST = os.getenv("PG_HOST")
DB_PORT = os.getenv("PG_PORT")
DB_NAME = os.getenv("PG_DB")
DB_USER = os.getenv("PG_USER")
DB_PASS = os.getenv("PG_PASS")

PARQUET_OUT = "fitness_enriched.parquet"

# Metricas fisiologicas calculadas directamente en SQL.
# Los NUMERIC de PostgreSQL llegan como DECIMAL: se convierten a DOUBLE para los calculos.
# El ranking se calcula sobre el VO2 max sin redondear; el redondeo es solo de presentacion.
FEATURES_QUERY = """
    WITH metrics AS (
        SELECT
            id, nombre, apellido, sexo,
            CAST(altura_cm AS DOUBLE)           AS altura_cm,
            CAST(peso_kg AS DOUBLE)             AS peso_kg,
            CAST(prueba_cooper_km AS DOUBLE)    AS prueba_cooper_km,
            CAST(pulso_reposo_ppm AS DOUBLE)    AS pulso_reposo_ppm,
            CAST(pulso_actividad_ppm AS DOUBLE) AS pulso_actividad_ppm,
            -- IMC = peso / (altura en metros)^2
            CAST(peso_kg AS DOUBLE) / POWER(CAST(altura_cm AS DOUBLE) / 100, 2) AS bmi_raw,
            -- VO2 max estimado (formula de Cooper)
            22.351 * CAST(prueba_cooper_km AS DOUBLE) - 11.288                  AS vo2_max_raw,
            -- Reserva de frecuencia cardiaca (NULL si falta alguno de los dos pulsos)
            CAST(pulso_actividad_ppm AS DOUBLE) - CAST(pulso_reposo_ppm AS DOUBLE) AS hrr
        FROM {source}
    )
    SELECT
        id, nombre, apellido, sexo,
        altura_cm, peso_kg, prueba_cooper_km, pulso_reposo_ppm, pulso_actividad_ppm,
        ROUND(bmi_raw, 2)    AS bmi,
        ROUND(vo2_max_raw, 2) AS vo2_max,
        hrr,
        -- Ranking dentro de cada sexo, de mayor a menor VO2 max (los empates comparten puesto)
        RANK() OVER (PARTITION BY sexo ORDER BY vo2_max_raw DESC) AS rank_vo2_max
    FROM metrics
"""

con = None
try:
    con = duckdb.connect()  # base de datos en memoria

    # 1. Postgres Scanner: PostgreSQL (Docker) visible desde DuckDB
    con.execute("INSTALL postgres_scanner;")
    con.execute("LOAD postgres_scanner;")
    pg_conn_string = (
        f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} "
        f"user={DB_USER} password={DB_PASS}"
    )
    con.execute(f"ATTACH '{pg_conn_string}' AS pg_db (TYPE POSTGRES, READ_ONLY);")
    print("✓ PostgreSQL conectado desde DuckDB.")

    # 2. Dataset enriquecido -> Parquet
    query = FEATURES_QUERY.format(source="pg_db.public.fitness_stats")
    con.execute(f"COPY ({query}) TO '{PARQUET_OUT}' (FORMAT PARQUET);")
    print(f"✓ Dataset enriquecido exportado a '{PARQUET_OUT}'.")

    # 3. Verificacion leyendo el Parquet generado
    check = con.execute(f"SELECT * FROM read_parquet('{PARQUET_OUT}')").df()
    print(f"\nFilas: {check.shape[0]} | Columnas: {check.shape[1]}")
    print(f"HRR sin valor (pulsos faltantes): {check['hrr'].isna().sum()}")

    cols = ["nombre", "apellido", "sexo", "bmi", "vo2_max", "hrr", "rank_vo2_max"]
    for sexo in ["Female", "Male"]:
        top = check[check["sexo"] == sexo].sort_values("rank_vo2_max").head(5)
        print(f"\nTop 5 VO2 max - {sexo}:")
        print(top[cols].to_string(index=False))

except Exception as e:
    print("✗ Error en DuckDB:", e)
finally:
    if con:
        con.close()
