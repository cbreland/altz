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


@pytest.fixture
def mock_response_valid():
    mock_resp = MagicMock()
    mock_resp.text = MOCK_HTML_VALID
    mock_resp.raise_for_status = MagicMock() # Mock this to do nothing for successful responses
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


@patch('altz.altz_calculator.requests.get')
def test_financial_data_parsing_valid(mock_get, mock_response_valid):
    mock_get.return_value = mock_response_valid
    calculator = AltmanZScoreCalculator("TEST")
    
    # _financial_data is called during __init__ if soup is available
    assert calculator.fs is not None
    assert calculator.fs['total_current_assets'] == 100000000.0
    assert calculator.fs['total_current_liabilities'] == 50000000.0
    assert calculator.fs['total_assets'] == 300000000.0
    assert calculator.fs['retained_earnings'] == 60000000.0
    assert calculator.fs['pre_tax_income'] == 40000000.0
    assert calculator.fs['interest_expense'] == 5000000.0
    assert calculator.fs['revenue'] == 200000000.0
    assert calculator.fs['market_cap'] == 250000000.0
    assert calculator.fs['total_liabilities'] == 150000000.0

@patch('altz.altz_calculator.requests.get')
def test_financial_data_parsing_missing_fields(mock_get, mock_response_missing_fields):
    mock_get.return_value = mock_response_missing_fields
    calculator = AltmanZScoreCalculator("TEST")

    assert calculator.fs is not None
    assert calculator.fs['total_current_assets'] == 100000000.0
    assert calculator.fs['total_assets'] == 300000000.0
    assert calculator.fs['revenue'] == 200000000.0
    assert calculator.fs['market_cap'] == 250000000.0
    assert calculator.fs['total_liabilities'] == 150000000.0
    
    # Fields that were missing should default to 0.0 as per implementation
    assert calculator.fs['total_current_liabilities'] == 0.0
    assert calculator.fs['retained_earnings'] == 0.0
    assert calculator.fs['pre_tax_income'] == 0.0
    assert calculator.fs['interest_expense'] == 0.0

@patch('altz.altz_calculator.requests.get')
def test_financial_data_parsing_insufficient_p_tags(mock_get, mock_response_insufficient_p_tags):
    mock_get.return_value = mock_response_insufficient_p_tags
    calculator = AltmanZScoreCalculator("TEST")
    # Expect all fields to be default (0.0) because parsing the specific p[19] will fail
    for field in calculator.FIELDS.keys():
        assert calculator.fs[field] == 0.0

@patch('altz.altz_calculator.requests.get')
def test_return_response_no_data_marker(mock_get, mock_response_no_data_marker):
    # This test checks if _return_response correctly identifies the "no data" marker
    # and returns None, leading to default fs values.
    mock_get.return_value = mock_response_no_data_marker # Simulate "does not have enough data"
    
    calculator = AltmanZScoreCalculator("NODATA")
    assert calculator.soup is None # soup should not be set if response indicates no data
    assert calculator.fs is not None # fs should be initialized to defaults
    for field_value in calculator.fs.values():
        assert field_value == 0.0 # All financial statement items should be default (0)

