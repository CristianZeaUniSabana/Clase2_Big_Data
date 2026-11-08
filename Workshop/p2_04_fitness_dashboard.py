import duckdb
import pandas as pd

PARQUET_IN = "fitness_enriched.parquet"

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

# Categorias de condicion fisica segun VO2 max (CASE WHEN):
#   Low < 30 | Average entre 30 y 40 | High > 40
TIERS_CTE = f"""
    WITH tiers AS (
        SELECT
            sexo,
            bmi,
            CASE
                WHEN vo2_max < 30  THEN 'Low'
                WHEN vo2_max <= 40 THEN 'Average'
                ELSE 'High'
            END AS nivel_fitness
        FROM read_parquet('{PARQUET_IN}')
    )
"""

# Detalle: una fila por sexo y nivel
LONG_QUERY = TIERS_CTE + """
    SELECT
        sexo,
        nivel_fitness,
        COUNT(*)           AS n_individuos,
        ROUND(AVG(bmi), 2) AS bmi_promedio
    FROM tiers
    GROUP BY sexo, nivel_fitness
    ORDER BY sexo,
             CASE nivel_fitness WHEN 'Low' THEN 1 WHEN 'Average' THEN 2 ELSE 3 END
"""

# Fitness Dashboard: agregacion condicional + pivot (una fila por sexo, columnas por nivel)
DASHBOARD_QUERY = TIERS_CTE + """
    SELECT
        sexo,
        COUNT(*)                                                    AS total,
        CAST(SUM(CASE WHEN nivel_fitness = 'Low'     THEN 1 ELSE 0 END) AS INTEGER)  AS n_low,
        CAST(SUM(CASE WHEN nivel_fitness = 'Average' THEN 1 ELSE 0 END) AS INTEGER)  AS n_average,
        CAST(SUM(CASE WHEN nivel_fitness = 'High'    THEN 1 ELSE 0 END) AS INTEGER)  AS n_high,
        ROUND(AVG(CASE WHEN nivel_fitness = 'Low'     THEN bmi END), 2) AS bmi_low,
        ROUND(AVG(CASE WHEN nivel_fitness = 'Average' THEN bmi END), 2) AS bmi_average,
        ROUND(AVG(CASE WHEN nivel_fitness = 'High'    THEN bmi END), 2) AS bmi_high,
        ROUND(AVG(bmi), 2)                                          AS bmi_promedio_total
    FROM tiers
    GROUP BY sexo
    ORDER BY sexo
"""

con = None
try:
    con = duckdb.connect()

    df_long = con.execute(LONG_QUERY).df()
    print("--- Detalle por sexo y nivel ---")
    print(df_long.to_string(index=False))

    df_dashboard = con.execute(DASHBOARD_QUERY).df()
    print("\n--- Fitness Dashboard ---")
    print(df_dashboard.to_string(index=False))
    print(f"\nTotal de individuos categorizados: {int(df_dashboard['total'].sum())}")

except Exception as e:
    print("✗ Error en DuckDB:", e)
finally:
    if con:
        con.close()
