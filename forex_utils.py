try:
    import requests
    print("Successfully imported requests module version:", requests.__version__)
except ImportError:
    # Handle the case where requests is not installed
    print("Warning: requests module not found. Some functionality may be limited.")
    # Create a more complete mock class to prevent errors
    class MockResponse:
        def __init__(self):
            self.status_code = 500  # Error code
            self._json_data = {"rates": {"KES": 130.0}}  # Provide expected data structure
            
        def json(self):
            return self._json_data
            
    class RequestsMock:
        def get(self, *args, **kwargs):
            return MockResponse()
        
        def request(self, *args, **kwargs):
            return MockResponse()
            
    requests = RequestsMock()

import logging
import sys
from datetime import datetime
from database import get_db

# Configure more detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# Configure logging
logger = logging.getLogger(__name__)

# Get a value from system settings
def get_setting(key, default=None):
    """Get a value from system settings"""
    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
            result = cursor.fetchone()
            
            if result:
                return result["value"]
            return default
    except Exception as e:
        logger.error(f"Error retrieving setting {key}: {e}")
        return default

# Fetch latest forex rates from CurrencyLayer API
def fetch_forex_rate():
    """
    Fetch the latest USD/KES exchange rate from CurrencyLayer API
    and store it in the database.
    
    Returns:
        float: The latest USD/KES exchange rate or None if there was an error
    """
    try:
        logger.info("Fetching latest USD/KES forex rate from CurrencyLayer API")
        
        # Get API key from settings, or use default if not found
        api_key = get_setting("apilayer_api_key", "OINCnb11BaevDpWgZQ7iNw85IajuFnNW")
        
        # Using the exact format provided in the documentation
        url = "https://api.apilayer.com/currency_data/live?source=USD&currencies=KES"
        logger.debug(f"API URL: {url}")
        
        payload = {}
        headers = {
            "apikey": api_key
        }
        logger.debug(f"Using API Key: {api_key[:5]}...{api_key[-5:]}")
        
        # Use the requests.request method as shown in the example
        logger.debug("Making API request...")
        response = requests.request("GET", url, headers=headers, data=payload)
        
        status_code = response.status_code
        logger.debug(f"Received status code: {status_code}")
        
        if status_code != 200:
            logger.error(f"API request failed with status code {status_code}")
            # Print full response for debugging
            logger.error(f"Response content: {response.text}")
            if status_code == 401:
                logger.error("Authentication failed - please check your API key")
            return None
        
        # Parse the JSON response    
        logger.debug("Parsing JSON response")
        data = response.json()
        logger.debug(f"Response JSON: {data}")
        
        # CurrencyLayer response format is different from Open Exchange Rates
        if not data.get("success") or "quotes" not in data:
            logger.error("Required data missing from API response")
            logger.error(f"Response content: {response.text}")
            return None
            
        # CurrencyLayer returns currency pairs with source currency prefix (USDKES)
        usd_to_kes = data["quotes"].get("USDKES")
        if not usd_to_kes:
            logger.error("KES rate not found in API response")
            logger.error(f"Available quotes: {data.get('quotes', {}).keys()}")
            return None
            
        logger.info(f"Received USD/KES rate: {usd_to_kes}")
        
        # Store the rate in database
        store_forex_rate(usd_to_kes)
        return usd_to_kes
    except Exception as e:
        logger.error(f"Error fetching forex rates: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

# Store forex rate in database
def store_forex_rate(rate):
    """
    Store the provided USD/KES exchange rate in the database
    
    Args:
        rate (float): The USD/KES exchange rate to store
    """
    try:
        with get_db() as db:
            cursor = db.cursor()
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # First try to update existing record
            cursor.execute("""
                UPDATE forex_rates 
                SET rate = ?, updated_at = ? 
                WHERE currency = 'USD/KES'
            """, (rate, current_time))
            
            # If no record was updated, insert a new one
            if cursor.rowcount == 0:
                cursor.execute("""
                    INSERT INTO forex_rates (currency, rate, updated_at)
                    VALUES (?, ?, ?)
                """, ("USD/KES", rate, current_time))
                
            db.commit()
            logger.info(f"Stored USD/KES rate: {rate} at {current_time}")
    except Exception as e:
        logger.error(f"Error storing forex rate: {e}")

# Get the latest stored forex rate
def get_latest_forex_rate():
    """
    Retrieve the latest USD/KES exchange rate from the database
    
    Returns:
        float: The latest USD/KES exchange rate or None if not available
        str: The timestamp when the rate was last updated
    """
    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("""
                SELECT rate, updated_at 
                FROM forex_rates 
                WHERE currency = 'USD/KES' 
                ORDER BY updated_at DESC 
                LIMIT 1
            """)
            result = cursor.fetchone()
            
            if result:
                return result["rate"], result["updated_at"]
            return None, None
    except Exception as e:
        logger.error(f"Error retrieving latest forex rate: {e}")
        return None, None

# Apply forex spread for deposit (higher rate)
def get_deposit_rate():
    """
    Gets the forex rate for deposits with a favorable spread
    
    Returns:
        float: The USD/KES exchange rate for deposits, rounded to 2 decimal places
        str: The timestamp when the rate was last updated
    """
    base_rate, updated_at = get_latest_forex_rate()
    if base_rate is None:
        return 132.90, None  # Default deposit rate if not available
    
    # Get deposit spread from settings (as percentage)
    deposit_spread = float(get_setting("deposit_rate_spread", "102.6"))
    
    # Apply deposit spread (higher rate for deposits)
    deposit_rate = base_rate * (deposit_spread / 100.0)
    
    # Round to 2 decimal places for consistent display
    deposit_rate = round(deposit_rate, 2)
    return deposit_rate, updated_at

# Apply forex spread for withdrawal (lower rate)
def get_withdrawal_rate():
    """
    Gets the forex rate for withdrawals with a spread
    
    Returns:
        float: The USD/KES exchange rate for withdrawals, rounded to 2 decimal places
        str: The timestamp when the rate was last updated
    """
    base_rate, updated_at = get_latest_forex_rate()
    if base_rate is None:
        return 126.20, None  # Default withdrawal rate if not available
    
    # Get withdrawal spread from settings (as percentage)
    withdrawal_spread = float(get_setting("withdrawal_rate_spread", "97.5"))
    
    # Apply withdrawal spread (lower rate for withdrawals)
    withdrawal_rate = base_rate * (withdrawal_spread / 100.0)
    
    # Round to 2 decimal places for consistent display
    withdrawal_rate = round(withdrawal_rate, 2)
    return withdrawal_rate, updated_at

# Calculate deposit amount with forex conversion and fees
def calculate_deposit_amount(usd_amount):
    """
    Calculate the KES amount and fee for a USD deposit
    
    Args:
        usd_amount (float): The amount in USD to deposit
        
    Returns:
        dict: A dictionary containing the calculated amounts and rates
    """
    forex_rate, updated_at = get_deposit_rate()
    
    if forex_rate is None:
        return {
            "success": False,
            "message": "Forex rate unavailable"
        }

    # Get deposit fee percentage from settings
    fee_percent = float(get_setting("deposit_fee_percent", "1.0"))
    fee_decimal = fee_percent / 100.0
    fee_usd = round(usd_amount * fee_decimal, 2)
    
    # Calculate net amount in USD and KES
    net_usd = round(usd_amount - fee_usd, 2)
    kes_amount = round(net_usd * forex_rate, 2)
    
    return {
        "success": True,
        "usd_amount": round(usd_amount, 2),
        "fee_percent": fee_percent,
        "fee_usd": fee_usd,
        "net_usd": net_usd,
        "forex_rate": forex_rate,
        "kes_amount": kes_amount,
        "rate_updated_at": updated_at
    }

# Calculate withdrawal amount with forex conversion and fees
def calculate_withdrawal_amount(usd_amount):
    """
    Calculate the KES amount and fee for a USD withdrawal
    
    Args:
        usd_amount (float): The amount in USD to withdraw
        
    Returns:
        dict: A dictionary containing the calculated amounts and rates
    """
    forex_rate, updated_at = get_withdrawal_rate()
    
    if forex_rate is None:
        return {
            "success": False,
            "message": "Forex rate unavailable"
        }

    # Get withdrawal fee percentage from settings
    fee_percent = float(get_setting("withdrawal_fee_percent", "1.5"))
    fee_decimal = fee_percent / 100.0
    fee_usd = round(usd_amount * fee_decimal, 2)
    
    # Calculate net amount in USD and KES
    net_usd = round(usd_amount - fee_usd, 2)
    kes_amount = round(net_usd * forex_rate, 2)
    
    return {
        "success": True,
        "usd_amount": round(usd_amount, 2),
        "fee_percent": fee_percent,
        "fee_usd": fee_usd,
        "net_usd": net_usd,
        "forex_rate": forex_rate,
        "kes_amount": kes_amount,
        "rate_updated_at": updated_at
    } 