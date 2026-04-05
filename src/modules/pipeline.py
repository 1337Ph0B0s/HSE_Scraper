from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional
from urllib.parse import urlsplit, parse_qs, urlencode, urlunsplit

import requests
from tqdm import tqdm

from src.modules.config import LIST_URL, DEFAULT_HEADERS, DEFAULT_TIMEOUT
from src.modules.http_client import fetch_html, make_session
from src.modules.list_parser import parse_list_page, parse_total_pages
from src.modules.detail_parser import parse_detail_page
from src.modules.storage import SQLiteStore

@dataclass
class NoticeRecord:
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
    time.sleep(random.uniform(min_delay, max_delay))


def _build_list_page_url(base_url: str, page: int) -> str:
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
    Orquesta:
    - detecta total de páginas
    - itera listado PN=start..end
    - entra al detalle por notice
    - guarda en SQLite (reanudable)
    - exporta CSV al final
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