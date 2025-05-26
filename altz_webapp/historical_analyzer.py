import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

def get_historical_financial_data(ticker_symbol, years=5):
    """
    Fetches and processes historical financial data from yfinance for a given ticker.

    Args:
        ticker_symbol (str): The stock ticker symbol.
        years (int): The number of past years of data to retrieve.

    Returns:
        list: A list of dictionaries, where each dictionary contains financial data
              for a year, or None if data retrieval fails significantly.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)

        # Fetch annual financial statements
        # .financials is income statement, .balance_sheet is balance sheet
        # These are typically DataFrames with columns as years (or period-end dates)
        # and rows as financial items.
        income_stmt_annual = ticker.financials
        balance_sheet_annual = ticker.balance_sheet
        
        if income_stmt_annual.empty or balance_sheet_annual.empty:
            print(f"No financial statements found for {ticker_symbol} using yfinance.")
            return None

        # Transpose so that years are rows for easier iteration if needed,
        # but it's often easier to work with financial items as rows and years as columns.
        # Let's keep them as yfinance provides (Items x Years)

        # Fetch historical market data for stock prices (annual interval)
        # To get end-of-year prices, we can use '1y' interval.
        # We need prices for roughly the same period as financial statements.
        # Financial statement columns are often like '2023-09-30', '2022-09-30'.
        # We need to align these.
        
        # Get available years from financial statements (use balance sheet as reference)
        # Columns are datetime objects, convert to year integer
        available_years = sorted([col.year for col in balance_sheet_annual.columns], reverse=True)
        
        if not available_years:
            print(f"No valid years found in financial statements for {ticker_symbol}.")
            return None

        # Limit to the number of years requested
        target_years = available_years[:years]
        if not target_years:
             print(f"Could not identify target years for {ticker_symbol} from available data: {available_years}")
             return None

        # Fetch historical stock price data to get closing prices around year-end for market cap
        # Fetching for a slightly longer period to ensure we have data points
        # yfinance 'period' for history: e.g., "5y" for 5 years.
        # We need daily data to pick specific end-of-financial-year prices.
        # The financial year end can be different from calendar year end.
        
        # Let's get daily data for the required span to ensure we can find closing prices
        # near the financial statement dates.
        history_start_date = f"{min(target_years) - 1}-01-01" # Start a bit earlier
        history_end_date = f"{max(target_years) + 1}-12-31"   # End a bit later
        
        hist_prices_daily = ticker.history(start=history_start_date, end=history_end_date, interval="1d")
        if hist_prices_daily.empty:
            print(f"Could not fetch historical price data for {ticker_symbol}.")
            # We might still proceed if we have current shares outstanding and use current market cap as proxy for all years,
            # but this is a big simplification. For now, let's consider it a failure for historical analysis.
            return None

        historical_data_list = []

        for year in target_years:
            # Find the specific column in financials that corresponds to this year.
            # Financial statements columns are datetime objects representing the period end.
            # We need to find the column that ends in the target 'year'.
            
            # Find the financial statement column for the current 'year'
            # This assumes statements are year-ending. Some companies have fiscal years like 2023-06-30.
            # We need to find the column that corresponds to the fiscal year 'year'.
            
            target_col_income = None
            for col_date in income_stmt_annual.columns:
                if col_date.year == year:
                    target_col_income = col_date
                    break
            
            target_col_balance = None
            for col_date in balance_sheet_annual.columns:
                if col_date.year == year:
                    target_col_balance = col_date
                    break

            if target_col_income is None or target_col_balance is None:
                print(f"Warning: Missing financial statement data for {ticker_symbol} for year {year}. Skipping.")
                continue

            data_for_year = {'year': year}

            # --- Extract from Balance Sheet ---
            # Common yfinance field names (can vary, be cautious):
            # 'Total Current Assets', 'Total Current Liabilities', 'Total Assets', 
            # 'Retained Earnings', 'Total Liab' (for Total Liabilities)
            # 'Common Stock Shares Outstanding'
            
            bs_series = balance_sheet_annual[target_col_balance]
            data_for_year['total_current_assets'] = bs_series.get('Total Current Assets', bs_series.get('Current Assets'))
            data_for_year['total_current_liabilities'] = bs_series.get('Total Current Liabilities', bs_series.get('Current Liabilities'))
            data_for_year['total_assets'] = bs_series.get('Total Assets', bs_series.get('Assets'))
            data_for_year['retained_earnings'] = bs_series.get('Retained Earnings')
            data_for_year['total_liabilities'] = bs_series.get('Total Liab', bs_series.get('Liabilities Net Minority Interest', bs_series.get('Total Liabilities Net Minority Interest')))
            
            shares_outstanding_hist = bs_series.get('Share Issued', bs_series.get('Common Stock Equity', bs_series.get('Ordinary Shares Number'))) # Trying various common names
            if shares_outstanding_hist is None : # Fallback to another common name
                shares_outstanding_hist = bs_series.get('Common Stock Shares Outstanding')


            # --- Extract from Income Statement ---
            # Common yfinance field names:
            # 'Total Revenue', 'Pretax Income', 'Interest Expense', 'EBIT' (Earnings Before Interest and Taxes)
            is_series = income_stmt_annual[target_col_income]
            data_for_year['revenue'] = is_series.get('Total Revenue', is_series.get('Revenues'))
            
            # EBIT logic: Prefer 'EBIT', then 'Pretax Income'. 
            # If 'Pretax Income' is used, Interest Expense is typically already deducted.
            # For Z-score, we need Earnings Before Interest and Taxes.
            ebit_val = is_series.get('EBIT', is_series.get('Earnings Before Interest and Taxes'))
            if ebit_val is None:
                pretax_income = is_series.get('Pretax Income')
                interest_expense_is = is_series.get('Interest Expense') # Interest expense on Income Statement
                if pretax_income is not None and interest_expense_is is not None:
                     # This assumes Pretax Income is EBT. EBIT = EBT + Interest Expense
                     # However, if Pretax Income on yfinance is already before interest, this is wrong.
                     # For now, use Pretax Income as proxy if EBIT is missing, as per subtask general guidance.
                     # A more robust solution would clarify yfinance's exact definitions.
                    ebit_val = pretax_income 
                else:
                    ebit_val = None # If Pretax Income is also None
            data_for_year['ebit'] = ebit_val
            data_for_year['interest_expense'] = is_series.get('Interest Expense')


            # --- Market Cap Calculation ---
            # Use closing price at the financial statement date (target_col_balance)
            # Find the closest available trading day's closing price in hist_prices_daily
            
            closing_price = None
            # Ensure target_col_balance is a valid timestamp before proceeding
            if pd.isna(target_col_balance):
                print(f"Warning: Invalid financial report date (target_col_balance) for {ticker_symbol} in {year}. Cannot calculate market cap.")
            elif hist_prices_daily.index.empty:
                print(f"Warning: No historical price data available for {ticker_symbol}. Cannot calculate market cap for {year}.")
            else:
                # financial_report_date is derived from balance sheet column, typically just a date (naive)
                financial_report_date_naive = pd.Timestamp(target_col_balance.date())

                # Timezone synchronization
                price_index_tz = getattr(hist_prices_daily.index, 'tz', None)
                
                financial_report_date_for_comparison = financial_report_date_naive
                if price_index_tz is not None: # If price index is timezone-aware
                    # Localize the naive financial_report_date to the price index's timezone
                    try:
                        financial_report_date_for_comparison = financial_report_date_naive.tz_localize(price_index_tz)
                    except Exception as tze: # Handle cases like ambiguous time during DST change if date had time part
                         print(f"Warning: Could not localize financial_report_date {financial_report_date_naive} to {price_index_tz} for {ticker_symbol}, year {year}: {tze}. Using naive comparison or UTC.")
                         # Fallback or make both UTC for comparison
                         financial_report_date_for_comparison = financial_report_date_naive.tz_localize('UTC')
                         hist_prices_daily_index_for_comparison = hist_prices_daily.index.tz_convert('UTC')
                else: # Price index is naive
                    hist_prices_daily_index_for_comparison = hist_prices_daily.index # Use as is


                # Try to find price on the exact date (after potential timezone alignment)
                if financial_report_date_for_comparison in hist_prices_daily_index_for_comparison:
                    closing_price = hist_prices_daily.loc[financial_report_date_for_comparison, 'Close']
                else:
                    # Get the index of the closest prior date
                    # Ensure hist_prices_daily.index (or its tz-converted version) is sorted (usually is)
                    prior_dates = hist_prices_daily_index_for_comparison[hist_prices_daily_index_for_comparison <= financial_report_date_for_comparison]
                    if not prior_dates.empty:
                        closest_date = prior_dates[-1] 
                        closing_price = hist_prices_daily.loc[closest_date, 'Close']
                    # else: closing_price remains None if no prior date found
            
            if closing_price is not None and shares_outstanding_hist is not None:
                data_for_year['market_cap'] = closing_price * shares_outstanding_hist
            else:
                data_for_year['market_cap'] = None
                print(f"Warning: Could not calculate market cap for {ticker_symbol} for {year} due to missing price or shares data.")
                print(f"Debug: Closing Price: {closing_price}, Shares Outstanding (hist): {shares_outstanding_hist} for report date {financial_report_date}")


            # Replace any None/NaN with 0 for calculation purposes later, but log warnings.
            # This is a simplification; in a real scenario, how to handle missing data (e.g., skip year)
            # would be a business decision.
            cleaned_data_for_year = {}
            all_required_present = True
            for key, value in data_for_year.items():
                if value is None or (isinstance(value, (int, float)) and np.isnan(value)):
                    print(f"Warning: Missing value for '{key}' for {ticker_symbol} in {year}. Defaulting to 0.")
                    cleaned_data_for_year[key] = 0.0
                    if key not in ['interest_expense']: # Interest expense can be legitimately zero
                        if key not in ['retained_earnings'] or data_for_year.get('ebit', 0) < 0 : # RE can be negative
                             all_required_present = False # Mark as incomplete if critical data is missing
                else:
                    cleaned_data_for_year[key] = value
            
            if all_required_present or year == data_for_year['year']: # Still add if year is present
                 historical_data_list.append(cleaned_data_for_year)

        return historical_data_list

    except Exception as e:
        print(f"An error occurred in get_historical_financial_data for {ticker_symbol}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def calculate_historical_z_scores(historical_financial_data):
    """
    Calculates Altman Z-Scores for a list of historical financial data.

    Args:
        historical_financial_data (list): List of dicts, from get_historical_financial_data.

    Returns:
        list: List of dicts, each containing year, Z-Score, and X-factors.
    """
    if not historical_financial_data:
        return []

    historical_z_scores = []

    for data_year in historical_financial_data:
        year = data_year.get('year')
        tca = data_year.get('total_current_assets', 0.0)
        tcl = data_year.get('total_current_liabilities', 0.0)
        ta = data_year.get('total_assets', 0.0)
        re = data_year.get('retained_earnings', 0.0)
        ebit = data_year.get('ebit', 0.0) # This is Earnings Before Interest and Tax
        mcap = data_year.get('market_cap', 0.0)
        tl = data_year.get('total_liabilities', 0.0)
        rev = data_year.get('revenue', 0.0)

        try:
            # Denominator checks
            if ta == 0:
                print(f"Warning: Total Assets is zero for {year}. Cannot calculate X1, X2, X3, X5. Skipping Z-Score for this year.")
                historical_z_scores.append({'year': year, 'z_score': None, 'X1': None, 'X2': None, 'X3': None, 'X4': None, 'X5': None, 'error': "Total Assets are zero."})
                continue
            if tl == 0: # Total Liabilities for X4
                # Market cap might also be zero if stock wasn't trading / data missing
                print(f"Warning: Total Liabilities is zero for {year}. Cannot calculate X4. X4 will be zero.")
                x4 = 0.0 # Or handle as error for the year if X4 is critical
            else:
                x4 = mcap / tl

            wc = tca - tcl  # Working Capital
            
            x1 = wc / ta
            x2 = re / ta
            x3 = ebit / ta 
            # x4 calculated above
            x5 = rev / ta

            z_score = (1.2 * x1) + (1.4 * x2) + (3.3 * x3) + (0.6 * x4) + (1.0 * x5)
            
            historical_z_scores.append({
                'year': year,
                'z_score': round(z_score, 4) if z_score is not None else None,
                'X1': round(x1, 4) if x1 is not None else None,
                'X2': round(x2, 4) if x2 is not None else None,
                'X3': round(x3, 4) if x3 is not None else None,
                'X4': round(x4, 4) if x4 is not None else None,
                'X5': round(x5, 4) if x5 is not None else None
            })

        except ZeroDivisionError as zde:
            print(f"Error calculating Z-Score for year {year} due to division by zero: {str(zde)}")
            historical_z_scores.append({'year': year, 'z_score': None, 'X1': None, 'X2': None, 'X3': None, 'X4': None, 'X5': None, 'error': str(zde)})
        except Exception as e:
            print(f"Unexpected error calculating Z-Score for year {year}: {str(e)}")
            historical_z_scores.append({'year': year, 'z_score': None, 'X1': None, 'X2': None, 'X3': None, 'X4': None, 'X5': None, 'error': str(e)})
            
    return historical_z_scores

if __name__ == '__main__':
    # Example Usage (for testing this module directly)
    # Replace 'AAPL' with a ticker you want to test
    # test_ticker = 'MSFT' 
    # print(f"--- Fetching historical data for {test_ticker} ---")
    # raw_data = get_historical_financial_data(test_ticker, years=5)
    
    # if raw_data:
    #     print(f"\\n--- Raw Data for {test_ticker} (first year example) ---")
    #     if raw_data:
    #         print(raw_data[0])
        
    #     print(f"\\n--- Calculating historical Z-Scores for {test_ticker} ---")
    #     z_scores_history = calculate_historical_z_scores(raw_data)
        
    #     if z_scores_history:
    #         for record in z_scores_history:
    #             print(record)
    #     else:
    #         print("Could not calculate historical Z-Scores.")
    # else:
    #     print(f"Could not retrieve historical data for {test_ticker}.")

    # Example with a ticker that might have less data or different fiscal year
    # test_ticker_intl = "BABA" # Alibaba, to check non-US company handling
    # print(f"\\n--- Fetching historical data for {test_ticker_intl} ---")
    # raw_data_intl = get_historical_financial_data(test_ticker_intl, years=3)
    # if raw_data_intl:
    #     print(f"\\n--- Raw Data for {test_ticker_intl} (first year example) ---")
    #     if raw_data_intl:
    #        print(raw_data_intl[0])
    #     z_scores_history_intl = calculate_historical_z_scores(raw_data_intl)
    #     print(f"\\n--- Z-Scores for {test_ticker_intl} ---")
    #     for record in z_scores_history_intl:
    #         print(record)
    # else:
    #     print(f"Could not retrieve historical data for {test_ticker_intl}.")
    pass
