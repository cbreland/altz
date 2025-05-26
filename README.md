# Altman Z-Score Analyzer Web Application

## Description

The Altman Z-Score is a formula used to predict the probability that a firm will go into bankruptcy within two years. It uses several income statement and balance sheet values to measure the financial health of a company. A score below 1.81 indicates a company is in financial distress, while a score above 2.99 indicates a company is in a "safe" zone. Scores between 1.81 and 2.99 are in a "grey" area.

This web application allows users to:
*   Input a stock ticker symbol.
*   View the current Altman Z-Score for the company, along with its components (X1-X5 factors) and a risk assessment.
*   See a graph of the company's historical Altman Z-Score trend over the last 5 years.

The application fetches current Z-Score components by scraping financial data from `gurufocus.com` and uses the `yfinance` library to retrieve historical financial statement data and stock prices for historical Z-Score calculations.

## Features

*   **Current Z-Score Calculation**: Displays the latest Altman Z-Score based on data from `gurufocus.com`.
*   **Historical Z-Score Analysis**: Calculates and displays a line graph of the Altman Z-Score for the past 5 years using `yfinance` data.
*   **Risk Assessment**: Provides a qualitative risk assessment (Safe, Grey, Distress Zone) based on the current Z-Score.
*   **Detailed Components**: Shows the values of the five X-factors (X1 to X5) that contribute to the Z-Score.
*   **Responsive Frontend**: User-friendly interface for easy input and clear visualization of results.
*   **Client-Side Validation**: Basic validation for ticker input.
*   **Loading Indicators**: Visual feedback during data fetching.

## Technology Stack

*   **Backend**:
    *   Python 3.x
    *   Flask (for the web framework and API)
    *   `yfinance` (for historical financial data and stock prices)
    *   `requests` (for HTTP requests to `gurufocus.com`)
    *   `BeautifulSoup4` (for parsing HTML from `gurufocus.com`)
    *   `numpy` (for numerical operations, especially with historical data)
*   **Frontend**:
    *   HTML5
    *   CSS3
    *   JavaScript (ES6+)
    *   Chart.js (for rendering the historical Z-Score graph)
*   **Testing**:
    *   `pytest`
    *   `pytest-mock`

## Project Structure

```
/altman_z_score_project      # Root directory (example name)
|-- /altz_webapp            # Main Flask application, frontend and historical data logic
|   |-- /static             # CSS, JavaScript files
|   |   |-- /css
|   |   |   |-- style.css
|   |   |-- /js
|   |       |-- script.js
|   |-- /templates          # HTML templates
|   |   |-- index.html
|   |-- __init__.py
|   |-- main.py             # Flask routes and main app logic
|   |-- historical_analyzer.py # Logic for yfinance data and historical scores
|-- /altz                   # Original Z-Score calculator logic (gurufocus.com based)
|   |-- __init__.py
|   |-- altz_calculator.py
|-- /tests                  # Unit and integration tests
|   |-- __init__.py
|   |-- test_altz_calculator.py
|   |-- test_historical_analyzer.py
|   |-- test_main_api.py
|-- requirements.txt        # Python dependencies
|-- README.md               # This file
```

## Setup and Installation

**Prerequisites**:
*   Python 3.7+ (Python 3.8+ recommended)
*   pip (Python package installer)

**Steps**:

1.  **Clone the repository** (or ensure you have the project files in a directory, e.g., `altman_z_score_project`):
    ```bash
    # If you are cloning:
    # git clone <repository_url>
    # cd altman_z_score_project
    ```

2.  **Create and activate a virtual environment** (recommended):
    Navigate to your project's root directory (e.g., `altman_z_score_project`).
    ```bash
    python -m venv venv
    ```
    *   On macOS and Linux:
        ```bash
        source venv/bin/activate
        ```
    *   On Windows:
        ```bash
        venv\Scripts\activate
        ```

3.  **Install dependencies**:
    Ensure your virtual environment is activated, then run:
    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

1.  **Set the `FLASK_APP` environment variable** (optional, but good practice):
    *   On macOS and Linux:
        ```bash
        export FLASK_APP=altz_webapp/main.py
        # Optional: for development mode which enables debugger and auto-reloader
        export FLASK_ENV=development 
        ```
    *   On Windows (Command Prompt):
        ```bash
        set FLASK_APP=altz_webapp\main.py
        set FLASK_ENV=development
        ```
    *   On Windows (PowerShell):
        ```bash
        $env:FLASK_APP="altz_webapp\main.py"
        $env:FLASK_ENV="development"
        ```

2.  **Run the Flask development server**:
    If you've set `FLASK_APP` (and optionally `FLASK_ENV`), you can use:
    ```bash
    flask run --host=0.0.0.0 --port=5000
    ```
    Alternatively, you can run the `main.py` script directly (as it includes `app.run()`):
    ```bash
    python altz_webapp/main.py
    ```
    This will typically start the server on `http://0.0.0.0:5000/`. The `--host=0.0.0.0` makes it accessible from other devices on your network.

3.  **Access the application**:
    Open your web browser and navigate to `http://localhost:5000` or `http://127.0.0.1:5000`.

## Running Tests

To run the automated tests, ensure your virtual environment is activated and dependencies (including `pytest` and `pytest-mock`) are installed.

Navigate to the root directory of the project (e.g., `altman_z_score_project`) and run:
```bash
pytest
```
This command will automatically discover and execute all test files (typically named `test_*.py` or `*_test.py`) within the `tests` directory and its subdirectories.

## Known Limitations / Future Improvements

*   **Data Source Reliability (Current Score)**: The current Z-Score calculation relies on web scraping `gurufocus.com`. This is prone to breaking if the website's HTML structure changes or if anti-scraping measures are implemented. An API-based solution would be more robust.
*   **Historical Market Cap (yfinance)**: The historical market capitalization calculation uses end-of-period share counts from balance sheets (via `yfinance`) and matches them with historical closing prices. Large intra-period changes in share count (not due to stock splits) might not be perfectly captured, leading to slight inaccuracies in historical X4 values.
*   **Data Availability (yfinance)**: Data from `yfinance` can sometimes have gaps, inconsistencies, or missing fundamental fields for certain tickers, especially for older periods, less common stocks, or companies with recent/complex financial reporting. This might lead to incomplete historical Z-Score charts or errors for some tickers.
*   **Error Handling**: While error handling is implemented for API responses and some calculation issues, it could be further refined for more specific user feedback and more robust backend logging.
*   **Limited Scope of Z-Score Model**: The application calculates the standard Altman Z-Score generally applicable to manufacturing companies. It does not explicitly differentiate or implement models for non-manufacturing companies, private firms, or emerging markets, where different Z-Score coefficients are often recommended.
*   **Frontend Simplicity**: The current frontend is basic. It could be enhanced with more advanced charting features, data export options, or more detailed explanations of the financial terms.

**Potential Future Work**:
*   Integrate with a more reliable API (e.g., Financial Modeling Prep, Alpha Vantage, IEX Cloud, subject to API key and cost considerations) for current financial data to replace `gurufocus.com` scraping.
*   Implement server-side caching for API responses from `yfinance` and other external sources to improve performance and reduce redundant calls.
*   Add user accounts for features like saving favorite tickers or comparing analyses.
*   Expand the range of financial ratios and analyses offered beyond the Altman Z-Score.
*   Provide options for different Z-Score models tailored to various company types (non-manufacturing, private).
*   More sophisticated data validation, cleaning, and imputation strategies for data sourced from `yfinance`.
*   Enhanced UI/UX with more interactive elements, data tables for historical X-factors, and detailed help sections.
```
