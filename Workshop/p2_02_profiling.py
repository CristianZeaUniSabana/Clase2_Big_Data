import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_HOST = os.getenv("PG_HOST")
DB_PORT = os.getenv("PG_PORT")
DB_NAME = os.getenv("PG_DB")
DB_USER = os.getenv("PG_USER")
DB_PASS = os.getenv("PG_PASS")

# Columnas fisiologicas a perfilar
COLUMNS = [
    "altura_cm",
    "peso_kg",
    "prueba_cooper_km",
    "pulso_reposo_ppm",
    "pulso_actividad_ppm",
]

# COUNT(*) cuenta todas las filas; COUNT(col) solo las no nulas -> la resta son los faltantes
PROFILING_QUERY = "\nUNION ALL\n".join(
    f"""SELECT '{c}' AS columna,
               COUNT(*) AS total_registros,
               COUNT(*) - COUNT({c}) AS valores_faltantes,
               ROUND(100.0 * (COUNT(*) - COUNT({c})) / COUNT(*), 2) AS pct_faltantes
        FROM fitness_stats"""
    for c in COLUMNS
)

print("--- Data profiling: fitness_stats ---")
conn = None
cur = None
try:
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS,
    )
    cur = conn.cursor()
    cur.execute(PROFILING_QUERY)
    rows = cur.fetchall()

    print(f"\nTotal de registros: {rows[0][1]}\n")
    print(f"{'columna':<22}{'faltantes':>10}{'% faltantes':>14}")
    print("-" * 46)
    for columna, total, faltantes, pct in rows:
        print(f"{columna:<22}{faltantes:>10}{float(pct):>13.2f}%")

except Exception as e:
    print("✗ Error en el profiling:", e)
finally:
    if cur:
        cur.close()
    if conn:
        conn.close()
