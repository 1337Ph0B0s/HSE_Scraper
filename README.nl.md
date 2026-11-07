# HSE Enforcement Notices — Webscraping- en data-engineeringpipeline

**Een hervatbare ETL-pipeline in Python voor het verzamelen, structureren en exporteren van openbare handhavingskennisgevingen van de Britse Health and Safety Executive (HSE).**

**Taal:** [English](README.md) | [Español](README.es.md) | Nederlands

[![Python](https://img.shields.io/badge/Python-3.x-blue)](https://www.python.org/)
[![Licentie: GPL v3](https://img.shields.io/badge/Code%20License-GPLv3-blue)](LICENSE)
[![Dataset DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.19438807-blue)](https://doi.org/10.5281/zenodo.19438807)

## Overzicht

Dit project implementeert een modulaire **webscraping- en ETL-pipeline** voor het [openbare HSE-register van handhavingskennisgevingen](https://resources.hse.gov.uk/notices/notices/notice_list.asp). De toepassing verzamelt kennisgevingen uit gepagineerde overzichtspagina's, volgt koppelingen naar afzonderlijke detailpagina's en bouwt gestructureerde datasets op. Deze zijn geschikt voor verkennende data-analyse (EDA), statistische analyses en verdere data-engineeringprocessen.

De gegevensverzameling verloopt in twee fasen:

1. **Overzichtspagina's (`notice_list.asp`):** Kennisgevingen identificeren en samenvattende gegevens ophalen uit gepagineerde lijsten (doorgaans ongeveer tien records per pagina).
2. **Detailpagina's (`notice_details.asp`):** De koppeling naar elke kennisgeving volgen om aanvullende velden uit te lezen.

De pipeline legt de nadruk op **reproduceerbaarheid, fouttolerantie en verantwoorde gegevensverzameling**. Bron-URL's en tijdstempels blijven behouden, de voortgang wordt opgeslagen in SQLite, fouten worden geregistreerd en de records worden als UTF-8-CSV geëxporteerd.

### Belangrijkste functionaliteiten

- Modulaire architectuur met afzonderlijke componenten voor HTTP-communicatie, HTML-parsing, procesorkestratie en gegevensopslag.
- Opdrachtregelinterface (CLI) voor steekproeven, het verwerken van een beperkt aantal pagina's of alle gedetecteerde pagina's.
- Incrementele SQLite-commits om de voortgang na een onderbreking zo veel mogelijk te behouden.
- Unieke identificatie via `notice_number` om dubbele opgeslagen records te voorkomen.
- Foutregistratie en automatische HTTP-herhaalpogingen met back-off bij tijdelijke storingen.
- Instelbare, willekeurige wachttijden tussen HTTP-verzoeken.
- Gestructureerde output in SQLite en CSV, met een gegevenswoordenboek op veldniveau.
- Tests voor de parsers en aanvullende ontwikkelhulpmiddelen.

## Gegevensbron

**Uitgever:** Health and Safety Executive (HSE), Verenigd Koninkrijk  
**Register:** [HSE Public Notices Register](https://resources.hse.gov.uk/notices/notices/notice_list.asp)

Voorbeeld van een overzichts-URL:

```text
https://resources.hse.gov.uk/notices/notices/notice_list.asp?PN=1&ST=N&rdoNType=&NT=&SN=F&EO=LIKE&SF=RN&SV=&SO=DNIS
```

Elk item in het overzicht verwijst naar een detailpagina (`notice_details.asp`). De brongegevens en de HTML-structuur kunnen in de loop van de tijd veranderen.

## Projectstructuur

```text
source/
  main.py                    # Startpunt van de CLI
  __init__.py
  modules/
    __init__.py
    config.py                # Configuratie
    http_client.py           # HTTP-client, herhaalpogingen en snelheidsbeperking
    list_parser.py           # Verwerking van overzichten en paginadetectie
    detail_parser.py         # Parser voor kennisgevingsdetails
    storage.py               # SQLite-opslag en CSV-export
    pipeline.py              # Orkestratie van het volledige extractieproces

tests/
  test_list_parser.py
  test_detail_parser.py

data/
  metadata/
    data_dictionary.md       # Gegevenswoordenboek
  processed/                 # Voorbeelddatasets en gearchiveerde exports

requirements.txt
requirements-dev.txt
LICENSE
README.md
README.es.md
README.nl.md
```

De detailparser leest HTML-tabellen met veldlabels en behoudt tekstvelden zoals `description` en `address`. De pipeline coördineert de verwerking van overzichts- en detailpagina's. `SQLiteStore` verzorgt de persistente opslag, het bewaren van voortgang en de export.

## Installatie

Het gebruik van een virtuele Python-omgeving wordt aanbevolen.

```bash
git clone https://github.com/1337Ph0B0s/HSE_Scraper.git
cd HSE_Scraper
python -m venv .venv
```

Activeer de omgeving en installeer de afhankelijkheden:

```bash
# Linux / macOS
source .venv/bin/activate

# Windows PowerShell (afzonderlijk uitvoeren)
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

De belangrijkste afhankelijkheden zijn `requests`, `beautifulsoup4`, `lxml`, `pandas` en `tqdm`. Installeer voor ontwikkeling en testen ook `requirements-dev.txt` (met onder meer `pytest`, `pylint` en `sphinx`).

## Gebruik via de opdrachtregel

Voer het programma uit vanuit de hoofdmap van de repository:

```bash
python -m source.main [options]
```

| Optie | Beschrijving |
| --- | --- |
| `--db` | Pad naar de SQLite-database voor opslag en hervatting |
| `--out` | Pad naar het CSV-uitvoerbestand |
| `--user-agent` | Identificeerbare HTTP User-Agent |
| `--min-delay` | Minimale wachttijd tussen verzoeken, in seconden |
| `--max-delay` | Maximale wachttijd tussen verzoeken, in seconden |
| `--start-page` | Eerste te verwerken overzichtspagina |
| `--pages` | Aantal te verwerken pagina's in de beperkte modus |
| `--all` | Alle gedetecteerde overzichtspagina's verwerken |
| `--commit-every` | Aantal records tussen opeenvolgende SQLite-commits |

### Snelle test (3 pagina's, ongeveer 30 records)

```bash
python -m source.main --pages 3 \
  --out data/processed/hse_sample.csv \
  --db data/processed/hse_sample.sqlite
```

### Extractie van tien pagina's

```bash
python -m source.main --pages 10 --min-delay 0.8 --max-delay 1.6 \
  --out data/processed/hse_10p.csv --db data/processed/hse_10p.sqlite
```

### Extractie van alle overzichtspagina's

```bash
python -m source.main --all --min-delay 1.2 --max-delay 2.5 \
  --out data/processed/hse_full.csv --db data/processed/hse_full.sqlite
```

De voorbeelden met meerdere regels gebruiken de Unix-regelvoortzetting (`\`). Voer de opdrachten in Windows PowerShell uit op één regel of gebruik het PowerShell-backtickteken voor regelvoortzetting.

**Opmerking:** Een volledige extractie kan vele uren of langer duren, afhankelijk van het aantal beschikbare pagina's, de ingestelde wachttijden en de responstijden van de website.

## Verantwoord webscrapen

De scraper is ontworpen om onnodige belasting van de HSE-systemen te vermijden:

- Stel willekeurige wachttijden in via `--min-delay` en `--max-delay`.
- Gebruik een herkenbare User-Agent met een passend onderzoeksdoel en contactadres.
- Herhaal verzoeken bij tijdelijke fouten, waaronder HTTP 429 en 5xx, met back-off.
- Stop bij een HTTP 403-respons; probeer toegangsbeperkingen niet te omzeilen.

Controleer vóór omvangrijke extracties steeds de actuele gebruiksvoorwaarden en toegangsbeperkingen van de website. Voor een demonstratie volstaat doorgaans een beperkte steekproef.

## SQLite-persistentie en hervatting

SQLite bewaart de voortgang stapsgewijs in de volgende tabellen:

| Tabel | Functie |
| --- | --- |
| `notices` | Eén record per `notice_number`, met de gegevens van de kennisgeving opgeslagen als JSON |
| `errors` | Logboek van mislukte URL's en extractiepogingen |

**De CSV-export vindt plaats aan het einde van een uitvoering.** Bij een onderbreking kan het CSV-bestand dus ouder zijn dan de laatst vastgelegde gegevens in SQLite. Records die nog niet gecommit zijn, moeten mogelijk opnieuw worden opgehaald.

Het aantal opgeslagen kennisgevingen opvragen:

```bash
python -c "import sqlite3; con=sqlite3.connect('data/processed/hse_sample.sqlite'); print(con.execute('SELECT COUNT(*) FROM notices').fetchone()[0])"
```

Om na pagina 96 te hervatten, hergebruik je dezelfde database en begin je bij pagina 97:

```bash
python -m source.main --all --start-page 97 --min-delay 1.2 --max-delay 2.5 \
  --out data/processed/hse_full.csv \
  --db data/processed/hse_full.sqlite
```

Vervang `97` door het juiste paginanummer voor jouw uitvoering. De hervatting steunt op `--start-page` en de opgeslagen SQLite-database.

## Gegevenswoordenboek en kwaliteitscontroles

Raadpleeg [`data/metadata/data_dictionary.md`](data/metadata/data_dictionary.md) voor velddefinities, herkomst, gegevenstypen en opmerkingen over gegevensopschoning.

Aanbevolen controles voor verdere data-analyse:

- **Uniciteit:** Controleer of `notice_number` uniek is.
- **Datums:** Parseer datumvelden consequent (bijvoorbeeld `DD/MM/YYYY` wanneer van toepassing).
- **Ontbrekende waarden:** Onderzoek onvolledige velden zonder ervan uit te gaan dat ieder attribuut beschikbaar is.
- **Tekst:** Normaliseer witruimte zonder meerregelige inhoud in `description` of `address` te verliezen.
- **Consistentie van velden:** Gebruik waar nodig gedocumenteerde terugvalwaarden uit de overzichtspagina's wanneer detailgegevens ontbreken.
- **Traceerbaarheid:** Bewaar bron-URL's en de tijdstempels `scraped_at_utc`.

Het project bereidt gestructureerde brongegevens voor. EDA, correlatieanalyse en ANOVA zijn mogelijke **vervolgtoepassingen**, maar zijn geen analytische functies die door de scraper zelf worden uitgevoerd.

## Gepubliceerde datasets

In de bestaande projectdocumentatie is de volgende extractieopdracht opgenomen:

```bash
python -m source.main --all --min-delay 1.0 --max-delay 3.0 \
  --out data/processed/hse_notities.csv \
  --db data/processed/hse_notities.sqlite
```

De repository bevat:

- [`hse_notices.csv.rar`](data/processed/hse_notices.csv.rar) — gearchiveerde CSV-export.
- [`hse_notices.sqlite.rar`](data/processed/hse_notices.sqlite.rar) — gearchiveerde SQLite-export.
- [`hse_sample.csv`](data/processed/hse_sample.csv) — voorbeeldbestand in CSV-formaat.
- [`hse_sample.sqlite`](data/processed/hse_sample.sqlite) — voorbeeldbestand in SQLite-formaat.

**DOI van de gepubliceerde dataset:** [10.5281/zenodo.19438807](https://doi.org/10.5281/zenodo.19438807)

De archieven en de voorbeelddatasets zijn verschillende bestanden. Controleer de inhoud van de archieven voordat je een exact aantal records of een voltooiingspercentage van de extractie vermeldt.

## Testen en reproduceerbaarheid

Installeer de ontwikkelafhankelijkheden en voer de parsertests uit:

```bash
pip install -r requirements-dev.txt
python -m pytest tests/
```

Bewaar voor reproduceerbaarheid de exacte CLI-opdracht, het tijdstip van extractie (`scraped_at_utc`), de versies van de afhankelijkheden, het gegevenswoordenboek en de bron-URL's van HSE. Aangezien het om een live gegevensbron gaat, kunnen latere uitvoeringen andere records opleveren.

## Licenties en bronvermelding

**Broncode:** Beschikbaar onder de **GNU General Public License, versie 3 of later**, volgens het bestand [`LICENSE`](LICENSE).

**Onderliggende openbare informatie van HSE:** [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Behoud de officiële Engelstalige bronvermelding: *Contains public sector information published by the Health and Safety Executive and licensed under the Open Government Licence v3.0.*

Deze voorwaarden gelden voor verschillende onderdelen: enerzijds de broncode van het project en anderzijds de oorspronkelijke overheidsinformatie.

## Academische context

Ontwikkeld in het kader van **M2.851 — Typologie en levenscyclus van data**, een academisch project over geautomatiseerde gegevensverzameling, gestructureerde opslag en reproduceerbare gegevensverwerking.

---

**Repository:** https://github.com/1337Ph0B0s/HSE_Scraper  
**Datasetreferentie:** https://doi.org/10.5281/zenodo.19438807
