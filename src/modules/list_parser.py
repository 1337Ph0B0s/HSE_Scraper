from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup


@dataclass
class ListItem:
    """
    Representa un registro “semilla” extraído desde una página del listado de HSE.

    `ListItem` corresponde a una fila del listado (notice_list.asp) y contiene:
    - el identificador del notice (`notice_number`)
    - la URL absoluta a la ficha de detalle (`detail_url`)
    - campos resumen mostrados en la tabla del listado (recipient, notice_type, issue_date, etc.)

    Este objeto NO es la fila final del dataset. Su propósito es:
    1) Proveer la lista de notices a procesar.
    2) Aportar campos resumen que se integrarán con los del detalle para construir `NoticeRecord`.

    En el pipeline:
    - `parse_list_page()` devuelve una lista de `ListItem`.
    - Por cada `ListItem`, se visita `detail_url` y se completa el resto de variables.

    Attributes:
        notice_number: Identificador único del notice (clave primaria del dataset).
        detail_url: URL absoluta a la página de detalle (`notice_details.asp`).
        recipient: Nombre del receptor (empresa/entidad) según el listado.
        notice_type: Tipo de notice según el listado (resumen).
        issue_date: Fecha de emisión según el listado (formato DD/MM/YYYY).
        local_authority: Autoridad local según el listado.
        main_activity: Actividad principal (puede incluir “código - etiqueta”) según el listado.
    """
    notice_number: str
    detail_url: str
    recipient: str
    notice_type: str
    issue_date: str
    local_authority: str
    main_activity: str


def parse_total_pages(html: str) -> int:

    """
    Extrae el número total de páginas del listado.

    El listado incluye un texto de estado del estilo: ``Showing Page 1 of 3055``.
    Esta función busca ese patrón y devuelve el total de páginas (por ejemplo, 3055).

    Args:
        html: HTML completo de la página del listado.

    Returns:
        Número total de páginas detectado.

    Raises:
        ValueError: Si no se encuentra el patrón esperado.
    """

    m = re.search(r"Showing\s+Page\s+\d+\s+of\s+(\d+)", html, flags=re.IGNORECASE)
    if not m:
        raise ValueError("No pude detectar el número total de páginas (formato inesperado).")
    return int(m.group(1))


def _find_results_table(soup: BeautifulSoup):
    """
        Localiza la tabla HTML que contiene el listado de resultados (notices).

        Esta función busca de forma robusta la tabla "principal" del listado, evitando
        depender de IDs o clases que podrían cambiar. Para ello inspecciona todas las
        etiquetas `<table>` y devuelve la primera cuyo texto contiene un conjunto mínimo
        de encabezados esperados del dataset:

        - "Notice Number"
        - "Recipient"
        - "Issue Date"
        - "Local Authority"

        Criterio de diseño:
        - Robustez ante cambios menores en el HTML (p.ej., wrappers, estilos).
        - Evitar seleccionar tablas auxiliares (cabeceras, menús, pie de página).

        Parameters
        ----------
        soup : bs4.BeautifulSoup
            Documento HTML ya parseado con BeautifulSoup.

        Returns
        -------
        bs4.element.Tag | None
            La etiqueta `<table>` que corresponde al listado de notices, o `None` si no se
            encontró ninguna tabla que cumpla el criterio.

        Notes
        -----
        - El método se basa en coincidencia de texto. Si el sitio cambia los nombres de
          los encabezados, se debe actualizar el conjunto de keywords.
        - Si existieran varias tablas con esos encabezados, esta función devolverá la primera.
          En ese escenario se recomienda reforzar el criterio (por ejemplo, verificando el
          número de columnas o la presencia de enlaces a `notice_details.asp`).
        """
    for table in soup.find_all("table"):
        txt = table.get_text(" ", strip=True)
        if ("Notice Number" in txt and "Recipient" in txt and "Issue Date" in txt and "Local Authority" in txt):
            return table
    return None


def parse_list_page(html: str, page_url: str) -> List[ListItem]:

    """
    Parsea una página del listado de notices y extrae los registros visibles (10 por página, aprox.).

    Esta función recibe el HTML de una página de listado (`notice_list.asp?PN=X...`),
    localiza la tabla principal de resultados (mediante `_find_results_table`) y, para
    cada fila válida, extrae:

    - `notice_number` (identificador de la notice)
    - `detail_url` (URL absoluta a la ficha de detalle `notice_details.asp`)
    - columnas resumen del listado: `recipient`, `notice_type`, `issue_date`,
      `local_authority`, `main_activity`

    El objetivo es construir una colección de items "semilla" que luego serán enriquecidos
    en la fase de scraping del detalle (página individual) para completar el dataset.

    Parameters
    ----------
    html : str
        HTML crudo de la página de listado.
    page_url : str
        URL de la página actual del listado. Se usa como base para convertir enlaces
        relativos a detalle en URLs absolutas.

    Returns
    -------
    List[ListItem]
        Lista de elementos (uno por notice encontrada) con el identificador y la URL de detalle
        más los campos resumen del listado.

    Raises
    ------
    ValueError
        Si no se encuentra la tabla de resultados esperada o si la estructura HTML no coincide
        con el patrón previsto.

    Notes
    -----
    - La función ignora filas que no contienen un enlace a `notice_details.asp` (cabeceras u otras tablas).
    - Si el sitio cambia el número/orden de columnas, se deberá ajustar el mapeo de índices `tds[i]`.
    - `notice_number` se normaliza eliminando espacios para mantener consistencia de claves.
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