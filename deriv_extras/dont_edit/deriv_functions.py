import websocket
import json
import ssl  # Might be needed depending on system SSL setup
from urllib.parse import urlparse, parse_qs
from config import app_id

          
def extract_tokens_from_url(url_string: str) -> str | None:
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

def fetch_deriv_user_info(session_token):
    DERIV_WS_URL = f"wss://ws.derivws.com/websockets/v3?app_id={app_id}"
    ws = None
    try:
        ws = websocket.create_connection(DERIV_WS_URL, sslopt={"cert_reqs": ssl.CERT_NONE})
        # print("WebSocket connection established.")

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

def get_account_settings(session_token):
    DERIV_WS_URL = f"wss://ws.derivws.com/websockets/v3?app_id={app_id}"
    ws = None
    try:
        ws = websocket.create_connection(DERIV_WS_URL, sslopt={"cert_reqs": ssl.CERT_NONE})
        # print("WebSocket connection established.")

        # Authorize the connection using the session token
        auth_request = json.dumps({
            "authorize": session_token
        })
        ws.send(auth_request)

        # Process authorization response
        auth_result_str = ws.recv()
        auth_result = json.loads(auth_result_str)

        # Check for authorization errors
        if 'error' in auth_result:
            return False, f"Authorization Failed: {auth_result['error']['code']} - {auth_result['error']['message']}"
        elif auth_result.get('msg_type') == 'authorize' and auth_result.get('authorize'):
            # print("Authorization Successful.")
            
            # Request user settings
            settings_request = json.dumps({
                "get_settings": 1
            })
            ws.send(settings_request)
            
            # Process settings response
            settings_result_str = ws.recv()
            settings_result = json.loads(settings_result_str)
            
            if 'error' in settings_result:
                return False, f"Failed to get settings: {settings_result['error']['message']}"
            elif settings_result.get('msg_type') == 'get_settings' and 'get_settings' in settings_result:
                return True, json.dumps(settings_result, indent=2)
            else:
                return False, "Unexpected response format received for settings."
        else:
            return False, "Authorization failed or unexpected response format."
            
    except websocket.WebSocketException as wse:
        return False, f"WebSocket Error: {wse}"
    except ConnectionRefusedError:
        return False, "Connection refused. Ensure the WebSocket server is reachable."
    except json.JSONDecodeError as jde:
        return False, f"JSON Parsing Error: {jde}"
    except Exception as e:
        return False, f"An unexpected error occurred: {e}"
    finally:
        if ws and ws.connected:
            ws.close()


        
