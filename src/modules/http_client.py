from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass(frozen=True)
class HttpConfig:
    timeout: int = 30


def make_session() -> requests.Session:
    """
    Session con reintentos y backoff para errores transitorios.
    No intenta evadir bloqueos: si hay 403, se deja fallar arriba.
    """
    session = requests.Session()
    retry = Retry(
        total=6,
        connect=6,
        read=6,
        status=6,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_html(
    session: requests.Session,
    url: str,
    headers: Dict[str, str],
    timeout: int = 30,
) -> str:
    r = session.get(url, headers=headers, timeout=timeout)

    # Si el sitio bloquea (403), NO se debe intentar “saltarlo”.
    if r.status_code == 403:
        raise RuntimeError(f"403 Forbidden en {url} (posible bloqueo / limitación).")

    r.raise_for_status()
    return r.text