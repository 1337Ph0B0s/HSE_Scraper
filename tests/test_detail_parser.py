from src.modules.detail_parser import parse_detail_page


def test_parse_detail_page_basic_fields():
    html = """
    <html><body>
      <h1>Notice 123 served against ACME LTD on 01/01/2024</h1>
      <div>Notice Type Improvement Notice</div>
      <div>Description Fix safety issue</div>
      <div>Compliance Date 15/01/2024 Revised Compliance Date 20/01/2024</div>
      <div>Result Complied</div>

      <h2>Location of Offence</h2>
      <div>Address</div>
      <div>Street 1</div>
      <div>City</div>
      <div>England Region Midlands</div>
      <div>Local Authority Test LA</div>
      <div>Industry Manufacturing</div>
      <div>Main Activity 123 - Test Activity</div>
      <div>Type of Location Factory</div>

      <h2>HSE Details</h2>
      <div>HSE Group Field Operations</div>
      <div>HSE Directorate Something</div>
      <div>HSE Area Area 1</div>
      <div>HSE Division Div 1</div>
    </body></html>
    """
    d = parse_detail_page(html)
    assert d["notice_number"] == "123"
    assert d["served_date"] == "01/01/2024"
    assert d["notice_type"] is not None
    assert d["compliance_date"] == "15/01/2024"
    assert d["revised_compliance_date"] == "20/01/2024"
    assert d["country"] == "England"
    assert d["region"] == "Midlands"
    assert d["main_activity_code"] == "123"