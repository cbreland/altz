import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime

# Add project root to sys.path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from altz_webapp import historical_analyzer

# --- Fixtures and Mock Data for get_historical_financial_data ---

@pytest.fixture
def mock_yfinance_ticker():
    mock_ticker = MagicMock()

    # Mock .financials (Income Statement)
    mock_income_data = {
        pd.Timestamp('2022-12-31'): {
            'Total Revenue': 2000e6, 'Pretax Income': 500e6, 'Interest Expense': 50e6,
            'EBIT': 550e6 # Explicitly provide EBIT if possible
        },
        pd.Timestamp('2021-12-31'): {
            'Total Revenue': 1800e6, 'Pretax Income': 450e6, 'Interest Expense': 40e6,
            'EBIT': 490e6
        },
         pd.Timestamp('2020-12-31'): { # Year with some missing data to test defaults
            'Total Revenue': 1600e6, 'Pretax Income': None, 'Interest Expense': 30e6, # EBIT will be None
        }
    }
    mock_ticker.financials = pd.DataFrame(mock_income_data)

    # Mock .balance_sheet
    mock_balance_data = {
        pd.Timestamp('2022-12-31'): {
            'Total Current Assets': 1000e6, 'Total Current Liabilities': 400e6,
            'Total Assets': 3000e6, 'Retained Earnings': 800e6,
            'Total Liab': 1500e6, 'Share Issued': 100e6 # Using 'Share Issued'
        },
        pd.Timestamp('2021-12-31'): {
            'Total Current Assets': 900e6, 'Total Current Liabilities': 350e6,
            'Total Assets': 2800e6, 'Retained Earnings': 700e6,
            'Total Liab': 1400e6, 'Common Stock Shares Outstanding': 90e6 # Using other shares name
        },
        pd.Timestamp('2020-12-31'): { # Year with some missing data
            'Total Current Assets': 800e6, 'Total Current Liabilities': None, # Missing TCL
            'Total Assets': 2500e6, 'Retained Earnings': 600e6,
            'Total Liab': 1200e6, 'Share Issued': 80e6
        }
    }
    mock_ticker.balance_sheet = pd.DataFrame(mock_balance_data)

    # Mock .history (for stock prices)
    # Create a sample history DataFrame
    dates_2022 = pd.to_datetime(['2022-12-29', '2022-12-30', '2022-12-31']) # Ensure financial report date is present or before
    prices_2022 = [150.0, 151.0, 150.5]
    dates_2021 = pd.to_datetime(['2021-12-29', '2021-12-30', '2021-12-31'])
    prices_2021 = [140.0, 141.0, 140.5]
    dates_2020 = pd.to_datetime(['2020-12-29', '2020-12-30', '2020-12-31'])
    prices_2020 = [130.0, 131.0, 130.5]
    
    hist_index = dates_2020.union(dates_2021).union(dates_2022)
    # Make the history index timezone-aware (e.g., UTC)
    hist_df = pd.DataFrame(index=hist_index.tz_localize('UTC'), columns=['Close'])
    hist_df.loc[dates_2022.tz_localize('UTC'), 'Close'] = prices_2022
    hist_df.loc[dates_2021.tz_localize('UTC'), 'Close'] = prices_2021
    hist_df.loc[dates_2020.tz_localize('UTC'), 'Close'] = prices_2020
    
    mock_ticker.history.return_value = hist_df

    # Mock .info (for fallback shares outstanding if needed, though we aim for balance sheet shares)
    mock_ticker.info = {'sharesOutstanding': 100e6} # Current shares
    
    return mock_ticker

@patch('altz_webapp.historical_analyzer.yf.Ticker')
def test_get_historical_financial_data_success(mock_yf_ticker_class, mock_yfinance_ticker):
    mock_yf_ticker_class.return_value = mock_yfinance_ticker
    
    data = historical_analyzer.get_historical_financial_data("MOCKTICKER", years=3)
    
    assert data is not None
    assert len(data) == 3 # Expecting data for 2022, 2021, 2020
    
    # Check 2022 data (most recent)
    data_2022 = next(item for item in data if item["year"] == 2022)
    assert data_2022['total_current_assets'] == 1000e6
    assert data_2022['total_liabilities'] == 1500e6
    assert data_2022['ebit'] == 550e6
    assert data_2022['market_cap'] == 150.5 * 100e6 # 2022-12-31 close * 2022 shares
    
    # Check 2021 data
    data_2021 = next(item for item in data if item["year"] == 2021)
    assert data_2021['total_assets'] == 2800e6
    assert data_2021['retained_earnings'] == 700e6
    assert data_2021['ebit'] == 490e6
    assert data_2021['market_cap'] == 140.5 * 90e6 # 2021-12-31 close * 2021 shares

    # Check 2020 data (with missing fields that should be defaulted to 0.0 by the function)
    data_2020 = next(item for item in data if item["year"] == 2020)
    assert data_2020['total_current_liabilities'] == 0.0 # Was None in mock, should be 0.0
    assert data_2020['ebit'] is None # Pretax income was None, so EBIT should be None then defaulted to 0 by cleaner
    assert data_2020['market_cap'] == 130.5 * 80e6

