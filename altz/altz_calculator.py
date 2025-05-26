import requests
from bs4 import BeautifulSoup as bs

class AltmanZScoreCalculator:
    FIELDS = {
        'total_current_assets': 'Total Current Assets was ',
        'total_current_liabilities':'Total Current Liabilities was ',
        'total_assets': 'Total Assets was ',
        'retained_earnings': 'Retained Earnings was ',
        'pre_tax_income': 'Pre-Tax Income was ',
        'interest_expense': 'Interest Expense was ',
        'revenue': 'Revenue was ',
        'market_cap': 'Market Cap (Today) was ',
        'total_liabilities': 'Total Liabilities was '
    }

    MARKETS = ['NYSE', 'NAS'] # Potentially add other markets if needed

    def __init__(self, ticker):
        self.ticker = ticker.upper()
        self.soup = None
        self.fs = {} # Financial statement data
        self._fetch_and_parse_data()

    def _fetch_and_parse_data(self):
        response = self._return_response()
        if response:
            self.soup = bs(response.text, 'html.parser')
            self.fs = self._financial_data()
        else:
            # Handle case where data is not found or response is None
            print(f"Warning: Could not retrieve or parse data for ticker {self.ticker}")
            self.fs = {key: 0 for key in self.FIELDS.keys()} # Initialize with zeros or handle error appropriately

    def _return_response(self):
        """
        Fetches financial data page from gurufocus.com for the given ticker.
        Tries different markets if the first one fails.
        """
        for market in self.MARKETS:
            url = f'https://www.gurufocus.com/term/zscore/{market}:{self.ticker}/Altman-Z-Score'
            try:
                # print(f"Trying URL: {url}") # Optional: for debugging
                response = requests.get(url, timeout=10) # Added timeout
                response.raise_for_status() # Raise HTTPError for bad responses (4XX or 5XX)
                if "does not have enough data to calculate Altman Z-Score" not in response.text and "Page Not Found" not in response.text:
                    return response
            except requests.exceptions.RequestException as e:
                print(f"Request failed for {url}: {e}")
                continue # Try next market
        print(f"Data not found for ticker {self.ticker} in markets: {', '.join(self.MARKETS)}")
        return None

    def _financial_data(self):
        """
        Parses the HTML soup to extract financial data points.
        Returns a dictionary of the financial data.
        """
        if not self.soup:
            return {key: 0 for key in self.FIELDS.keys()} # Return default if soup is not available

        z_data_dict = {}
        
        # The parsing logic from the notebook: find <p> tag at index 19.
        # This is fragile and might break if gurufocus.com changes its HTML structure.
        # A more robust parser would use specific IDs, classes, or more resilient search patterns.
        try:
            data_paragraph = self.soup.find_all("p")
            if len(data_paragraph) > 19:
                data_text = data_paragraph[19].text
            else: # Fallback or error if the expected paragraph isn't there
                print(f"Warning: Could not find the data paragraph for {self.ticker}. Data might be incomplete.")
                return {key: 0 for key in self.FIELDS.keys()}

            for row in data_text.split("\\n"):
                for key, value_prefix in self.FIELDS.items():
                    if value_prefix in row:
                        z_data_dict[key] = self._clear_characters(row, value_prefix)
            
            # Ensure all fields are present, if not, fill with 0 or handle error
            for field in self.FIELDS.keys():
                if field not in z_data_dict:
                    # print(f"Warning: Field '{field}' not found for {self.ticker}. Defaulting to 0.")
                    z_data_dict[field] = 0.0 # Default to float 0.0

        except Exception as e:
            print(f"Error parsing financial data for {self.ticker}: {e}")
            return {key: 0 for key in self.FIELDS.keys()}
            
        return z_data_dict

    def _clear_characters(self, row_text, name_prefix):
        """
        Helper function to clean and convert financial figure strings to float.
        """
        # print(f"Raw text for {name_prefix}: {row_text}") # Debugging
        row_val_str = row_text.split(name_prefix)[-1].split("=")[-1]
        remove_chars = ["$", ",", "Mil.", " "]
        for char_to_remove in remove_chars:
            row_val_str = row_val_str.replace(char_to_remove, "")
        try:
            # Assuming "Mil." means millions
            return float(row_val_str) * 1000 * 1000
        except ValueError:
            # print(f"Warning: Could not convert '{row_val_str}' to float for {name_prefix}. Defaulting to 0.")
            return 0.0


    @property
    def X1(self): # Working Capital / Total Assets
        if self.fs.get('total_assets') == 0: return 0
        working_capital = (
            self.fs.get('total_current_assets', 0) -
            self.fs.get('total_current_liabilities', 0)
        )
        return working_capital / self.fs['total_assets']

    @property
    def X2(self): # Retained Earnings / Total Assets
        if self.fs.get('total_assets') == 0: return 0
        return self.fs.get('retained_earnings', 0) / self.fs['total_assets']

    @property
    def X3(self): # Earnings Before Interest and Taxes (EBIT) / Total Assets
        # EBIT in the notebook is Pre-Tax Income - Interest Expense. 
        # This might be slightly different from standard EBIT if taxes are already excluded from Pre-Tax Income.
        # For consistency with the notebook, we use their definition.
        if self.fs.get('total_assets') == 0: return 0
        ebit = (
            self.fs.get('pre_tax_income', 0) - # Assuming this is Earnings Before Tax (EBT)
            self.fs.get('interest_expense', 0) 
        )
        # The notebook uses pre_tax_income - interest_expense.
        # Gurufocus might provide EBIT directly, or EBT.
        # If 'pre_tax_income' is actually EBT, then EBT - Interest Expense is not EBIT.
        # EBIT = Net Income + Interest + Taxes. Or, more simply, Revenue - COGS - Operating Expenses.
        # The notebook calls it EBITA, which is unusual. Assuming it's a proxy for EBIT.
        return ebit / self.fs['total_assets']

    @property
    def X4(self): # Market Cap / Total Liabilities
        if self.fs.get('total_liabilities') == 0: return 0
        return self.fs.get('market_cap', 0) / self.fs['total_liabilities']

    @property
    def X5(self): # Revenue / Total Assets
        if self.fs.get('total_assets') == 0: return 0
        return self.fs.get('revenue', 0) / self.fs['total_assets']

    def calculate_score(self):
        """
        Calculates the Altman Z-Score.
        Formula for publicly traded manufacturing companies:
        Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5
        """
        # Check if all necessary data was fetched
        if not self.fs or any(val == 0 for key, val in self.fs.items() if key in ['total_assets']): # total_assets is a common denominator
            # If total_assets is 0, it means data wasn't properly fetched or ticker is problematic.
            # Individual X properties already handle division by zero for their specific cases.
            # However, if fs itself is empty or total_assets is 0, it indicates a larger issue.
            # print(f"Cannot calculate Z-score for {self.ticker} due to missing critical data (e.g., total_assets).")
            return None # Or raise an error, or return a specific indicator like NaN

        try:
            z_score = (1.2 * self.X1) + \
                      (1.4 * self.X2) + \
                      (3.3 * self.X3) + \
                      (0.6 * self.X4) + \
                      (1.0 * self.X5)
            return z_score
        except TypeError: # Handles cases where some X values might be None if fs data was incomplete
            # print(f"Cannot calculate Z-score for {self.ticker} due to incomplete data for X ratios.")
            return None


    def get_score_details(self):
        """
        Returns a dictionary with the Z-Score, its components (X1-X5),
        and the raw financial data used.
        """
        z_score = self.calculate_score()
        details = {
            'ticker': self.ticker,
            'z_score': z_score,
            'X1': self.X1 if z_score is not None else None,
            'X2': self.X2 if z_score is not None else None,
            'X3': self.X3 if z_score is not None else None,
            'X4': self.X4 if z_score is not None else None,
            'X5': self.X5 if z_score is not None else None,
            'raw_data': self.fs
        }
        return details

    # Methods for interactive analysis (from the notebook)
    # These might need adaptation or could be part of a separate utility/testing script
    def mod_i(self, amt_str, field_key, by_symbol="$"):
        """
        Modifies a financial statement item by increasing it.
        amt_str: amount to increase by (as string, e.g., "10000", "0.10")
        field_key: dictionary key of the item in self.fs (e.g., 'revenue')
        by_symbol: "$" for absolute amount, "%" for percentage
        """
        try:
            amt = float(str(amt_str).replace(",", ""))
        except ValueError:
            print(f"Invalid amount for modification: {amt_str}")
            return "Invalid amount"

        initial_value = self.fs.get(field_key)
        if initial_value is None:
            print(f"Field '{field_key}' not found in financial data.")
            return "Incorrect Field"

        print(f"Initial {field_key} value: {'${:,.2f}'.format(round(initial_value, 2))}")
        
        modification_amount = 0
        if by_symbol == "$":
            modification_amount = amt
        elif by_symbol == "%":
            modification_amount = initial_value * amt # amt should be like 0.10 for 10%
        else:
            print("Invalid 'by' symbol. Use '$' or '%'.")
            return "Invalid 'by' symbol"

        self.fs[field_key] += modification_amount
        print(f"Modified {field_key} value: {'${:,.2f}'.format(round(self.fs[field_key], 2))}")

    def mod_d(self, amt_str, field_key, by_symbol="$"):
        """
        Modifies a financial statement item by decreasing it.
        amt_str: amount to decrease by (as string, e.g., "10000", "0.10")
        field_key: dictionary key of the item in self.fs (e.g., 'revenue')
        by_symbol: "$" for absolute amount, "%" for percentage
        """
        try:
            amt = float(str(amt_str).replace(",", ""))
        except ValueError:
            print(f"Invalid amount for modification: {amt_str}")
            return "Invalid amount"

        initial_value = self.fs.get(field_key)
        if initial_value is None:
            print(f"Field '{field_key}' not found in financial data.")
            return "Incorrect Field"

        print(f"Initial {field_key} value: {'${:,.2f}'.format(round(initial_value, 2))}")

        modification_amount = 0
        if by_symbol == "$":
            modification_amount = amt
        elif by_symbol == "%":
            modification_amount = initial_value * amt # amt should be like 0.10 for 10%
        else:
            print("Invalid 'by' symbol. Use '$' or '%'.")
            return "Invalid 'by' symbol"
            
        self.fs[field_key] -= modification_amount
        print(f"Modified {field_key} value: {'${:,.2f}'.format(round(self.fs[field_key], 2))}")

    def reset_financial_data(self):
        """
        Resets financial data to the initially fetched values.
        This requires storing the original data if mod_i/mod_d are used extensively.
        For now, it re-fetches and parses.
        """
        print("Resetting financial data by re-fetching and parsing...")
        self._fetch_and_parse_data()
        print("Financial data has been reset.")

