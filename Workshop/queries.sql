-- ============================================
-- 1. UNPIVOT: fitness_stats (ancha) -> fitness_long (larga)
-- ============================================
DROP TABLE IF EXISTS fitness_long;

CREATE TABLE fitness_long AS
SELECT sexo, 'altura_cm' AS indicator, altura_cm AS value
FROM fitness_stats
WHERE altura_cm IS NOT NULL

UNION ALL

SELECT sexo, 'peso_kg', peso_kg
FROM fitness_stats
WHERE peso_kg IS NOT NULL

UNION ALL

SELECT sexo, 'prueba_cooper_km', prueba_cooper_km
FROM fitness_stats
WHERE prueba_cooper_km IS NOT NULL

UNION ALL

SELECT sexo, 'pulso_reposo_ppm', pulso_reposo_ppm
FROM fitness_stats
WHERE pulso_reposo_ppm IS NOT NULL

UNION ALL

SELECT sexo, 'pulso_actividad_ppm', pulso_actividad_ppm
FROM fitness_stats
WHERE pulso_actividad_ppm IS NOT NULL;


-- ============================================
-- 2. PIVOT: fitness_long (larga) -> ancha, agregada por sexo
-- ============================================
SELECT
    sexo,
    MAX(CASE WHEN indicator = 'altura_cm'          THEN value END) AS altura_cm,
    MAX(CASE WHEN indicator = 'peso_kg'            THEN value END) AS peso_kg,
    MAX(CASE WHEN indicator = 'prueba_cooper_km'   THEN value END) AS prueba_cooper_km,
    MAX(CASE WHEN indicator = 'pulso_reposo_ppm'   THEN value END) AS pulso_reposo_ppm,
    MAX(CASE WHEN indicator = 'pulso_actividad_ppm' THEN value END) AS pulso_actividad_ppm
FROM fitness_long
GROUP BY sexo;