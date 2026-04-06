# Práctica 1 (M2.851 Tipología y ciclo de vida de los datos) — Web Scraping + Dataset (HSE Notices)

## 1. Descripción general
Este proyecto implementa un pipeline de **web scraping** para construir un **dataset estructurado (CSV)** a partir del registro público de **HSE (Health and Safety Executive, UK)**: *Enforcement Notices*.

El scraping se realiza en dos etapas:

1) **LISTADO** (`notice_list.asp`): páginas paginadas con ~10 registros por página.  
2) **DETALLE** (`notice_details.asp`): ficha individual del notice con campos ampliados.

El resultado es un dataset apto para análisis posterior (limpieza, EDA, segmentación, correlaciones, ANOVA, etc.), con:
- **Trazabilidad** (URL de detalle y timestamp de extracción)
- **Reanudación** (checkpoint en SQLite)
- **Exportación** a CSV (UTF-8)

---

## 2. Fuente de datos
**Sitio web:** HSE Public Notices Register (UK)

**URL base (listado):**
```
https://resources.hse.gov.uk/notices/notices/notice_list.asp?PN=1&ST=N&rdoNType=&NT=&SN=F&EO=LIKE&SF=RN&SV=&SO=DNIS
```

Cada fila del listado enlaza a una ficha:
- `notice_details.asp?...` (con campos completos del notice)

---

## 3. Estructura del proyecto
Estructura estilo PEC/UOC (Opción 1):

```text
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
```

### Responsabilidad de módulos
- `src/main.py`  
  Punto de entrada CLI (parsea argumentos, valida y llama al pipeline).

- `src/modules/pipeline.py`  
  Orquestador del scraping (listado → detalle), persistencia incremental y export CSV.

- `src/modules/storage.py`  
  `SQLiteStore` para checkpoint/reanudación y exportación.

- `src/modules/detail_parser.py`  
  Parser del detalle **basado en tablas HTML** (celda izquierda = label, derecha = valor).  
  **Importante:** `description` y `address` se extraen como **bloques completos** de la celda derecha.

- `src/modules/list_parser.py`  
  Parser del listado y cálculo del total de páginas.

---

## 4. Requisitos e instalación
Se recomienda usar un entorno virtual (`venv`).

### Instalación
```bash
pip install -r requirements.txt
```

**Dependencias principales**
- `requests`
- `beautifulsoup4`
- `lxml`
- `pandas`
- `tqdm`

**Dev (opcional)**
- `pytest`
- `pylint`
- `sphinx`

---

## 5. Ejecución (CLI)

Ejecuta el proyecto con:

```bash
python -m src.main [opciones]
```

### Opciones disponibles
- `--db` : Ruta del archivo SQLite (checkpoint/reanudación).  
- `--out` : Ruta del CSV final a exportar.  
- `--user-agent` : User-Agent identificable (recomendado incluir email real).  
- `--min-delay` : Segundos mínimos entre peticiones.  
- `--max-delay` : Segundos máximos entre peticiones.  
- `--start-page` : Página inicial del listado (útil para reanudar).  
- `--pages` : Nº de páginas a scrapear en modo parcial (si no se usa `--all`).  
- `--all` : Procesa hasta la última página disponible (usar con cuidado).  
- `--commit-every` : Commit a SQLite cada N registros.

### Ejemplo 1 — Prueba rápida (3 páginas ≈ 30 registros)
```bash
python -m src.main --pages 3 \
  --out data/processed/hse_sample.csv \
  --db  data/processed/hse_sample.sqlite
```

### Ejemplo 2 — Ajustar velocidad (más rápido)
```bash
python -m src.main --pages 10 --min-delay 0.8 --max-delay 1.6 \
  --out data/processed/hse_10p.csv --db data/processed/hse_10p.sqlite
```

### Ejemplo 3 — Scraping completo (hasta última página)
```bash
python -m src.main --all --min-delay 1.2 --max-delay 2.5 \
  --out data/processed/hse_full.csv --db data/processed/hse_full.sqlite
```

---

## 6. Scraping responsable (rate limiting y User-Agent)
- El scraper aplica pausas aleatorias (**jitter**) entre peticiones usando `--min-delay` y `--max-delay`.
- Se recomienda un `--user-agent` con propósito y contacto (uso académico).
- La sesión HTTP está configurada con reintentos/backoff para errores transitorios (p. ej. 429/5xx).
- Si se recibe **403**, el proceso aborta (no se intenta bypass).

**Recomendación práctica**
- Para un dataset de práctica suele bastar con **300–1000 registros**.
- El scraping completo puede tardar muchas horas/días.

---

## 7. Persistencia y reanudación (SQLiteStore)
El progreso se guarda incrementalmente en SQLite:
- Tabla `notices`: 1 registro por `notice_number` (PK), almacenado como JSON.
- Tabla `errors`: log de errores por URL sin detener el pipeline.

### Importante sobre Ctrl+C
El **CSV se exporta al final**.  
Si interrumpes con `Ctrl+C`, el CSV puede quedarse con el último export previo.  
El progreso real queda en la base SQLite (`--db`).

### Contar filas acumuladas en SQLite
```bash
python -c "import sqlite3; con=sqlite3.connect('data/processed/hse_sample.sqlite'); print(con.execute('select count(*) from notices').fetchone()[0])"
```

### Reanudar desde una página específica
Si el proceso se cortó en PN=96, puedes continuar desde 97:

```bash
python -m src.main --all --start-page 97 --min-delay 1.2 --max-delay 2.5 \
  --out data/processed/hse_full.csv --db data/processed/hse_full.sqlite
```

---

## 8. Dataset y diccionario de variables
El dataset exportado se describe en:

- `data_dictionary.md`

Incluye:
- clave primaria (`notice_number`)
- origen de columnas (listado / detalle / derivadas)
- tipología recomendada (nominal, temporal, texto)
- notas de limpieza y validación

---

## 9. Validaciones recomendadas
- **Unicidad:** `notice_number` debe ser único.  
- **Fechas:** validar `DD/MM/YYYY` y convertir a fecha en análisis.  
- **Nulos:** esperables en campos HSE (p. ej. `hse_area`).  
- **Texto:** normalizar espacios; mantener `address` como bloque (separador `|` o espacio).  
- **Consistencia:** si `notice_type` del detalle es nulo, usar `notice_type_summary` (fallback); idem `local_authority`.

---

## 10. Licencia y atribución (publicación del dataset)
El dataset se deriva de un registro público del Reino Unido. Al publicar en Zenodo:
- Citar HSE como fuente.
- Incluir una nota de atribución coherente con el marco de reutilización del sector público (OGL) cuando aplique (ej.: “Contains public sector information published by the Health and Safety Executive…”).

---

## 11. Reproducibilidad (recomendado)
Guardar junto al CSV:
- comando exacto de ejecución (CLI)
- fecha de extracción (`scraped_at_utc`)
- `requirements.txt`
- `data_dictionary.md`
