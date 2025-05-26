import pytest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup as bs

# Add project root to sys.path to allow importing altz.altz_calculator
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from altz.altz_calculator import AltmanZScoreCalculator

# Mock HTML content similar to what gurufocus.com might return
MOCK_HTML_VALID = """
<html><body>
    <p>Some irrelevant text</p> 
    <p>More irrelevant text</p>
    <p>Even more text</p> <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> 
    <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> 
    <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> <!-- Index 19 -->
    <p>
        Total Current Assets was $100.00 Mil. = 100000000
        Total Current Liabilities was $50.00 Mil. = 50000000
        Total Assets was $300.00 Mil. = 300000000
        Retained Earnings was $60.00 Mil. = 60000000
        Pre-Tax Income was $40.00 Mil. = 40000000
        Interest Expense was $5.00 Mil. = 5000000
        Revenue was $200.00 Mil. = 200000000
        Market Cap (Today) was $250.00 Mil. = 250000000
        Total Liabilities was $150.00 Mil. = 150000000
    </p>
</body></html>
"""

MOCK_HTML_MISSING_FIELDS = """
<html><body>
    <p>Some irrelevant text</p> <p>More irrelevant text</p> <p>Even more text</p> 
    <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> 
    <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> 
    <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> <!-- Index 19 -->
    <p>
        Total Current Assets was $100.00 Mil. = 100000000
        Total Assets was $300.00 Mil. = 300000000
        Revenue was $200.00 Mil. = 200000000
        Market Cap (Today) was $250.00 Mil. = 250000000
        Total Liabilities was $150.00 Mil. = 150000000
        <!-- Missing: Total Current Liabilities, Retained Earnings, Pre-Tax Income, Interest Expense -->
    </p>
</body></html>
"""

MOCK_HTML_INSUFFICIENT_P_TAGS = """
<html><body>
    <p>Only one p tag</p>
</body></html>
"""

MOCK_HTML_NO_DATA_MARKER = """
<html><body>
    <p>Some irrelevant text</p> <p>More irrelevant text</p> <p>Even more text</p> 
    <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> 
    <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> 
    <p>Text</p> <p>Text</p> <p>Text</p> <p>Text</p> <!-- Index 19 -->
    <p>
        Company X does not have enough data to calculate Altman Z-Score.
    </p>
</body></html>
"""

MOCK_HTML_NVDA_STYLE = """
<html><body>
    <p>Some introductory text about Z-Score calculation for NVDA.</p>
    <p>The formula is Z = 1.2 * X1 + ...</p>
    <p>
        Info about TTM data.
        Trailing Twelve Months (TTM) ended in Jan. 2025:
        [744]Total Assets was $111,601 Mil.
        [745]Total Current Assets was $80,126 Mil.
        [746]Total Current Liabilities was $18,047 Mil.
        [747]Retained Earnings was $68,038 Mil.
        [748]Pre-Tax Income was 25217 + 22316 + 19214 + 17279 = $84,026 Mil.
        [749]Interest Expense was -61 + -61 + -61 + -64 = $-247 Mil.
        [750]Revenue was 39331 + 35082 + 30040 + 26044 = $130,497 Mil.
        [751]Market Cap (Today) was $3,201,842.367 Mil.
        [752]Total Liabilities was $32,274 Mil.
        Other lines irrelevant to parsing...
    </p>
    <p>Further details and explanations.</p>
</body></html>
"""

@pytest.fixture
def mock_response_valid():
    mock_resp = MagicMock()
    mock_resp.text = MOCK_HTML_VALID
    mock_resp.raise_for_status = MagicMock() 
    return mock_resp

@pytest.fixture
def mock_response_missing_fields():
    mock_resp = MagicMock()
    mock_resp.text = MOCK_HTML_MISSING_FIELDS
    mock_resp.raise_for_status = MagicMock()
    return mock_resp

@pytest.fixture
def mock_response_insufficient_p_tags():
    mock_resp = MagicMock()
    mock_resp.text = MOCK_HTML_INSUFFICIENT_P_TAGS
    mock_resp.raise_for_status = MagicMock()
    return mock_resp
    
@pytest.fixture
def mock_response_no_data_marker():
    mock_resp = MagicMock()
    mock_resp.text = MOCK_HTML_NO_DATA_MARKER
    mock_resp.raise_for_status = MagicMock()
    return mock_resp

