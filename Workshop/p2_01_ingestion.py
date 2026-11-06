import os
import psycopg2
from dotenv import load_dotenv

# 1. Credenciales desde el .env
load_dotenv()
DB_HOST = os.getenv("PG_HOST")
DB_PORT = os.getenv("PG_PORT")
DB_NAME = os.getenv("PG_DB")
DB_USER = os.getenv("PG_USER")
DB_PASS = os.getenv("PG_PASS")

CSV_FILE = "jovenes_adultos_actividad_fisica.csv"

# 2. Tabla con tipos estrictos y restricciones.
#    Los pulsos admiten NULL (el CSV trae valores faltantes y el profiling los reporta);
#    las demas columnas son obligatorias.
DDL = """
    CREATE TABLE fitness_stats (
        id                  SERIAL PRIMARY KEY,
        nombre              VARCHAR(50)  NOT NULL,
        apellido            VARCHAR(50)  NOT NULL,
        sexo                VARCHAR(6)   NOT NULL CHECK (sexo IN ('Male', 'Female')),
        altura_cm           NUMERIC(5,2) NOT NULL CHECK (altura_cm BETWEEN 100 AND 250),
        peso_kg             NUMERIC(5,2) NOT NULL CHECK (peso_kg BETWEEN 20 AND 300),
        prueba_cooper_km    NUMERIC(4,2) NOT NULL CHECK (prueba_cooper_km BETWEEN 0.5 AND 5),
        pulso_reposo_ppm    NUMERIC(4,1) CHECK (pulso_reposo_ppm BETWEEN 30 AND 120),
        pulso_actividad_ppm NUMERIC(4,1) CHECK (pulso_actividad_ppm BETWEEN 60 AND 250),
        CHECK (pulso_actividad_ppm >= pulso_reposo_ppm)
    );
"""

# 3. COPY con lista de columnas: 'id' se genera solo y el orden coincide con el CSV
COPY_SQL = """
    COPY fitness_stats (nombre, apellido, sexo, altura_cm, peso_kg,
                        prueba_cooper_km, pulso_reposo_ppm, pulso_actividad_ppm)
    FROM STDIN WITH (FORMAT CSV, HEADER)
"""

print("--- Ingesta en PostgreSQL (tipos estrictos y restricciones) ---")
conn = None
cur = None
try:
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS,
    )
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS fitness_stats;")
    cur.execute(DDL)
    conn.commit()
    print("✓ Tabla fitness_stats creada.")

    with open(CSV_FILE, "r", encoding="utf-8") as f:
        cur.copy_expert(COPY_SQL, f)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM fitness_stats;")
    print(f"✓ Datos cargados: {cur.fetchone()[0]} registros en fitness_stats.")

except Exception as e:
    print("✗ Error en PostgreSQL:", e)
    if conn:
        conn.rollback()
finally:
    if cur:
        cur.close()
    if conn:
        conn.close()
