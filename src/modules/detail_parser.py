import re
from typing import Dict, Optional, List
from bs4 import BeautifulSoup


_UK_NATIONS = {"England", "Scotland", "Wales", "Northern Ireland"}


def _norm_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _cell_text(cell, sep: str = " ") -> Optional[str]:
    """Extrae texto completo de una celda, respetando separador."""
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
    """Encuentra la primera tabla que contenga todas las keywords en su texto."""
    for table in soup.find_all("table"):
        blob = table.get_text(" ", strip=True)
        if all(k.lower() in blob.lower() for k in keywords):
            return table
    return None


def _value_by_label(table: BeautifulSoup, label: str, sep: str = " ") -> Optional[str]:
    """
    Busca una celda con el texto EXACTO del label y devuelve el texto
    de la celda inmediatamente a la derecha (next sibling).
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

    # Main Activity: "41200 - CONSTRUCTION OF BUILDINGS"
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