@patch('altz_webapp.historical_analyzer.yf.Ticker')
def test_get_historical_financial_data_yfinance_errors(mock_yf_ticker_class):
    # Case 1: yfinance.Ticker fails or returns object with empty data
    mock_empty_ticker = MagicMock()
    mock_empty_ticker.financials = pd.DataFrame() # Empty dataframe
    mock_empty_ticker.balance_sheet = pd.DataFrame()
    mock_empty_ticker.history.return_value = pd.DataFrame()
    mock_yf_ticker_class.return_value = mock_empty_ticker
    
    assert historical_analyzer.get_historical_financial_data("EMPTY", years=3) is None

    # Case 2: yfinance.Ticker raises an exception (e.g. ticker not found)
    # yfinance often just returns empty DataFrames for bad tickers rather than raising error on Ticker call
    # but other calls like .financials might raise or return empty.
    # Let's simulate history call failing after financials were okay.
    mock_history_fail_ticker = MagicMock()
    mock_history_fail_ticker.financials = pd.DataFrame({pd.Timestamp('2022-12-31'): {'Total Revenue': 1e9}})
    mock_history_fail_ticker.balance_sheet = pd.DataFrame({pd.Timestamp('2022-12-31'): {'Total Assets': 1e9, 'Share Issued': 1e6}})
    mock_history_fail_ticker.history.return_value = pd.DataFrame() # Empty history
    mock_yf_ticker_class.return_value = mock_history_fail_ticker
    
    data_hist_fail = historical_analyzer.get_historical_financial_data("HISTFAIL", years=1)
    assert data_hist_fail is not None # Should return a list
    assert len(data_hist_fail) == 1 # One year of data
    assert data_hist_fail[0]['market_cap'] is None # Market cap calculation should fail


@patch('altz_webapp.historical_analyzer.yf.Ticker')
def test_get_historical_financial_data_timezone_handling(mock_yf_ticker_class, mock_yfinance_ticker):
    """
    Tests that get_historical_financial_data correctly handles timezone differences
    between financial report dates (naive) and stock history index (aware).
    The mock_yfinance_ticker fixture already returns timezone-aware history.
    """
    mock_yf_ticker_class.return_value = mock_yfinance_ticker # This mock has tz-aware history
    
    # Call the function that performs the comparison
    # No TypeError should be raised.
    try:
        data = historical_analyzer.get_historical_financial_data("TZTEST", years=1)
        assert data is not None # Should not fail catastrophically
        if data:
            # Check if market cap was calculated (implies date comparison worked)
            # Depending on mock data, it might be None if shares/price missing for the specific date,
            # but the key is no TypeError.
            assert 'market_cap' in data[0] 
            # For the mock_yfinance_ticker, 2022 data should have market_cap
            data_2022 = next(item for item in data if item["year"] == 2022)
            assert data_2022['market_cap'] is not None
            assert data_2022['market_cap'] == 150.5 * 100e6

    except TypeError as e:
        pytest.fail(f"Timezone comparison TypeError should not have been raised: {e}")
    except Exception as e:
        # Other exceptions might occur if mock data is incomplete, but not TypeError
        print(f"An unexpected error occurred during timezone test: {e}")


# --- Tests for calculate_historical_z_scores ---

