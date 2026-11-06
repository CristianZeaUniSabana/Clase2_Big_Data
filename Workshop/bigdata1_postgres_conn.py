import psycopg2
import pandas as pd
import os
from dotenv import load_dotenv

# 1. Load environment variables from .env file
load_dotenv()

# 2. Database connection settings
DB_HOST = os.getenv("PG_HOST")
DB_PORT = os.getenv("PG_PORT")
DB_NAME = os.getenv("PG_DB")
DB_USER = os.getenv("PG_USER")
DB_PASS = os.getenv("PG_PASS")

csv_file = "jovenes_adultos_actividad_fisica.csv"
parquet_file = "fitness_stats.parquet"

print("--- Part 1: Setting up PostgreSQL (OLTP) ---")
try:
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME, 
        user=DB_USER, password=DB_PASS
    )
    cur = conn.cursor()

    # Create table
    cur.execute("DROP TABLE IF EXISTS fitness_stats;")
    cur.execute("""
        CREATE TABLE fitness_stats (
            nombre VARCHAR(50), apellido VARCHAR(50), sexo VARCHAR(10),
            altura_cm FLOAT, peso_kg FLOAT, prueba_cooper_km FLOAT,
            pulso_reposo_ppm FLOAT, pulso_actividad_ppm FLOAT
        );
    """)
    conn.commit()

    # Load CSV into Postgres
    with open(csv_file, "r", encoding="utf-8") as file:
        cur.copy_expert("COPY fitness_stats FROM STDIN WITH (FORMAT CSV, HEADER)", file)
    conn.commit()
    print("✓ Data successfully loaded into PostgreSQL 'fitness_stats' table.")

except Exception as e:
    print("✗ PostgreSQL Error:", e)
    if conn: conn.rollback()
finally:
    if cur: cur.close()
    if conn: conn.close()

print("\n--- Part 2: Exporting to Parquet (Big Data Format) ---")
try:
    # Read CSV with Pandas
    df = pd.read_csv(csv_file)
    
    # Data Engineering Best Practice: Standardize column names 
    # (Removes spaces/parentheses to match DB schema and prevent SQL quoting issues later)
    df.columns = [
        'nombre', 'apellido', 'sexo', 'altura_cm', 'peso_kg', 
        'prueba_cooper_km', 'pulso_reposo_ppm', 'pulso_actividad_ppm'
    ]
    
    # Save as Parquet
    df.to_parquet(parquet_file, index=False, engine='pyarrow')
    print(f"✓ Successfully exported {len(df)} records to '{parquet_file}'.")
    
except Exception as e:
    print("✗ Parquet Export Error:", e)