@pytest.fixture
def mock_response_nvda_style():
    mock_resp = MagicMock()
    mock_resp.text = MOCK_HTML_NVDA_STYLE
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


@patch('altz.altz_calculator.requests.get')
def test_financial_data_parsing_valid(mock_get, mock_response_valid):
    mock_get.return_value = mock_response_valid
    calculator = AltmanZScoreCalculator("TEST") # perform_init_fetch is True by default
    assert calculator.fs is not None
    assert calculator.fs['total_current_assets'] == 100000000.0
    assert calculator.fs['total_current_liabilities'] == 50000000.0
    # ... (other assertions remain the same) ...
    assert calculator.fs['total_liabilities'] == 150000000.0

@patch('altz.altz_calculator.requests.get')
def test_financial_data_parsing_missing_fields(mock_get, mock_response_missing_fields):
    mock_get.return_value = mock_response_missing_fields
    calculator = AltmanZScoreCalculator("TEST_MISSING") # perform_init_fetch is True
    assert calculator.fs is not None
    # ... (assertions for present fields) ...
    assert calculator.fs['total_liabilities'] == 150000000.0
    # Fields that were missing should default to 0.0
    assert calculator.fs['total_current_liabilities'] == 0.0
    # ... (other assertions for missing fields) ...
    assert calculator.fs['interest_expense'] == 0.0

@patch('altz.altz_calculator.requests.get')
def test_financial_data_parsing_insufficient_p_tags(mock_get, mock_response_insufficient_p_tags):
    mock_get.return_value = mock_response_insufficient_p_tags
    calculator = AltmanZScoreCalculator("TEST_INSUFFICIENT") # perform_init_fetch is True
    for field in calculator.FIELDS.keys():
        assert calculator.fs[field] == 0.0

@patch('altz.altz_calculator.requests.get')
def test_return_response_no_data_marker(mock_get, mock_response_no_data_marker):
    mock_get.return_value = mock_response_no_data_marker
    calculator = AltmanZScoreCalculator("NODATA") # perform_init_fetch is True
    assert calculator.soup is None
    for field_value in calculator.fs.values():
        assert field_value == 0.0

@patch('altz.altz_calculator.requests.get')
def test_financial_data_parsing_nvda_style(mock_get, mock_response_nvda_style):
    mock_get.return_value = mock_response_nvda_style
    calculator = AltmanZScoreCalculator("NVDA_TEST") # perform_init_fetch is True
    assert calculator.fs is not None
    assert calculator.fs['total_current_assets'] == 80126000000.0
    # ... (other assertions for NVDA style) ...
    assert abs(calculator.fs['market_cap'] - 3201842367000.0) < 0.01
    assert calculator.fs['total_liabilities'] == 32274000000.0

def test_clear_characters_method():
    calculator = AltmanZScoreCalculator("CLEAR_TEST", perform_init_fetch=False)
    test_cases = [
        ("[123]Total Assets was $1,234.56 Mil.", "Total Assets was ", 1234560000.0),
        ("Total Assets was $1,234.56 Mil.", "Total Assets was ", 1234560000.0),
        ("Pre-Tax Income was some text ... = $123.45 Mil.", "Pre-Tax Income was ", 123450000.0),
        ("Revenue was $100", "Revenue was ", 100.0),
        ("Market Cap (Today) was $ 2,000.00 Mil.", "Market Cap (Today) was ", 2000000000.0),
        ("Interest Expense was $-50.0 Mil.", "Interest Expense was ", -50000000.0),
        ("Retained Earnings was $0 Mil.", "Retained Earnings was ", 0.0),
        ("Total Liabilities was $12,345,678.90", "Total Liabilities was ", 12345678.90),
        ("Field was $Value Mil. with extra text", "Field was ", 0.0),
        ("Field was $10.00 Mil. (USD)", "Field was ", 10000000.0),
        ("Field was $10.00 (USD) Mil.", "Field was ", 10000000.0),
        ("Field was $10..00 Mil.", "Field was ", 0.0),
    ]
    for row_text, name_prefix, expected_value in test_cases:
        assert calculator._clear_characters(row_text, name_prefix) == expected_value, f"Failed for: {row_text}"

