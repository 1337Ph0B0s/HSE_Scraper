from __future__ import annotations

import argparse

from src.modules.config import DEFAULT_MAX_DELAY, DEFAULT_MIN_DELAY, DEFAULT_USER_AGENT
from src.modules.pipeline import run


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Scraper de avisos (notices) de HSE (listado -> detalle) con reanudación mediante SQLite."
    )
    p.add_argument(
        "--db",
        default="data/processed/hse_notices.sqlite",
        help="Archivo SQLite para checkpoint/reanudación."
    )
    p.add_argument(
        "--out",
        default="data/processed/hse_notices.csv",
        help="Archivo CSV de salida."
    )
    p.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="User-Agent con email de contacto real."
    )
    p.add_argument(
        "--min-delay",
        type=float,
        default=DEFAULT_MIN_DELAY,
        help="Segundos mínimos de espera entre solicitudes."
    )
    p.add_argument(
        "--max-delay",
        type=float,
        default=DEFAULT_MAX_DELAY,
        help="Segundos máximos de espera entre solicitudes."
    )
    p.add_argument(
        "--start-page",
        type=int,
        default=1,
        help="Número de página inicial."
    )
    p.add_argument(
        "--pages",
        type=int,
        default=5,
        help="Si no se usa --all, número de páginas a scrapear."
    )
    p.add_argument(
        "--all",
        action="store_true",
        help="Scrapear hasta la última página (usar con cuidado)."
    )
    p.add_argument(
        "--commit-every",
        type=int,
        default=25,
        help="Hacer commit en SQLite cada N registros."
    )
    """
    Define y parsea los argumentos de línea de comandos (CLI) del scraper.

    Esta función centraliza la interfaz de ejecución del proyecto para facilitar:
    - Reproducibilidad (misma configuración = mismo scraping).
    - Ajuste de parámetros sin modificar código (delays, rango de páginas, salida, etc.).
    - Buenas prácticas de scraping responsable (User-Agent identificable y rate limiting).

    Argumentos principales
    ----------------------
    --db : ruta al archivo SQLite usado como checkpoint/reanudación.
    --out : ruta al CSV final exportado desde SQLite.
    --user-agent : encabezado HTTP User-Agent (debe incluir contacto y propósito académico).
    --min-delay / --max-delay : intervalo de pausas aleatorias entre peticiones (rate limiting).
    --start-page : página inicial del listado (útil para reanudar manualmente).
    --pages : número de páginas a procesar en modo parcial (si no se usa --all).
    --all : procesa hasta la última página detectada del listado.
    --commit-every : frecuencia de commits en SQLite para minimizar pérdida de progreso.

    Returns
    -------
    argparse.Namespace
        Estructura con los valores parseados para ser consumidos por `main()` y el pipeline.

    Notes
    -----
    - `parse_args()` no ejecuta scraping; solo define la configuración.
    - La validación de coherencia (p. ej. `max_delay >= min_delay`) se realiza en `main()`.
    """
    return p.parse_args()


def main() -> None:
    """
    Punto de entrada principal del programa (CLI).

    Flujo:

    1. Leer la configuración desde la línea de comandos con `parse_args()`.
    2. Validar coherencia básica de parámetros (por ejemplo, `max_delay >= min_delay`).
    3. Ejecutar el pipeline `run()` (listado → detalle), persistiendo en SQLite y exportando CSV.

    Notas:

    - `main()` no implementa la lógica de scraping; delega en `src.modules.pipeline`.
    - La configuración se controla desde el CLI para facilitar reproducibilidad.
    """
    args = parse_args()
    if args.max_delay < args.min_delay:
        raise ValueError("--max-delay must be >= --min-delay")

    run(
        db_path=args.db,
        out_csv=args.out,
        user_agent=args.user_agent,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        start_page=args.start_page,
        pages=args.pages,
        scrape_all=args.all,
        commit_every=args.commit_every,
    )


if __name__ == "__main__":
    main()