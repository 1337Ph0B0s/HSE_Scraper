from __future__ import annotations

LIST_URL = (
    "https://resources.hse.gov.uk/notices/notices/notice_list.asp"
    "?PN=1&ST=N&rdoNType=&NT=&SN=F&EO=LIKE&SF=RN&SV=&SO=DNIS"
)

DEFAULT_USER_AGENT = (
    "AcademicScraper/1.0 (+contact: pdpazmino@uoc.edu) "
    "Purpose: academic research (UOC Practice 1) - respectful rate limiting"
)

DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Connection": "keep-alive",
}

# Delays conservadores por defecto (ajustables por CLI)
DEFAULT_MIN_DELAY = 1.5
DEFAULT_MAX_DELAY = 6.0

# Timeout por request
DEFAULT_TIMEOUT = 30