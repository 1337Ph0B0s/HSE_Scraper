import re
from typing import Dict, Optional, List
from bs4 import BeautifulSoup

# Lista de naciones de Inglaterra, usadas para el parsing.
_UK_NATIONS = {"England", "Scotland", "Wales", "Northern Ireland"}


def _norm_spaces(text: str) -> str:
    """
    Normaliza espacios en un texto, colapsando whitespace repetido a un solo espacio.

    Esta función se usa para limpiar texto extraído del HTML (por ejemplo, `description`,
    encabezados o valores de celdas) donde pueden aparecer saltos de línea, tabulaciones o
    múltiples espacios consecutivos. El objetivo es producir un texto uniforme y fácil de
    almacenar/analizar, sin cambiar el contenido semántico.

    Regla:
        - Cualquier secuencia de whitespace (espacios, \\n, \\t) se reemplaza por un único
          espacio, y el resultado se recorta (`strip()`).

    Args:
        text: Texto de entrada (posiblemente con saltos de línea o espacios múltiples).

    Returns:
        Texto normalizado con espacios simples y sin espacios al inicio/final.
    """
    return re.sub(r"\s+", " ", text).strip()


def _cell_text(cell, sep: str = " ") -> Optional[str]:
    """
    Extrae el texto completo de una celda HTML (td/th) y lo normaliza para el dataset.

    Esta función está pensada para celdas "valor" en tablas del detalle, donde:
    - La etiqueta de la izquierda contiene el nombre del campo (label),
    - La celda de la derecha contiene el valor (posiblemente con saltos de línea, <br>, listas, etc.).

    El objetivo es devolver completamente el contenido textual de la celda derecha como una sola cadena,
    manteniendo una representación consistente:

    - Si `sep=" "`: une fragmentos con espacios (útil para `description`).
    - Si `sep=" | "`: preserva los saltos de línea/segmentos con un separador visible (útil para `address`).

    Si la celda está vacía (o solo contiene whitespace), devuelve `None`.

    Args:
        cell: Tag de BeautifulSoup correspondiente a la celda (td/th). Puede ser None.
        sep: Separador usado por `get_text(separator=sep)`.
             Valores típicos:
             - `" "` para texto continuo (description)
             - `" | "` para bloques multi-línea (address)

    Returns:
        El texto normalizado de la celda, o `None` si no hay contenido.

    Notes:
        - La función normaliza whitespace (múltiples espacios, saltos de línea, tabs).
        - Si `sep` incluye `|`, se normaliza también el formato alrededor de `|` para evitar
          secuencias como `"a|b"` o `"a  |   b"`.
        - No interpreta HTML semánticamente: solo extrae texto visible.
    """
    if cell is None:
        return None
    txt = cell.get_text(separator=sep, strip=True)
    if not txt:
        return None
    # Normaliza whitespace (sin destruir separadores)
    if sep == " | ":
        txt = re.sub(r"\s*\|\s*", " | ", txt)
        txt = _norm_spaces(txt)
    else:
        txt = _norm_spaces(txt)
    return txt or None


def _find_table_with_keywords(soup: BeautifulSoup, keywords: List[str]):
    """
    Localiza una tabla HTML que contenga un conjunto de palabras clave en su texto.

    Esta función recorre todas las etiquetas `<table>` del documento y devuelve la primera
    cuyo texto (normalizado) contiene todas las palabras clave indicadas. Se utiliza para
    seleccionar de forma robusta la tabla correcta en páginas donde existen varias tablas
    (por ejemplo: tabla principal del notice, tabla de "Location of Offence" y tabla de
    "HSE Details").

    Estrategia:
    - Para cada tabla, se obtiene un "blob" textual con `get_text(" ", strip=True)`.
    - Se compara en minúsculas para evitar problemas de mayúsculas/minúsculas.
    - Una tabla se considera candidata si contiene **todas** las keywords.

    Args:
        soup: Documento HTML ya parseado con BeautifulSoup.
        keywords: Lista de palabras/fragmentos de texto que deben aparecer en la tabla.
                  Ejemplos típicos:
                  - ["Notice Type", "Description", "Compliance Date", "Result"]
                  - ["Location of Offence", "Address", "Region"]
                  - ["HSE Details", "HSE Group"]

    Returns:
        La primera tabla (`bs4.element.Tag`) que cumple el criterio, o `None` si no se encuentra.

    Notes:
        - El método es robusto ante cambios leves de estructura HTML (IDs/clases).
        - Si el sitio cambia los textos de los encabezados, debe actualizarse la lista de keywords.
        - Si hubiera múltiples tablas que cumplen el criterio, se devuelve la primera; en ese caso,
          puede reforzarse el criterio (p. ej., comprobando labels específicos o presencia de filas).
    """
    for table in soup.find_all("table"):
        blob = table.get_text(" ", strip=True)
        if all(k.lower() in blob.lower() for k in keywords):
            return table
    return None


