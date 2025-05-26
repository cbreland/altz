import pytest
from unittest.mock import patch, MagicMock
import json

# Add project root to sys.path to allow importing altz_webapp
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the Flask app instance from your main application file
# Assuming your Flask app instance is named 'app' in 'altz_webapp.main'
from altz_webapp.main import app as flask_app

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # You might need to configure your app for testing here if it's not already
    # e.g., app.config['TESTING'] = True
    # app.config['DEBUG'] = False
    flask_app.config.update({
        "TESTING": True,
    })
    yield flask_app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

# --- Tests for /api/zscore/<ticker> ---

@patch('altz_webapp.main.AltmanZScoreCalculator') # Patch where it's imported in main.py
def test_get_zscore_success(mock_altman_calculator_class, client):
    # Configure the mock instance that AltmanZScoreCalculator will produce
    mock_calculator_instance = MagicMock()
    mock_calculator_instance.get_score_details.return_value = {
        "ticker": "TEST", "z_score": 2.5, "X1": 0.1, "X2": 0.2, "X3": 0.3, "X4": 0.4, "X5": 0.5,
        "raw_data": {"total_assets": 1000}
    }
    mock_calculator_instance.soup = True # Simulate successful data fetch for initial checks in API
    mock_calculator_instance.fs = {"total_assets": 1000} # Simulate successful data fetch

    mock_altman_calculator_class.return_value = mock_calculator_instance
    
    response = client.get('/api/zscore/TEST')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['ticker'] == "TEST"
    assert data['z_score'] == 2.5

@patch('altz_webapp.main.AltmanZScoreCalculator')
def test_get_zscore_calculator_init_fails_data_fetch(mock_altman_calculator_class, client):
    # Simulate failure during calculator's data fetching (_fetch_and_parse_data)
    mock_calculator_instance = MagicMock()
    mock_calculator_instance.soup = None # This indicates failed fetch in the API logic
    mock_calculator_instance.fs = {} # fs might be empty or default
    mock_altman_calculator_class.return_value = mock_calculator_instance

    response = client.get('/api/zscore/NOFETCH')
    assert response.status_code == 404 # As per API error handling
    data = json.loads(response.data)
    assert "error" in data
    assert "Could not retrieve or parse sufficient financial data" in data["error"]

@patch('altz_webapp.main.AltmanZScoreCalculator')
def test_get_zscore_score_details_none(mock_altman_calculator_class, client):
    mock_calculator_instance = MagicMock()
    mock_calculator_instance.get_score_details.return_value = {"z_score": None, "raw_data": {"total_assets": 0}} # Z-score is None
    mock_calculator_instance.soup = True 
    mock_calculator_instance.fs = {"total_assets": 0} # total_assets 0 can also lead to None z_score in details
    mock_altman_calculator_class.return_value = mock_calculator_instance
    
    response = client.get('/api/zscore/NODETAILS')
    assert response.status_code == 404 # Changed from 500, as this indicates insufficient data
    data = json.loads(response.data)
    assert "error" in data
    assert "Could not calculate Z-Score" in data["error"]
    assert "insufficient data for one or more X factors" in data["error"]

@patch('altz_webapp.main.AltmanZScoreCalculator')
def test_get_zscore_calculator_exception(mock_altman_calculator_class, client):
    # Simulate an unexpected exception during calculator instantiation or method call
    mock_altman_calculator_class.side_effect = Exception("Unexpected internal error")
    
    response = client.get('/api/zscore/CRASH')
    assert response.status_code == 500
    data = json.loads(response.data)
    assert "error" in data
    assert "An unexpected error occurred: Unexpected internal error" in data["error"]

# --- Tests for /api/historical_zscore/<ticker> ---

@patch('altz_webapp.main.historical_analyzer.get_historical_financial_data')
@patch('altz_webapp.main.historical_analyzer.calculate_historical_z_scores')
def test_get_historical_zscore_success(mock_calculate_scores, mock_get_data, client):
    mock_get_data.return_value = [{'year': 2022, 'total_assets': 1000}] # Sample raw data
    mock_calculate_scores.return_value = [{'year': 2022, 'z_score': 3.1, 'X1':0.1, 'X2':0.2, 'X3':0.3, 'X4':0.4, 'X5':0.5}]
    
    response = client.get('/api/historical_zscore/HISTTEST?years=1')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['ticker'] == "HISTTEST"
    assert len(data['historical_z_scores']) == 1
    assert data['historical_z_scores'][0]['year'] == 2022
    assert data['historical_z_scores'][0]['z_score'] == 3.1

@patch('altz_webapp.main.historical_analyzer.get_historical_financial_data')
def test_get_historical_zscore_get_data_none(mock_get_data, client):
    mock_get_data.return_value = None # Simulate yfinance failing to get any data
    
    response = client.get('/api/historical_zscore/NOHISTDATA')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert "error" in data
    assert "Could not retrieve historical financial data" in data["error"]

@patch('altz_webapp.main.historical_analyzer.get_historical_financial_data')
def test_get_historical_zscore_get_data_empty_list(mock_get_data, client):
    mock_get_data.return_value = [] # Simulate data processing resulting in no valid periods
    
    response = client.get('/api/historical_zscore/EMPTYHIST')
    assert response.status_code == 404 
    data = json.loads(response.data)
    assert "error" in data
    assert "No valid historical data periods found" in data["error"]

@patch('altz_webapp.main.historical_analyzer.get_historical_financial_data')
@patch('altz_webapp.main.historical_analyzer.calculate_historical_z_scores')
def test_get_historical_zscore_calculate_scores_empty(mock_calculate_scores, mock_get_data, client):
    mock_get_data.return_value = [{'year': 2022, 'total_assets': 0}] # Data that would lead to calculation issues
    mock_calculate_scores.return_value = [] # Simulate calculation failing for all periods
    
    response = client.get('/api/historical_zscore/CALCFAIL')
    assert response.status_code == 500
    data = json.loads(response.data)
    assert "error" in data
    assert "Could not calculate any historical Z-Scores" in data["error"]

@patch('altz_webapp.main.historical_analyzer.get_historical_financial_data')
def test_get_historical_zscore_analyzer_exception(mock_get_data, client):
    mock_get_data.side_effect = Exception("YFinance unexpected error")
    
    response = client.get('/api/historical_zscore/YFINCRASH')
    assert response.status_code == 500
    data = json.loads(response.data)
    assert "error" in data
    assert "An unexpected server error occurred: YFinance unexpected error" in data["error"]

def test_get_historical_zscore_invalid_years_param(client):
    response = client.get('/api/historical_zscore/TEST?years=0') # years < 1
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "Number of years must be between 1 and 10" in data["error"]

    response = client.get('/api/historical_zscore/TEST?years=11') # years > 10
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "Number of years must be between 1 and 10" in data["error"]

    response = client.get('/api/historical_zscore/TEST?years=abc') # years not int
    assert response.status_code == 400 # Flask's type conversion for args will fail
    data = json.loads(response.data)
    assert "error" in data # Default Flask error for bad request parameter type
    # The exact message might vary based on Flask version, so check for generic error presence
```
