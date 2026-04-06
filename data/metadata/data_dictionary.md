# Data Dictionary — HSE Enforcement Notices Dataset

## Dataset overview
- **Title:** HSE Enforcement Notices (List → Detail) — Extracted Dataset
- **Unit of analysis:** One enforcement notice (unique by `notice_number`)
- **Primary key:** `notice_number`
- **Source website:** HSE public notices register (resources.hse.gov.uk)
- **Extraction method:** Web scraping (HTML list pages + HTML detail pages)
- **Export format:** CSV (UTF-8)
- **Null policy:** Any field may be `null`/empty when the source page has an empty cell or the information is not available.
- **Date formats (as scraped):** `DD/MM/YYYY` (UK-style) for notice dates; `scraped_at_utc` is ISO-8601.

## Column dictionary
> **Source** = where the value comes from: `list` (notice_list.asp), `detail` (notice_details.asp), `derived` (computed/normalized by the scraper)

| Column | Description | Data type | Level | Source | Example | Notes / Cleaning |
|---|---|---|---|---|---|---|
| notice_number | Unique notice identifier shown by HSE | string | nominal | list/detail | `315684361` | Strip whitespace; treat as string (may exceed 32-bit int). |
| detail_url | Absolute URL to the notice detail page | string | — | list (derived) | `https://.../notice_details.asp?...` | Keep for traceability; do not use as key. |
| recipient_name_summary | Recipient name as shown in the list row | string | nominal | list | `Harren Limited` | May differ slightly from detail header; keep both if needed. |
| notice_type_summary | Notice type shown in list (summary) | string | nominal | list | `Improvement Notice` | Used as fallback if detail field is empty. |
| issue_date_summary | Issue date shown in list | string (date) | temporal | list | `20/02/2026` | Convert to date in analysis; validate `DD/MM/YYYY`. |
| local_authority_summary | Local authority shown in list | string | nominal | list | `Nottingham UA` | May be missing or abbreviated. |
| main_activity_summary | Main activity shown in list | string | nominal | list | `41200 - CONSTRUCTION OF BUILDINGS` | Can be split into code/label if needed. |
| served_date | Date served (from detail header) | string (date) | temporal | detail | `20/02/2026` | Convert to date; can be used as primary time marker. |
| notice_type | Notice type from detail page | string | nominal | detail | `Improvement Notice` | Prefer this over `_summary` fields; fallback to summary when null. |
| description | Full notice description (entire right-hand cell) | string | — | detail | `...` | Keep full text; normalize whitespace; avoid truncation. |
| compliance_date | Compliance date (right-hand cell) | string (date) | temporal | detail | `16/03/2026` | Convert to date; may be empty. |
| revised_compliance_date | Revised compliance date (right-hand cell) | string (date) | temporal | detail | `20/03/2026` | Often empty; keep null if missing. |
| result | Outcome/result status | string | nominal | detail | `Complied` | Categorical; expect small set of values. |
| address | Full address block (entire right-hand cell) | string | — | detail | `Castle Gate | Nottingham | ... | England` | Join lines using `|` or spaces; do **not** split unless required. |
| country | Country inferred from address (UK nations) | string | nominal | derived | `England` | Derived from last address line when it matches a UK nation; else null. |
| region | Region field (right-hand cell) | string | nominal | detail | `Midlands` | Do not mix into address. |
| local_authority | Local authority field (prefer detail) | string | nominal | detail/list | `Nottingham UA` | Prefer detail value; fallback to `_summary`. |
| industry | Industry field (right-hand cell) | string | nominal | detail | `Construction` | Useful grouping variable for ANOVA/segmentation. |
| main_activity_code | Numeric activity code parsed from “Main Activity” | string | nominal | derived | `41200` | Keep as string; may contain leading zeros in other domains. |
| main_activity_label | Activity label parsed from “Main Activity” | string | nominal | derived | `CONSTRUCTION OF BUILDINGS` | If parsing fails, keep full “Main Activity” as label. |
| location_type | Type of location field | string | nominal | detail | `Factory` | May be empty. |
| hse_group | HSE Group value (right-hand cell) | string | nominal | detail | `ISDIIU1G6` | Cells may be blank; keep null. |
| hse_directorate | HSE Directorate value (right-hand cell) | string | nominal | detail | `INSPECTION DIVISION` | Cells may be blank; keep null. |
| hse_area | HSE Area value (right-hand cell) | string | nominal | detail | `...` | Often blank; keep null. |
| hse_division | HSE Division value (right-hand cell) | string | nominal | detail | `East Midlands` | Cells may be blank; keep null. |
| scraped_at_utc | Timestamp when record was scraped (UTC) | string (datetime) | temporal | derived | `2026-04-06T20:14:32+00:00` | For reproducibility and provenance. |

## Recommended validation checks
- **Uniqueness:** `notice_number` must be unique (1 row per notice).
- **Date validity:** `served_date`, `issue_date_summary`, `compliance_date`, `revised_compliance_date` should match `DD/MM/YYYY` when non-null.
- **Whitespace:** normalize multiple spaces; preserve `address` line breaks using `|` or a single space.
- **Missingness:** expect missing values in HSE fields (especially `hse_area`).
- **Consistency:** if `notice_type` is null, use `notice_type_summary`; similarly for `local_authority`.

## Licensing and attribution (for Zenodo)
This dataset is derived from a UK public register. When publishing, include an attribution statement consistent with the Open Government Licence terms used by UK public sector information and cite HSE as the source.