def test_z_score_calculation_and_components():
    # Test calculations with a fixed set of data, bypassing parsing
    calculator = AltmanZScoreCalculator("DUMMY") # Dummy ticker, we will overwrite fs

    # Pre-populate fs with known data
    calculator.fs = {
        'total_current_assets': 100.0,
        'total_current_liabilities': 50.0,
        'total_assets': 300.0,
        'retained_earnings': 60.0,
        'pre_tax_income': 40.0, # Assuming this is used as EBIT if interest_expense is 0 or not used in X3 directly
        'interest_expense': 0.0, # For simplicity in this test, assume EBIT = pre_tax_income
        'revenue': 200.0,
        'market_cap': 250.0,
        'total_liabilities': 150.0
    }
    # Expected X values based on above data:
    # X1 = (100 - 50) / 300 = 50 / 300 = 0.16666...
    # X2 = 60 / 300 = 0.2
    # X3 = 40 / 300 = 0.13333... (assuming pre_tax_income is EBIT for this test)
    # X4 = 250 / 150 = 1.66666...
    # X5 = 200 / 300 = 0.66666...

    expected_x1 = (100.0 - 50.0) / 300.0
    expected_x2 = 60.0 / 300.0
    expected_x3 = 40.0 / 300.0 # calculator.X3 uses pre_tax_income - interest_expense
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
    calculator = AltmanZScoreCalculator("DUMMY_EDGE")

    # Case 1: Total Assets = 0
    calculator.fs = {
        'total_current_assets': 100.0, 'total_current_liabilities': 50.0, 'total_assets': 0.0,
        'retained_earnings': 60.0, 'pre_tax_income': 40.0, 'interest_expense': 5.0,
        'revenue': 200.0, 'market_cap': 250.0, 'total_liabilities': 150.0
    }
    assert calculator.X1 == 0 # As per implementation, division by zero in X properties returns 0
    assert calculator.X2 == 0
    assert calculator.X3 == 0
    assert calculator.X5 == 0
    # X4 should still calculate if total_liabilities is not zero
    assert abs(calculator.X4 - (250.0 / 150.0)) < 0.0001
    # calculate_score might return a score if X4 is non-zero and others are zero, or None if it detects total_assets = 0
    # Based on current AltmanZScoreCalculator, if total_assets is 0, calculate_score returns None.
    assert calculator.calculate_score() is None 

    # Case 2: Total Liabilities = 0 (and Total Assets non-zero)
    calculator.fs = {
        'total_current_assets': 100.0, 'total_current_liabilities': 50.0, 'total_assets': 300.0,
        'retained_earnings': 60.0, 'pre_tax_income': 40.0, 'interest_expense': 5.0,
        'revenue': 200.0, 'market_cap': 250.0, 'total_liabilities': 0.0
    }
    assert calculator.X4 == 0 # Division by zero for X4 returns 0
    z_score_tl_zero = calculator.calculate_score() # Should calculate, with X4 contributing 0
    assert z_score_tl_zero is not None
    
    # Expected X values when TL=0
    expected_x1_tl0 = (100.0 - 50.0) / 300.0
    expected_x2_tl0 = 60.0 / 300.0
    expected_x3_tl0 = (40.0 - 5.0) / 300.0 
    expected_x4_tl0 = 0.0 # Market Cap / 0 -> should be 0
    expected_x5_tl0 = 200.0 / 300.0
    expected_z_tl0 = (1.2 * expected_x1_tl0) + (1.4 * expected_x2_tl0) + (3.3 * expected_x3_tl0) + \
                     (0.6 * expected_x4_tl0) + (1.0 * expected_x5_tl0)
    assert abs(z_score_tl_zero - expected_z_tl0) < 0.0001


@patch('altz.altz_calculator.requests.get')
def test_get_score_details(mock_get, mock_response_valid):
    mock_get.return_value = mock_response_valid
    calculator = AltmanZScoreCalculator("TEST")
    
    details = calculator.get_score_details()

    assert details is not None
    assert details['ticker'] == "TEST"
    assert 'z_score' in details
    assert 'X1' in details
    assert 'X2' in details
    assert 'X3' in details
    assert 'X4' in details
    assert 'X5' in details
    assert 'raw_data' in details
    assert details['raw_data']['total_assets'] == 300000000.0

@patch('altz.altz_calculator.requests.get')
def test_init_failure_request_exception(mock_get):
    mock_get.side_effect = requests.exceptions.RequestException("Network Error")
    calculator = AltmanZScoreCalculator("FAIL")
    assert calculator.soup is None
    assert calculator.fs is not None # fs gets initialized to defaults
    for field_value in calculator.fs.values():
        assert field_value == 0.0
    
    details = calculator.get_score_details()
    assert details['z_score'] is None # Cannot calculate score with default 0 data

@patch('altz.altz_calculator.AltmanZScoreCalculator._return_response') # Mocking at a higher level
def test_init_no_response_from_return_response(mock_return_response):
    mock_return_response.return_value = None # _return_response fails to get a page
    
    calculator = AltmanZScoreCalculator("NORESP")
    assert calculator.soup is None
    assert calculator.fs is not None
    for field_value in calculator.fs.values():
        assert field_value == 0.0

    details = calculator.get_score_details()
    assert details['z_score'] is None
```
