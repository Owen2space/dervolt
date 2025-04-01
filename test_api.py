"""
Test script for CurrencyLayer API
Run this directly to test if the API connection works properly
"""

import requests
import json

def test_currencylayer_api():
    print("Testing CurrencyLayer API connection...")
    
    url = "https://api.apilayer.com/currency_data/live?source=USD&currencies=KES"
    api_key = "OINCnb11BaevDpWgZQ7iNw85IajuFnNW"
    
    payload = {}
    headers = {
        "apikey": api_key
    }
    
    print(f"Making request to: {url}")
    print(f"Using API key: {api_key[:5]}...{api_key[-5:]}")
    
    try:
        response = requests.request("GET", url, headers=headers, data=payload)
        
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
        
        if response.status_code == 200:
            data = response.json()
            print("\nResponse data:")
            print(json.dumps(data, indent=2))
            
            if "quotes" in data and "USDKES" in data["quotes"]:
                rate = data["quotes"]["USDKES"]
                print(f"\nUSD to KES rate: {rate}")
            else:
                print("\nQuotes or USDKES not found in response")
                if "quotes" in data:
                    print(f"Available quotes: {list(data['quotes'].keys())}")
        else:
            print(f"Error response: {response.text}")
            
    except Exception as e:
        print(f"Exception occurred: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    test_currencylayer_api() 