from flask import Flask, jsonify, request, render_template # Added render_template
import sys
import os

# Add the parent directory to the Python path to allow imports from 'altz'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from altz.altz_calculator import AltmanZScoreCalculator
from altz_webapp import historical_analyzer # Import the new module

app = Flask(__name__)

@app.route('/api/zscore/<string:ticker>', methods=['GET'])
def get_zscore(ticker):
    try:
        # Ensure ticker is uppercase as expected by the calculator
        calculator = AltmanZScoreCalculator(ticker.upper())
        
        # Check if financial data was successfully fetched and parsed
        # The _fetch_and_parse_data method in the calculator now initializes fs with zeros
        # if data retrieval fails. We need a more robust check here.
        # A simple check could be if 'total_assets' (a critical denominator) is non-zero.
        # Or, more directly, if the soup object is None after initialization.
        if calculator.soup is None or not calculator.fs or calculator.fs.get('total_assets', 0) == 0:
            # This indicates that data fetching/parsing likely failed in _fetch_and_parse_data
            # or critical data like 'total_assets' is missing/zero.
             return jsonify({
                "error": f"Could not retrieve or parse sufficient financial data for ticker {ticker.upper()}. "
                         f"The data source (gurufocus.com) may not have the required information or might be temporarily unavailable."
            }), 404

        score_details = calculator.get_score_details()

        if score_details is None:
            return jsonify({"error": f"Could not calculate Z-Score for {ticker.upper()} due to missing data components."}), 500
        
        if score_details.get('z_score') is None:
            # This case handles when data was fetched but some specific component for Z-score was missing
            # leading to z_score being None (as per get_score_details logic)
            raw_data_summary = {k: v for k, v in score_details.get('raw_data', {}).items() if v is not None and v != 0} # Show non-zero raw data
            return jsonify({
                "error": f"Could not calculate Z-Score for {ticker.upper()} due to insufficient data for one or more X factors. "
                         f"Please check the raw data returned for completeness. Ticker might not be a manufacturing company or data is sparse.",
                "raw_data_preview": raw_data_summary
            }), 404
            
        return jsonify(score_details), 200

    except Exception as e:
        # Catch any other unexpected exceptions during calculator instantiation or method calls
        # These could be network errors not caught by `_return_response`, or other unexpected issues.
        app.logger.error(f"An unexpected error occurred while processing ticker {ticker.upper()}: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@app.route('/api/historical_zscore/<string:ticker>', methods=['GET'])
def get_historical_zscore(ticker):
    try:
        num_years = request.args.get('years', default=5, type=int)
        if not 1 <= num_years <= 10: # Basic validation for number of years
            return jsonify({"error": "Number of years must be between 1 and 10."}), 400

        raw_historical_data = historical_analyzer.get_historical_financial_data(ticker.upper(), years=num_years)

        if raw_historical_data is None:
            return jsonify({"error": f"Could not retrieve historical financial data for {ticker.upper()} from yfinance. "
                                     f"The ticker may be invalid, delisted, or lack sufficient data."}), 404
        
        if not raw_historical_data: # Empty list means some issue during processing or no valid years found
            return jsonify({"error": f"No valid historical data periods found for {ticker.upper()} after processing. "
                                     f"Data might be too sparse or inconsistent for analysis."}), 404

        historical_z_scores = historical_analyzer.calculate_historical_z_scores(raw_historical_data)

        if not historical_z_scores:
            # This might happen if all years had issues during Z-score calculation (e.g. all had total_assets=0)
            return jsonify({
                "error": f"Could not calculate any historical Z-Scores for {ticker.upper()}. "
                         f"This might be due to missing critical data (like Total Assets) for all reported periods.",
                "retrieved_data_summary": f"Retrieved {len(raw_historical_data)} period(s) of raw data but calculations failed for all."
            }), 500
            
        # Successfully calculated some historical scores
        # It's possible some years in historical_z_scores list have 'z_score': None if that specific year failed.
        # The frontend can handle displaying this.
        return jsonify({
            "ticker": ticker.upper(),
            "historical_z_scores": historical_z_scores
        }), 200

    except Exception as e:
        app.logger.error(f"An unexpected error occurred while processing historical Z-Score for {ticker.upper()}: {str(e)}")
        import traceback
        traceback.print_exc() # For more detailed server-side logging
        return jsonify({"error": f"An unexpected server error occurred: {str(e)}"}), 500

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # Note: For development, debug=True is fine. For production, use a WSGI server like Gunicorn.
    app.run(debug=True, host='0.0.0.0', port=5000)
