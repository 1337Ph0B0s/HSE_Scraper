from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup


@dataclass
class ListItem:
    notice_number: str
    detail_url: str
    recipient: str
    notice_type: str
    issue_date: str
    local_authority: str
    main_activity: str


def parse_total_pages(html: str) -> int:
    """
    Extrae: 'Showing Page 1 of 3055'
    """
    m = re.search(r"Showing\s+Page\s+\d+\s+of\s+(\d+)", html, flags=re.IGNORECASE)
    if not m:
        raise ValueError("No pude detectar el número total de páginas (formato inesperado).")
    return int(m.group(1))


def _find_results_table(soup: BeautifulSoup):
    # Encuentra la tabla que contiene los encabezados esperados
    for table in soup.find_all("table"):
        txt = table.get_text(" ", strip=True)
        if ("Notice Number" in txt and "Recipient" in txt and "Issue Date" in txt and "Local Authority" in txt):
            return table
    return None


def parse_list_page(html: str, page_url: str) -> List[ListItem]:
    """
    Parseo del listado (tabla) y extracción de la URL a detalle.
    """
    soup = BeautifulSoup(html, "lxml")
    table = _find_results_table(soup)
    if table is None:
        raise ValueError("No se encontró la tabla de resultados en la página de listado.")

    items: List[ListItem] = []
    for tr in table.find_all("tr"):
        a = tr.find("a", href=re.compile(r"notice_details\.asp", re.I))
        if not a:
            continue

        tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if len(tds) < 6:
            continue

        notice_number = re.sub(r"\s+", "", a.get_text(strip=True))
        detail_url = urljoin(page_url, a["href"])

        items.append(
            ListItem(
                notice_number=notice_number,
                detail_url=detail_url,
                recipient=tds[1],
                notice_type=tds[2],
                issue_date=tds[3],
                local_authority=tds[4],
                main_activity=tds[5],
            )
        )

    return items