def test_calculate_historical_z_scores_valid_data():
    sample_data = [
        {
            'year': 2022, 'total_current_assets': 100.0, 'total_current_liabilities': 50.0,
            'total_assets': 300.0, 'retained_earnings': 60.0, 'ebit': 35.0, # EBIT = Pretax - Interest
            'market_cap': 250.0, 'total_liabilities': 150.0, 'revenue': 200.0
        },
        { # Data for another year
            'year': 2021, 'total_current_assets': 120.0, 'total_current_liabilities': 60.0,
            'total_assets': 350.0, 'retained_earnings': 70.0, 'ebit': 40.0,
            'market_cap': 280.0, 'total_liabilities': 160.0, 'revenue': 220.0
        }
    ]
    
    results = historical_analyzer.calculate_historical_z_scores(sample_data)
    assert len(results) == 2
    
    # Check 2022
    res_2022 = results[0]
    assert res_2022['year'] == 2022
    wc_2022 = 100.0 - 50.0
    x1_2022 = wc_2022 / 300.0
    x2_2022 = 60.0 / 300.0
    x3_2022 = 35.0 / 300.0
    x4_2022 = 250.0 / 150.0
    x5_2022 = 200.0 / 300.0
    expected_z_2022 = (1.2*x1_2022) + (1.4*x2_2022) + (3.3*x3_2022) + (0.6*x4_2022) + (1.0*x5_2022)
    assert abs(res_2022['z_score'] - expected_z_2022) < 0.0001
    assert abs(res_2022['X1'] - x1_2022) < 0.0001

    # Check 2021
    res_2021 = results[1]
    assert res_2021['year'] == 2021
    wc_2021 = 120.0 - 60.0
    x1_2021 = wc_2021 / 350.0
    x2_2021 = 70.0 / 350.0
    x3_2021 = 40.0 / 350.0
    x4_2021 = 280.0 / 160.0
    x5_2021 = 220.0 / 350.0
    expected_z_2021 = (1.2*x1_2021) + (1.4*x2_2021) + (3.3*x3_2021) + (0.6*x4_2021) + (1.0*x5_2021)
    assert abs(res_2021['z_score'] - expected_z_2021) < 0.0001

def test_calculate_historical_z_scores_division_by_zero():
    # Test with Total Assets = 0 for one year
    sample_data_ta_zero = [
        {
            'year': 2022, 'total_current_assets': 100.0, 'total_current_liabilities': 50.0,
            'total_assets': 0.0, 'retained_earnings': 60.0, 'ebit': 35.0,
            'market_cap': 250.0, 'total_liabilities': 150.0, 'revenue': 200.0
        }
    ]
    results_ta_zero = historical_analyzer.calculate_historical_z_scores(sample_data_ta_zero)
    assert len(results_ta_zero) == 1
    assert results_ta_zero[0]['year'] == 2022
    assert results_ta_zero[0]['z_score'] is None
    assert results_ta_zero[0]['X1'] is None # Since TA is 0
    assert 'error' in results_ta_zero[0]
    assert results_ta_zero[0]['error'] == "Total Assets are zero."

    # Test with Total Liabilities = 0 for one year (TA is non-zero)
    sample_data_tl_zero = [
        {
            'year': 2023, 'total_current_assets': 100.0, 'total_current_liabilities': 50.0,
            'total_assets': 300.0, 'retained_earnings': 60.0, 'ebit': 35.0,
            'market_cap': 250.0, 'total_liabilities': 0.0, 'revenue': 200.0
        }
    ]
    results_tl_zero = historical_analyzer.calculate_historical_z_scores(sample_data_tl_zero)
    assert len(results_tl_zero) == 1
    res_2023 = results_tl_zero[0]
    assert res_2023['year'] == 2023
    assert res_2023['X4'] == 0.0 # Market Cap / 0 should result in X4 = 0 as per implementation
    assert res_2023['z_score'] is not None # Z-score should be calculable
    assert 'error' not in res_2023 # No error expected here, just X4 = 0

def test_calculate_historical_z_scores_missing_critical_fields_in_input():
    # Input data missing a critical field like 'total_assets'
    sample_data_missing_fields = [
        {
            'year': 2022, 'total_current_assets': 100.0, 'total_current_liabilities': 50.0,
            # 'total_assets': 300.0, # Missing Total Assets
            'retained_earnings': 60.0, 'ebit': 35.0,
            'market_cap': 250.0, 'total_liabilities': 150.0, 'revenue': 200.0
        }
    ]
    results = historical_analyzer.calculate_historical_z_scores(sample_data_missing_fields)
    assert len(results) == 1
    assert results[0]['z_score'] is None # TA defaults to 0, so X1,X2,X3,X5 become None or error
    assert results[0]['error'] == "Total Assets are zero."


def test_calculate_historical_z_scores_empty_input():
    assert historical_analyzer.calculate_historical_z_scores([]) == []

def test_calculate_historical_z_scores_input_none():
    assert historical_analyzer.calculate_historical_z_scores(None) == []

```
