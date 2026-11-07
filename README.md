# HSE Enforcement Notices — Web Scraping & Data Engineering Pipeline

**A resumable Python ETL pipeline for collecting, structuring, and exporting public enforcement notices from the UK's Health and Safety Executive (HSE).**

**Language:** English | [Español](README.es.md) | [Nederlands](README.nl.md)

[![Python](https://img.shields.io/badge/Python-3.x-blue)](https://www.python.org/)
[![License: GPL v3](https://img.shields.io/badge/Code%20License-GPLv3-blue)](LICENSE)
[![Dataset DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.19438807-blue)](https://doi.org/10.5281/zenodo.19438807)

## Overview

This project implements a modular **web scraping and ETL pipeline** for the [HSE Public Notices Register](https://resources.hse.gov.uk/notices/notices/notice_list.asp). It extracts enforcement notice records from paginated listing pages, follows links to individual notices, and creates structured datasets suitable for exploratory data analysis (EDA), statistical analysis, and downstream data engineering workflows.

Data collection has two stages:

1. **Listing pages (`notice_list.asp`):** Discover notices and extract summary information from paginated lists (typically around ten entries per page).
2. **Detail pages (`notice_details.asp`):** Follow each notice link to extract additional fields.

The pipeline prioritizes **reproducibility, fault tolerance, and responsible data acquisition**. It preserves source URLs and extraction timestamps, persists progress in SQLite, logs extraction errors, and exports records to UTF-8 CSV.

### Key capabilities

- Modular architecture separating HTTP communication, HTML parsing, pipeline orchestration, and persistence.
- Command-line interface (CLI) for limited sampling, page-range extraction, or processing all discovered pages.
- Incremental SQLite commits to help recover progress after interrupted runs.
- Notice identification using `notice_number` to prevent duplicate stored records.
- Error logging and HTTP retry/backoff for transient failures.
- Configurable randomized delays between HTTP requests.
- Structured SQLite and CSV outputs with a field-level data dictionary.
- Parser tests and supporting development tools.

## Data source

**Publisher:** Health and Safety Executive (HSE), United Kingdom  
**Register:** [HSE Public Notices Register](https://resources.hse.gov.uk/notices/notices/notice_list.asp)

Example listing URL:

```text
https://resources.hse.gov.uk/notices/notices/notice_list.asp?PN=1&ST=N&rdoNType=&NT=&SN=F&EO=LIKE&SF=RN&SV=&SO=DNIS
```

Each listing entry links to a detail page (`notice_details.asp`). Source content and HTML structure may change over time.

## Repository structure

```text
source/
  main.py                    # CLI entry point
  __init__.py
  modules/
    __init__.py
    config.py                # Configuration
    http_client.py           # HTTP client, retries and throttling
    list_parser.py           # Listing parser and page discovery
    detail_parser.py         # Notice detail parser
    storage.py               # SQLite persistence and CSV export
    pipeline.py              # End-to-end extraction orchestration

tests/
  test_list_parser.py
  test_detail_parser.py

data/
  metadata/
    data_dictionary.md       # Data dictionary
  processed/                 # Example datasets and archived exports

requirements.txt
requirements-dev.txt
LICENSE
README.md
README.es.md
README.nl.md
```

The detail parser reads labeled HTML tables and preserves text fields such as `description` and `address`. The pipeline coordinates listing/detail extraction, while `SQLiteStore` handles durable storage, checkpoints, and export.

## Installation

A Python virtual environment is recommended.

```bash
git clone https://github.com/1337Ph0B0s/HSE_Scraper.git
cd HSE_Scraper
python -m venv .venv
```

Activate it and install dependencies:

```bash
# Linux / macOS
source .venv/bin/activate

# Windows PowerShell (run separately)
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Main dependencies include `requests`, `beautifulsoup4`, `lxml`, `pandas`, and `tqdm`. For development and testing, install `requirements-dev.txt` (includes `pytest`, `pylint`, and `sphinx`).

## Command-line usage

Run from the repository root:

```bash
python -m source.main [options]
```

| Option | Description |
| --- | --- |
| `--db` | SQLite database path for persistence and resuming |
| `--out` | Output CSV path |
| `--user-agent` | Identifiable HTTP User-Agent |
| `--min-delay` | Minimum delay between requests, in seconds |
| `--max-delay` | Maximum delay between requests, in seconds |
| `--start-page` | First listing page to process |
| `--pages` | Number of listing pages to process in partial mode |
| `--all` | Process all discovered listing pages |
| `--commit-every` | Number of records between SQLite commits |

### Quick sample (3 pages, approximately 30 records)

```bash
python -m source.main --pages 3 \
  --out data/processed/hse_sample.csv \
  --db data/processed/hse_sample.sqlite
```

### Ten-page extraction

```bash
python -m source.main --pages 10 --min-delay 0.8 --max-delay 1.6 \
  --out data/processed/hse_10p.csv --db data/processed/hse_10p.sqlite
```

### Full-listing extraction

```bash
python -m source.main --all --min-delay 1.2 --max-delay 2.5 \
  --out data/processed/hse_full.csv --db data/processed/hse_full.sqlite
```

The multiline examples use Unix shell continuation (`\`). On Windows PowerShell, run each command on one line or use PowerShell's backtick continuation character.

**Note:** Full extraction may take many hours or longer depending on available pages, request delays, and site response times.

## Responsible scraping

The scraper is designed to avoid unnecessary load on HSE systems:

- Configure randomized waits using `--min-delay` and `--max-delay`.
- Set an identifiable User-Agent with an appropriate research purpose and contact address.
- Retry transient failures, including HTTP 429 and 5xx responses, with backoff.
- Stop when receiving HTTP 403; do not attempt to bypass access restrictions.

Review the website's current terms and access restrictions before large extraction runs. A small sample is usually adequate for demonstrations.

## SQLite persistence and recovery

SQLite retains incremental progress in these tables:

| Table | Purpose |
| --- | --- |
| `notices` | One record per `notice_number`, with notice fields stored as JSON |
| `errors` | Log entries for failed URLs or extraction attempts |

**CSV is exported at the end of a run.** If the program is interrupted, the CSV may be older than the latest committed SQLite data. Any uncommitted records may need to be fetched again.

To count committed notices:

```bash
python -c "import sqlite3; con=sqlite3.connect('data/processed/hse_sample.sqlite'); print(con.execute('SELECT COUNT(*) FROM notices').fetchone()[0])"
```

To resume after processing page 96, reuse the same database and start at page 97:

```bash
python -m source.main --all --start-page 97 --min-delay 1.2 --max-delay 2.5 \
  --out data/processed/hse_full.csv \
  --db data/processed/hse_full.sqlite
```

Replace `97` with the page appropriate for your run. Resumption is configured through `--start-page` and the persisted SQLite database.

## Data dictionary and quality checks

See [`data/metadata/data_dictionary.md`](data/metadata/data_dictionary.md) for field definitions, sources, data types, and cleaning notes.

Recommended checks for downstream data analysis:

- **Uniqueness:** Verify that `notice_number` is unique.
- **Dates:** Parse date fields consistently (such as `DD/MM/YYYY` where applicable).
- **Missing values:** Review incomplete fields without assuming all attributes exist.
- **Text:** Normalize whitespace without discarding multiline `description` or `address` content.
- **Field consistency:** Use list-level values as documented fallbacks when detail-level values are missing.
- **Traceability:** Retain source URLs and `scraped_at_utc` timestamps.

The project prepares structured source data. EDA, correlation analysis, or ANOVA are potential **downstream uses**, not analytical features implemented by the scraper itself.

## Published datasets

The existing documentation records this extraction command:

```bash
python -m source.main --all --min-delay 1.0 --max-delay 3.0 \
  --out data/processed/hse_notities.csv \
  --db data/processed/hse_notities.sqlite
```

The repository includes:

- [`hse_notices.csv.rar`](data/processed/hse_notices.csv.rar) — archived CSV export.
- [`hse_notices.sqlite.rar`](data/processed/hse_notices.sqlite.rar) — archived SQLite export.
- [`hse_sample.csv`](data/processed/hse_sample.csv) — sample CSV.
- [`hse_sample.sqlite`](data/processed/hse_sample.sqlite) — sample SQLite database.

**Published dataset DOI:** [10.5281/zenodo.19438807](https://doi.org/10.5281/zenodo.19438807)

The archives and sample datasets are distinct. Verify archive contents before claiming a specific record total or extraction-completion percentage.

## Testing and reproducibility

Install development dependencies and run the parser tests:

```bash
pip install -r requirements-dev.txt
python -m pytest tests/
```

For reproducibility, retain the exact CLI invocation, extraction time (`scraped_at_utc`), dependency versions, data dictionary, and HSE source URLs. Since the source is live, subsequent runs may yield different records.

## Licensing and attribution

**Code:** Distributed under the **GNU General Public License v3 or later**, according to [`LICENSE`](LICENSE).

**Underlying HSE public-sector information:** [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Retain the attribution: *Contains public sector information published by the Health and Safety Executive and licensed under the Open Government Licence v3.0.*

These terms apply to different components: the repository's code and the source information, respectively.

## Academic context

Developed as part of **M2.851 — Data Typology and Life Cycle**, an academic project involving automated data collection, structured storage, and reproducible processing.

---

**Repository:** https://github.com/1337Ph0B0s/HSE_Scraper  
**Dataset reference:** https://doi.org/10.5281/zenodo.19438807
