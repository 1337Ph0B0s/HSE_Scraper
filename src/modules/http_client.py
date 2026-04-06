from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass(frozen=True)
class HttpConfig:
    """
    Configuración inmutable del cliente HTTP.

    Agrupa parámetros básicos usados por el scraper para mantener una configuración
    consistente y reproducible.

    :param timeout: Tiempo máximo de espera (segundos) para una petición HTTP.
    :type timeout: int
    """
    timeout: int = 30


def make_session() -> requests.Session:
    """
    Crea una sesión HTTP (`requests.Session`) con reintentos y backoff.

    La sesión resultante reutiliza conexiones (pooling) y aplica una política de reintentos
    ante errores transitorios (por ejemplo 429 y 5xx) para mejorar la robustez del scraping.

    :return: Sesión HTTP configurada con `HTTPAdapter` y `Retry`.
    :rtype: requests.Session
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
    """
    Descarga una página HTML mediante HTTP GET y devuelve su contenido como texto.

    Esta función centraliza la descarga de páginas del listado y del detalle, usando una
    `requests.Session` reutilizable. No intenta evadir bloqueos: si el servidor responde
    con 403 se aborta la ejecución con un error.

    Args:
        session: Sesión HTTP (`requests.Session`) reutilizable.
        url: URL absoluta a descargar.
        headers: Cabeceras HTTP (debe incluir un User-Agent identificable).
        timeout: Tiempo máximo de espera en segundos.

    Returns:
        El HTML de la página descargada.

    Raises:
        RuntimeError: Si el servidor devuelve 403 (Forbidden).
        requests.HTTPError: Si hay un código HTTP no exitoso (tras reintentos, si aplican).
        requests.RequestException: Para errores de red (timeouts, conexión, etc.).
    """

    r = session.get(url, headers=headers, timeout=timeout)

    # Si el sitio bloquea (403), NO se debe intentar “saltarlo”.
    if r.status_code == 403:
        raise RuntimeError(f"403 Forbidden en {url} (posible bloqueo / limitación).")

    r.raise_for_status()
    return r.text