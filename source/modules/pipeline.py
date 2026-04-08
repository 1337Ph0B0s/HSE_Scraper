from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional
from urllib.parse import urlsplit, parse_qs, urlencode, urlunsplit

import requests
from tqdm import tqdm

from source.modules.config import LIST_URL, DEFAULT_HEADERS, DEFAULT_TIMEOUT
from source.modules.http_client import fetch_html, make_session
from source.modules.list_parser import parse_list_page, parse_total_pages
from source.modules.detail_parser import parse_detail_page
from source.modules.storage import SQLiteStore

@dataclass
class NoticeRecord:
    """
    Representa una fila del dataset final de HSE Enforcement Notices.

    Se construye combinando:

    - Campos del LISTADO (notice_list.asp): resumen por fila.
    - Campos del DETALLE (notice_details.asp): información ampliada.

    Convenciones:

    - Campos con sufijo `_summary` provienen del listado.
    - Los demás campos provienen del detalle (o se completan con fallback).
    - Un campo puede ser `None` si la celda del sitio está vacía.
    """
    notice_number: str
    detail_url: str

    recipient_name_summary: Optional[str] = None
    notice_type_summary: Optional[str] = None
    issue_date_summary: Optional[str] = None
    local_authority_summary: Optional[str] = None
    main_activity_summary: Optional[str] = None

    served_date: Optional[str] = None
    notice_type: Optional[str] = None
    description: Optional[str] = None
    compliance_date: Optional[str] = None
    revised_compliance_date: Optional[str] = None
    result: Optional[str] = None

    address: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    local_authority: Optional[str] = None
    industry: Optional[str] = None
    main_activity_code: Optional[str] = None
    main_activity_label: Optional[str] = None
    location_type: Optional[str] = None

    hse_group: Optional[str] = None
    hse_directorate: Optional[str] = None
    hse_area: Optional[str] = None
    hse_division: Optional[str] = None

    scraped_at_utc: Optional[str] = None


def _polite_sleep(min_delay: float, max_delay: float) -> None:

    """
    Aplica una pausa aleatoria (jitter) entre peticiones para realizar scraping responsable.

    La función introduce un retardo uniforme aleatorio en el intervalo [min_delay, max_delay]
    antes de continuar con la siguiente petición (por ejemplo, entre páginas del listado o
    entre páginas de detalle). Este patrón reduce el riesgo de sobrecargar el servidor y
    evita un ritmo de acceso determinista típico de bots.

    Parameters
    ----------
    min_delay : float
        Tiempo mínimo de espera (en segundos).
    max_delay : float
        Tiempo máximo de espera (en segundos). Debe ser >= min_delay.

    Returns
    -------
    None

    Notes
    -----
    - El retardo se aplica tanto a peticiones del listado como del detalle (según la implementación
      del pipeline).
    - Un intervalo demasiado bajo puede aumentar el riesgo de bloqueos o errores HTTP (p.ej. 429/403).
    - Un intervalo demasiado alto incrementa el tiempo total de ejecución; por ello se recomienda
      ajustar estos parámetros desde la línea de comandos en función del tamaño del scraping.
    """
    time.sleep(random.uniform(min_delay, max_delay))


