import requests
from src.modules.detail_parser import parse_detail_page

URL = "https://resources.hse.gov.uk/notices/notices/notice_details.asp?SF=CN&SV=315684361"
HEADERS = {"User-Agent": "AcademicScraper/1.0 (+contact: you@example.com)"}

html = requests.get(URL, headers=HEADERS, timeout=30).text
d = parse_detail_page(html)

for k in [
    "notice_number","notice_type","description","compliance_date","revised_compliance_date","result",
    "address","region","local_authority","industry","main_activity_code","main_activity_label",
    "hse_group","hse_directorate","hse_area","hse_division"
]:
    print(f"{k}: {d.get(k)}")