if __name__ == '__main__':
    # Example Usage:
    # Note: This part is for testing the module directly.
    # In a real application, you'd import AltmanZScoreCalculator and use it.
    
    # Test with a ticker that likely has data
    # calculator = AltmanZScoreCalculator("MSFT") 
    # details = calculator.get_score_details()
    # if details and details['z_score'] is not None:
    #     print(f"\\n--- Altman Z-Score Details for {details['ticker']} ---")
    #     print(f"Z-Score: {details['z_score']:.4f}")
    #     print(f"X1 (Working Capital / Total Assets): {details['X1']:.4f}")
    #     print(f"X2 (Retained Earnings / Total Assets): {details['X2']:.4f}")
    #     print(f"X3 (EBIT / Total Assets): {details['X3']:.4f}")
    #     print(f"X4 (Market Cap / Total Liabilities): {details['X4']:.4f}")
    #     print(f"X5 (Revenue / Total Assets): {details['X5']:.4f}")
    #     print("\\n--- Raw Data ---")
    #     for key, value in details['raw_data'].items():
    #         if isinstance(value, float):
    #             print(f"{key.replace('_', ' ').title()}: ${value:,.2f}")
    #         else:
    #             print(f"{key.replace('_', ' ').title()}: {value}")
    # else:
    #     print(f"Could not calculate Z-Score for {calculator.ticker}.")

    # Test with a ticker that might not have data or is from a different market
    # calculator_no_data = AltmanZScoreCalculator("NONEXISTENTTICKER")
    # details_no_data = calculator_no_data.get_score_details()
    # if details_no_data['z_score'] is None:
    #    print(f"\\nAs expected, Z-Score could not be calculated for {calculator_no_data.ticker}.")

    # Test mod_i and mod_d (requires a successful initial data fetch)
    # calculator_mod = AltmanZScoreCalculator("AAPL") # Assuming AAPL has data
    # if calculator_mod.fs and calculator_mod.fs.get('total_assets', 0) != 0 :
    #     print("\\n--- Testing Interactive Modifications for AAPL ---")
    #     initial_details = calculator_mod.get_score_details()
    #     print(f"Initial Z-Score for AAPL: {initial_details['z_score']:.4f}")
        
    #     calculator_mod.mod_i("1000000000", "revenue", "$") # Increase revenue by $1B
    #     calculator_mod.mod_d("0.05", "total_current_liabilities", "%") # Decrease TCL by 5%
        
    #     modified_details = calculator_mod.get_score_details()
    #     print(f"Z-Score for AAPL after modifications: {modified_details['z_score']:.4f}")
        
    #     calculator_mod.reset_financial_data()
    #     reset_details = calculator_mod.get_score_details()
    #     print(f"Z-Score for AAPL after reset: {reset_details['z_score']:.4f}")
    pass