def _build_list_page_url(base_url: str, page: int) -> str:

    """
    Construye la URL de una página del listado modificando únicamente el parámetro `PN`.

    El listado de HSE se pagina mediante el parámetro de query `PN` (Page Number).
    Esta función toma una URL base (que ya contiene el resto de parámetros de filtrado/orden)
    y devuelve una nueva URL equivalente pero con `PN=<page>`.

    Esto permite iterar sobre el listado de forma determinista (PN=1..N) sin alterar
    el resto de parámetros (ST, SN, EO, SF, SV, SO, etc.), garantizando que el scraping
    recorre exactamente el mismo conjunto y orden de resultados.

    Parameters
    ----------
    base_url : str
        URL base del listado (incluye querystring). Ejemplo:
        `...notice_list.asp?PN=1&ST=N&SN=F&EO=LIKE&SF=RN&SV=&SO=DNIS`
    page : int
        Número de página a construir (>= 1).

    Returns
    -------
    str
        URL completa del listado con el parámetro `PN` actualizado al valor indicado.

    Raises
    ------
    ValueError
        Si `page` es menor que 1 (recomendado validar antes de llamar).

    Notes
    -----
    - Se preservan todos los parámetros existentes en la URL, y solo se modifica `PN`.
    - La implementación usa `urllib.parse` para evitar errores al manipular strings a mano.
    """

    parts = urlsplit(base_url)
    qs = parse_qs(parts.query)
    qs["PN"] = [str(page)]
    new_query = urlencode(qs, doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


def run(
    db_path: str,
    out_csv: str,
    user_agent: str,
    min_delay: float,
    max_delay: float,
    start_page: int = 1,
    pages: Optional[int] = None,
    scrape_all: bool = False,
    commit_every: int = 25,
) -> int:
    """
    Ejecuta el pipeline completo: listado → detalle → SQLite → exportación CSV.

    Pasos principales:

    1. Descarga la primera página del listado y calcula el total con `parse_total_pages()`.
    2. Itera por páginas del listado (`PN`) para extraer items semilla con `parse_list_page()`.
    3. Visita cada página de detalle y extrae campos con `parse_detail_page()`.
    4. Guarda incrementalmente en SQLite (reanudable) y exporta CSV al finalizar.

    Scraping responsable:

    - Aplica pausas aleatorias entre peticiones (`min_delay`, `max_delay`).
    - Usa User-Agent identificable (uso académico).
    - Registra errores por URL en la tabla `errors` sin detener el proceso.

    Args:
        db_path: Ruta del archivo SQLite (checkpoint).
        out_csv: Ruta del CSV final.
        user_agent: Valor del User-Agent.
        min_delay: Pausa mínima entre peticiones (segundos).
        max_delay: Pausa máxima entre peticiones (segundos).
        start_page: Página inicial para comenzar o reanudar.
        pages: Número de páginas si no se usa `scrape_all`.
        scrape_all: Si True, procesa hasta la última página.
        commit_every: Commit a SQLite cada N registros.

    Returns:
        Número de filas exportadas al CSV.
    """
    headers = dict(DEFAULT_HEADERS)
    headers["User-Agent"] = user_agent

    session = make_session()
    store = SQLiteStore(db_path=db_path)

    # Detectar total
    first_url = _build_list_page_url(LIST_URL, 1)
    first_html = fetch_html(session, first_url, headers=headers, timeout=DEFAULT_TIMEOUT)
    total_pages = parse_total_pages(first_html)

    if scrape_all:
        end_page = total_pages
    else:
        if pages is None:
            pages = 5
        end_page = min(total_pages, start_page + pages - 1)

    print(f"Procesando páginas: {start_page}..{end_page} (total disponible: {total_pages})")

    pending_commits = 0

    try:
        for page in tqdm(range(start_page, end_page + 1), desc="List pages"):
            page_url = _build_list_page_url(LIST_URL, page)
            html = fetch_html(session, page_url, headers=headers, timeout=DEFAULT_TIMEOUT)

            items = parse_list_page(html, page_url)
            _polite_sleep(min_delay, max_delay)

            for it in tqdm(items, desc=f"Details p{page}", leave=False):
                if store.has_notice(it.notice_number):
                    continue

                try:
                    detail_html = fetch_html(session, it.detail_url, headers=headers, timeout=DEFAULT_TIMEOUT)
                    detail = parse_detail_page(detail_html)

                    rec = NoticeRecord(
                        notice_number=it.notice_number,
                        detail_url=it.detail_url,
                        recipient_name_summary=it.recipient,
                        notice_type_summary=it.notice_type,
                        issue_date_summary=it.issue_date,
                        local_authority_summary=it.local_authority,
                        main_activity_summary=it.main_activity,
                    )

                    rec.served_date = detail.get("served_date")
                    rec.notice_type = detail.get("notice_type") or rec.notice_type_summary
                    rec.description = detail.get("description")
                    rec.compliance_date = detail.get("compliance_date")
                    rec.revised_compliance_date = detail.get("revised_compliance_date")
                    rec.result = detail.get("result")

                    rec.address = detail.get("address")
                    rec.country = detail.get("country")
                    rec.region = detail.get("region")
                    rec.local_authority = detail.get("local_authority") or rec.local_authority_summary
                    rec.industry = detail.get("industry")
                    rec.main_activity_code = detail.get("main_activity_code")
                    rec.main_activity_label = detail.get("main_activity_label") or rec.main_activity_summary
                    rec.location_type = detail.get("location_type")

                    rec.hse_group = detail.get("hse_group")
                    rec.hse_directorate = detail.get("hse_directorate")
                    rec.hse_area = detail.get("hse_area")
                    rec.hse_division = detail.get("hse_division")

                    rec.scraped_at_utc = datetime.now(timezone.utc).isoformat()

                    store.upsert_notice(rec)
                    pending_commits += 1

                    if pending_commits >= commit_every:
                        store.commit()
                        pending_commits = 0

                except Exception as e:
                    store.log_error(
                        url=it.detail_url,
                        error=str(e),
                        created_at=datetime.now(timezone.utc).isoformat(),
                    )
                    store.commit()

                _polite_sleep(min_delay, max_delay)

        # Commit final
        store.commit()
        n = store.export_to_csv(out_csv)
        print(f"CSV exportado: {out_csv} ({n} filas)")
        return n

    finally:
        store.close()