README.TXT — Práctica 1 (M2.851) — Web Scraping + Dataset (HSE Notices)
===============================================================================

1. Descripción general
-------------------------------------------------------------------------------
Este proyecto implementa un pipeline de web scraping para construir un dataset
estructurado (CSV) a partir del registro público de “Enforcement Notices” de HSE
(Health and Safety Executive, Reino Unido).

El scraping se realiza en dos pasos:
  (1) LISTADO (notice_list.asp): páginas paginadas con ~10 registros por página.
  (2) DETALLE (notice_details.asp): ficha individual del notice con campos ampliados.

El resultado es un dataset (CSV) apto para análisis posterior (limpieza, EDA,
segmentación, correlaciones, ANOVA, etc.), con trazabilidad (URL y timestamp de
extracción) y reanudación mediante SQLite.

-------------------------------------------------------------------------------
2. Fuente de datos
-------------------------------------------------------------------------------
Sitio web: HSE Public Notices Register (UK)
Base URL (listado):
https://resources.hse.gov.uk/notices/notices/notice_list.asp?PN=1&ST=N&rdoNType=&NT=&SN=F&EO=LIKE&SF=RN&SV=&SO=DNIS

Cada fila del listado contiene un enlace a una página de detalle:
notice_details.asp?... (con campos completos del notice)

-------------------------------------------------------------------------------
3. Estructura del proyecto
-------------------------------------------------------------------------------
Estructura recomendada (Opción 1: estilo PEC/UOC):

src/
  main.py
  __init__.py
  modules/
    __init__.py
    config.py
    http_client.py
    list_parser.py
    detail_parser.py
    storage.py
    pipeline.py

tests/
  test_list_parser.py
  test_detail_parser.py

data/
  processed/
    (CSV y SQLite generados)

Archivos clave:
- src/main.py:
    Punto de entrada CLI (parsea argumentos, valida y llama al pipeline).
- src/modules/pipeline.py:
    Orquestador del scraping (listado -> detalle), persistencia incremental y export CSV.
- src/modules/storage.py:
    SQLiteStore para checkpoint/reanudación y exportación.
- src/modules/detail_parser.py:
    Parser del detalle basado en tablas HTML (celda izquierda=label, derecha=valor).
- src/modules/list_parser.py:
    Parser del listado y cálculo del total de páginas.

-------------------------------------------------------------------------------
4. Requisitos e instalación
-------------------------------------------------------------------------------
Se recomienda usar un entorno virtual (venv).

Instalación (desde la terminal del proyecto):
  pip install -r requirements.txt

Dependencias principales:
- requests
- beautifulsoup4
- lxml
- pandas
- tqdm

(Para desarrollo opcional: pytest, pylint, sphinx)

-------------------------------------------------------------------------------
5. Ejecución (CLI)
-------------------------------------------------------------------------------
El programa se ejecuta mediante:
  python -m src.main [opciones]

Opciones disponibles:
--db            Ruta del archivo SQLite (checkpoint/reanudación).
--out           Ruta del CSV final a exportar.
--user-agent    User-Agent identificable (se recomienda incluir email real).
--min-delay     Segundos mínimos entre peticiones.
--max-delay     Segundos máximos entre peticiones.
--start-page    Página inicial del listado (útil para reanudar manualmente).
--pages         Nº de páginas a scrapear en modo parcial (si no se usa --all).
--all           Procesa hasta la última página disponible (usar con cuidado).
--commit-every  Commit a SQLite cada N registros.

Ejemplo 1 — Prueba rápida (3 páginas ≈ 30 registros):
  python -m src.main --pages 3 ^
    --out data/processed/hse_sample.csv ^
    --db  data/processed/hse_sample.sqlite

Ejemplo 2 — Ajustar velocidad (más rápido):
  python -m src.main --pages 10 --min-delay 0.8 --max-delay 1.6 ^
    --out data/processed/hse_10p.csv --db data/processed/hse_10p.sqlite

Ejemplo 3 — Scraping completo (hasta última página):
  python -m src.main --all --min-delay 1.2 --max-delay 2.5 ^
    --out data/processed/hse_full.csv --db data/processed/hse_full.sqlite

-------------------------------------------------------------------------------
6. Scraping responsable (rate limiting y User-Agent)
-------------------------------------------------------------------------------
- El scraper aplica pausas aleatorias (“jitter”) entre peticiones mediante
  min-delay y max-delay.
- Se recomienda un User-Agent con propósito y contacto (uso académico).
- La sesión HTTP está configurada con reintentos/backoff para errores transitorios
  (p. ej. 429/5xx). Si se recibe 403, el proceso aborta (no se intenta bypass).

Recomendación práctica:
- Para un dataset de práctica, suele ser suficiente con 300–1000 registros.
- El scraping completo (miles de páginas + decenas de miles de detalles) puede
  tardar muchas horas/días.

-------------------------------------------------------------------------------
7. Persistencia y reanudación (SQLiteStore)
-------------------------------------------------------------------------------
El progreso se guarda incrementalmente en SQLite:
- Tabla "notices": 1 registro por notice_number (PRIMARY KEY) guardado como JSON.
- Tabla "errors": log de errores por URL para análisis posterior sin detener el pipeline.

Importante:
- El CSV final se exporta al FINAL del proceso. Si se interrumpe con Ctrl+C,
  el CSV puede no reflejar el progreso. El progreso real queda en la base SQLite.

Cómo verificar cuántos registros hay en SQLite:
  python -c "import sqlite3; con=sqlite3.connect('data/processed/hse_sample.sqlite'); print(con.execute('select count(*) from notices').fetchone()[0])"

Cómo exportar manualmente lo acumulado:
  (Se puede ejecutar de nuevo el scraper para que exporte al final o exportar con un script propio.)

Reanudar manualmente:
  python -m src.main --all --start-page 97 --min-delay 1.2 --max-delay 2.5 ^
    --out data/processed/hse_full.csv --db data/processed/hse_full.sqlite

-------------------------------------------------------------------------------
8. Dataset y diccionario de variables
-------------------------------------------------------------------------------
El dataset exportado se describe en:
  data_dictionary.md

Incluye:
- Clave primaria: notice_number
- Origen de columnas: listado (summary), detalle, derivadas (p. ej. country)
- Tipología recomendada: nominal, temporal, texto
- Notas de limpieza y validación

-------------------------------------------------------------------------------
9. Validaciones recomendadas
-------------------------------------------------------------------------------
- Unicidad: notice_number debe ser único.
- Fechas: validar formato DD/MM/YYYY y convertir a tipo fecha en análisis.
- Nulos: esperables en campos HSE (p. ej. hse_area).
- Texto: normalizar espacios; mantener address como bloque (con separador “|” o espacio).
- Consistencia: si notice_type detail es nulo, usar notice_type_summary; idem local_authority.

-------------------------------------------------------------------------------
10. Licencia y atribución (publicación del dataset)
-------------------------------------------------------------------------------
Contains public sector information published by the Health and Safety Executive and licensed under the Open Government
Licence v3.0.

-------------------------------------------------------------------------------
11. Contacto / reproducibilidad
-------------------------------------------------------------------------------
Para reproducibilidad, se recomienda guardar junto al CSV:
- Fecha/hora de extracción (scraped_at_utc por registro).
- Comando exacto de ejecución (CLI).
- Versión de dependencias (requirements.txt).
- data_dictionary.md

Fin del README.TXT
===============================================================================