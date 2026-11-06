import os
import psycopg2
import pandas as pd
from dotenv import load_dotenv

# 1. Load environment variables from .env file
load_dotenv()
DB_HOST = os.getenv("PG_HOST")
DB_PORT = os.getenv("PG_PORT")
DB_NAME = os.getenv("PG_DB")
DB_USER = os.getenv("PG_USER")
DB_PASS = os.getenv("PG_PASS")

CSV_FILE = "jovenes_adultos_actividad_fisica.csv"
PARQUET_FILE = "fitness_stats.parquet"

# 2. Mapeo: encabezado original del CSV -> columna limpia en snake_case
COLUMN_MAP = {
    "Nombre": "nombre",
    "Apellido": "apellido",
    "Sexo": "sexo",
    "Altura (cm)": "altura_cm",
    "Peso (kg)": "peso_kg",
    "Prueba Cooper (km)": "prueba_cooper_km",
    "Pulso en Reposo (ppm)": "pulso_reposo_ppm",
    "Pulso en Actividad (ppm)": "pulso_actividad_ppm",
}

# --- Parte 1: PostgreSQL ---
print("--- Parte 1: PostgreSQL ---")
conn = None
cur = None
try:
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS,
    )
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS fitness_stats;")
    cur.execute("""
        CREATE TABLE fitness_stats (
            nombre              VARCHAR(50),
            apellido            VARCHAR(50),
            sexo                VARCHAR(10),
            altura_cm           FLOAT,
            peso_kg             FLOAT,
            prueba_cooper_km    FLOAT,
            pulso_reposo_ppm    FLOAT,
            pulso_actividad_ppm FLOAT
        );
    """)
    conn.commit()

    with open(CSV_FILE, "r", encoding="utf-8") as f:
        cur.copy_expert(
            "COPY fitness_stats FROM STDIN WITH (FORMAT CSV, HEADER)", f
        )
    conn.commit()
    print("✓ Datos cargados en la tabla fitness_stats.")

except Exception as e:
    print("✗ Error en PostgreSQL:", e)
    if conn:
        conn.rollback()
finally:
    if cur:
        cur.close()
    if conn:
        conn.close()

# --- Parte 2: Parquet ---
print("\n--- Parte 2: Exportar a Parquet ---")
try:
    df = pd.read_csv(CSV_FILE)
    df = df.rename(columns=COLUMN_MAP)
    df.to_parquet(PARQUET_FILE, index=False, engine="pyarrow")
    print(f"✓ {len(df)} registros exportados a '{PARQUET_FILE}'.")
except Exception as e:
    print("✗ Error al exportar Parquet:", e)