def _value_by_label(table: BeautifulSoup, label: str, sep: str = " ") -> Optional[str]:
    """
    Obtiene el valor asociado a un label dentro de una tabla HTML (celda izquierda → celda derecha).

    En las páginas de detalle de HSE, muchos campos se representan como una tabla de dos columnas:
    - La celda izquierda contiene el nombre del campo (label), por ejemplo: "Description".
    - La celda derecha contiene el valor correspondiente (que puede incluir saltos de línea o estar vacía).

    Esta función busca una celda (td/th) cuyo texto sea exactamente igual a `label` y devuelve
    el contenido textual completo de la celda inmediatamente a la derecha (next sibling),
    normalizado mediante `_cell_text()`.

    Args:
        table: Tabla HTML (`<table>`) donde se buscará el label. Puede ser `None`.
        label: Texto exacto del label tal como aparece en la celda izquierda (p. ej. "Address").
        sep: Separador para unir fragmentos al extraer el texto de la celda derecha. Usos típicos:
            - `" "` para campos de texto continuo (p. ej. `description`)
            - `" | "` para campos multi-línea (p. ej. `address`)

    Returns:
        Texto completo de la celda derecha normalizado, o `None` si:
        - `table` es `None`,
        - no se encuentra el label,
        - o la celda derecha está vacía.

    Notes:
        - La búsqueda del label es estricta (coincidencia exacta). Si el sitio cambia el texto
          del label, se debe actualizar el argumento `label`.
        - Esta función es crítica para capturar correctamente valores en celdas derechas que
          contienen múltiples líneas, y para manejar celdas vacías en secciones como "HSE Details".
    """
    if table is None:
        return None

    def is_label(tag):
        if tag.name not in ("td", "th"):
            return False
        return tag.get_text(" ", strip=True) == label

    lab = table.find(is_label)
    if not lab:
        return None

    val = lab.find_next_sibling(["td", "th"])
    return _cell_text(val, sep=sep)


def parse_detail_page(html: str) -> Dict[str, Optional[str]]:
    """
    Parsea una página de detalle de HSE (notice_details.asp) y extrae campos del dataset.

    La extracción se basa en tablas HTML con patrón "label → valor", donde el label está en la
    celda izquierda y el valor en la celda derecha. En particular, `description` y `address`
    se obtienen como el contenido completo de la celda derecha.

    :param html: HTML crudo de la página de detalle.
    :type html: str
    :return: Diccionario con los campos extraídos (strings) o `None` si la celda está vacía.
    :rtype: Dict[str, Optional[str]]
    :raises ValueError: Si no se detectan estructuras mínimas esperadas (tablas/labels).
    """
    soup = BeautifulSoup(html, "lxml")
    out: Dict[str, Optional[str]] = {}

    # 1) Encabezado (Notice N served against X on dd/mm/yyyy)
    header_text = soup.get_text(" ", strip=True)
    m = re.search(
        r"Notice\s+(\d+)\s+served against\s+(.+?)\s+on\s+(\d{2}/\d{2}/\d{4})",
        header_text,
    )
    if m:
        out["notice_number"] = m.group(1)
        out["recipient_name_detail"] = _norm_spaces(m.group(2))
        out["served_date"] = m.group(3)

    # 2) Tabla principal (Notice Type, Description, Compliance Date, Revised Compliance Date, Result)
    main_table = _find_table_with_keywords(
        soup,
        ["Notice Type", "Description", "Compliance Date", "Result"],
    )
    out["notice_type"] = _value_by_label(main_table, "Notice Type")
    # Description: toda la celda derecha (puede tener saltos) -> separador espacio
    out["description"] = _value_by_label(main_table, "Description", sep=" ")
    out["compliance_date"] = _value_by_label(main_table, "Compliance Date")
    out["revised_compliance_date"] = _value_by_label(main_table, "Revised Compliance Date")
    out["result"] = _value_by_label(main_table, "Result")

    # 3) Location of Offence (Address, Region, Local Authority, Industry, Main Activity, Type of Location)
    loc_table = _find_table_with_keywords(
        soup,
        ["Location of Offence", "Address", "Region", "Local Authority", "Industry", "Main Activity"],
    )
    # Address: toda la celda derecha -> separador " | " para conservar líneas
    out["address"] = _value_by_label(loc_table, "Address", sep=" | ")
    out["region"] = _value_by_label(loc_table, "Region")
    out["local_authority"] = _value_by_label(loc_table, "Local Authority")
    out["industry"] = _value_by_label(loc_table, "Industry")
    main_activity = _value_by_label(loc_table, "Main Activity")
    out["location_type"] = _value_by_label(loc_table, "Type of Location")

    # Heurística opcional para country: si la última línea de Address es una nación UK
    if out.get("address"):
        last = out["address"].split(" | ")[-1].strip()
        out["country"] = last if last in _UK_NATIONS else None
    else:
        out["country"] = None

    # Main Activity seguirá el patrón de este ejemplo: "41200 - CONSTRUCTION OF BUILDINGS"
    if main_activity:
        m2 = re.match(r"(\d+)\s*-\s*(.+)", main_activity)
        if m2:
            out["main_activity_code"] = m2.group(1)
            out["main_activity_label"] = _norm_spaces(m2.group(2))
        else:
            out["main_activity_label"] = main_activity
            out["main_activity_code"] = None
    else:
        out["main_activity_code"] = None
        out["main_activity_label"] = None

    # 4) HSE Details (valores a la derecha; pueden estar vacíos)
    hse_table = _find_table_with_keywords(soup, ["HSE Details", "HSE Group"])
    out["hse_group"] = _value_by_label(hse_table, "HSE Group")
    out["hse_directorate"] = _value_by_label(hse_table, "HSE Directorate")
    out["hse_area"] = _value_by_label(hse_table, "HSE Area")
    out["hse_division"] = _value_by_label(hse_table, "HSE Division")

    return out