def test_z_score_calculation_and_components():
    calculator = AltmanZScoreCalculator("DUMMY", perform_init_fetch=False)
    calculator.fs = {
        'total_current_assets': 100.0, 'total_current_liabilities': 50.0,
        'total_assets': 300.0, 'retained_earnings': 60.0,
        'pre_tax_income': 40.0, 'interest_expense': 0.0, 
        'revenue': 200.0, 'market_cap': 250.0, 'total_liabilities': 150.0
    }
    # ... (assertions remain the same) ...
    expected_x1 = (100.0 - 50.0) / 300.0
    expected_x2 = 60.0 / 300.0
    expected_x3 = 40.0 / 300.0 
    expected_x4 = 250.0 / 150.0
    expected_x5 = 200.0 / 300.0

    assert abs(calculator.X1 - expected_x1) < 0.0001
    assert abs(calculator.X2 - expected_x2) < 0.0001
    assert abs(calculator.X3 - expected_x3) < 0.0001
    assert abs(calculator.X4 - expected_x4) < 0.0001
    assert abs(calculator.X5 - expected_x5) < 0.0001

    expected_z_score = (1.2 * expected_x1) + (1.4 * expected_x2) + (3.3 * expected_x3) + \
                       (0.6 * expected_x4) + (1.0 * expected_x5)
    
    actual_z_score = calculator.calculate_score()
    assert actual_z_score is not None
    assert abs(actual_z_score - expected_z_score) < 0.0001


def test_z_score_calculation_edge_cases():
    # For this test, we want to control fs directly, so perform_init_fetch=False
    calculator = AltmanZScoreCalculator("DUMMY_EDGE", perform_init_fetch=False)

    # Case 1: Total Assets = 0
    calculator.fs = {
        'total_current_assets': 100.0, 'total_current_liabilities': 50.0, 'total_assets': 0.0,
        'retained_earnings': 60.0, 'pre_tax_income': 40.0, 'interest_expense': 5.0,
        'revenue': 200.0, 'market_cap': 250.0, 'total_liabilities': 150.0
    }
    # ... (assertions remain the same) ...
    assert calculator.calculate_score() is None 

    # Case 2: Total Liabilities = 0 (and Total Assets non-zero)
    calculator.fs = {
        'total_current_assets': 100.0, 'total_current_liabilities': 50.0, 'total_assets': 300.0,
        'retained_earnings': 60.0, 'pre_tax_income': 40.0, 'interest_expense': 5.0,
        'revenue': 200.0, 'market_cap': 250.0, 'total_liabilities': 0.0
    }
    # ... (assertions remain the same) ...
    expected_x1_tl0 = (100.0 - 50.0) / 300.0
    expected_x2_tl0 = 60.0 / 300.0
    expected_x3_tl0 = (40.0 - 5.0) / 300.0 
    expected_x4_tl0 = 0.0 
    expected_x5_tl0 = 200.0 / 300.0
    expected_z_tl0 = (1.2 * expected_x1_tl0) + (1.4 * expected_x2_tl0) + (3.3 * expected_x3_tl0) + \
                     (0.6 * expected_x4_tl0) + (1.0 * expected_x5_tl0)
    z_score_tl_zero = calculator.calculate_score()
    assert z_score_tl_zero is not None
    assert abs(z_score_tl_zero - expected_z_tl0) < 0.0001


@patch('altz.altz_calculator.requests.get')
def test_get_score_details(mock_get, mock_response_valid):
    mock_get.return_value = mock_response_valid
    calculator = AltmanZScoreCalculator("TEST") # perform_init_fetch is True
    # ... (assertions remain the same) ...
    assert details['raw_data']['total_assets'] == 300000000.0

@patch('altz.altz_calculator.requests.get')
def test_init_failure_request_exception(mock_get):
    mock_get.side_effect = requests.exceptions.RequestException("Network Error")
    calculator = AltmanZScoreCalculator("FAIL") # perform_init_fetch is True
    assert calculator.soup is None
    assert calculator.fs is not None 
    for field_value in calculator.fs.values():
        assert field_value == 0.0
    details = calculator.get_score_details()
    assert details['z_score'] is None

@patch('altz.altz_calculator.AltmanZScoreCalculator._return_response')
def test_init_no_response_from_return_response(mock_return_response):
    mock_return_response.return_value = None 
    calculator = AltmanZScoreCalculator("NORESP") # perform_init_fetch is True
    assert calculator.soup is None
    assert calculator.fs is not None 
    for field_value in calculator.fs.values():
        assert field_value == 0.0
    details = calculator.get_score_details()
    assert details['z_score'] is None
```
