from source.modules.list_parser import parse_total_pages, parse_list_page


def test_parse_total_pages():
    html = "Showing Page 1 of 3055"
    assert parse_total_pages(html) == 3055


def test_parse_list_page_extracts_rows():
    html = """
    <html><body>
      <table>
        <tr><th>Notice Number</th><th>Recipient</th><th>Notice Type</th><th>Issue Date</th><th>Local Authority</th><th>Main Activity</th></tr>
        <tr>
          <td><a href="notice_details.asp?SF=CN&SV=123">123</a></td>
          <td>ACME LTD</td><td>Improvement</td><td>01/01/2024</td><td>Some LA</td><td>123 - Activity</td>
        </tr>
      </table>
    </body></html>
    """
    items = parse_list_page(html, "https://resources.hse.gov.uk/notices/notices/notice_list.asp?PN=1")
    assert len(items) == 1
    assert items[0].notice_number == "123"
    assert "notice_details.asp" in items[0].detail_url