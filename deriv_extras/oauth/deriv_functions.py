import websocket
import json
import ssl  # Might be needed depending on system SSL setup
from urllib.parse import urlparse, parse_qs


def fetch_deriv_user_info(session_token, app_id):
    DERIV_WS_URL = f"wss://ws.derivws.com/websockets/v3?app_id={app_id}"
    ws = None
    try:
        ws = websocket.create_connection(DERIV_WS_URL, sslopt={"cert_reqs": ssl.CERT_NONE})
        print("WebSocket connection established.")

        # Prepare the authorize request
        auth_request = json.dumps({
            "authorize": session_token
        })

        ws.send(auth_request)

        result_str = ws.recv()
        result = json.loads(result_str)

        # Check for errors
        if 'error' in result:
            return False, f"API Error: {result['error']['code']} - {result['error']['message']}"
        elif 'authorize' in result:

            user_info = result['authorize']

            if 'account_list' in user_info:
                return True, json.dumps(result, indent=2)

            else:
                return False, "Account list not found in response."

        else:
            return False, "Received unexpected response format."

    except websocket.WebSocketException as wse:
        return False, f"WebSocket Error: {wse}"
    except ConnectionRefusedError:
        return False, "Connection refused. Ensure the WebSocket server is reachable."
    except Exception as e:
        return False, f"An unexpected error occurred: {e}"
    finally:
        if ws and ws.connected:
            ws.close()

def extract_tokens_from_url(url_string: str):
    """
    Extract account and token information from a Deriv OAuth redirect URL
    
    Args:
        url_string: The URL or query string to parse
        
    Returns:
        A list of tuples containing (account_id, token, currency) for each account
    """
    try:
        # If this is a full URL, extract just the query part
        if '?' in url_string:
            url_string = url_string.split('?', 1)[1]
            
        # Parse the query string into a dictionary
        if not url_string:
            return []
            
        # Split by & to get key-value pairs
        params = {}
        for pair in url_string.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[key] = value
        
        # Extract accounts and tokens
        accounts = []
        
        # Look for acct1, token1, cur1, etc.
        index = 1
        while f'acct{index}' in params and f'token{index}' in params:
            account = params.get(f'acct{index}')
            token = params.get(f'token{index}')
            currency = params.get(f'cur{index}', 'USD')  # Default to USD if not specified
            
            if account and token:
                accounts.append((account, token, currency))
                
            index += 1
            
        return accounts
    except Exception as e:
        print(f"Error processing URL: {e}")
        return []
    
def extract_tokens_from_url_1(url_string: str) -> str | None:
    try:
        # Parse the URL into its components
        parsed_url = urlparse(url_string)

        # Parse the query string into a dictionary
        # parse_qs returns values as lists, as parameters can appear multiple times
        query_params = parse_qs(parsed_url.query)

        # Extract the first value for 'token1' and 'token2'
        # Use .get() with a default of None to avoid KeyError if the token is missing
        token1_list = query_params.get('token1')
        token2_list = query_params.get('token2')

        # Check if both tokens were found and have at least one value
        if token1_list and token2_list:
            token1 = token1_list[0]  # Get the first value
            token2 = token2_list[0]  # Get the first value
            return token1, token2
        else:
            # Return None if either token is missing
            return None

    except Exception as e:
        # Handle potential parsing errors or other unexpected issues
        print(f"Error processing URL '{url_string}': {e}")
        return None