import websocket
import json
import ssl # Optional: May be needed for some environments
from config import app_id
# --- Configuration ---
# Replace with your actual App ID from Deriv app registration
APP_ID = app_id

# IMPORTANT: This is the Access Token you obtained through the OAuth2 flow.
# You need to implement the OAuth flow separately to get this token.
# How you get this into your script depends on your application structure
# (e.g., passed as an argument, read from a secure store, etc.)
OAUTH_ACCESS_TOKEN = 'a1-m0icN9TJKmq9Tp6IoLU9rV79CG6X8' # <--- Replace this

API_URL = f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}"

# --- Main Logic ---
ws = None # Initialize websocket variable

# --- Validate Token ---
# Basic check to ensure the placeholder is replaced
if not OAUTH_ACCESS_TOKEN or OAUTH_ACCESS_TOKEN == 'THE_OAUTH_ACCESS_TOKEN_YOU_OBTAINED':
    print("Error: Please replace 'THE_OAUTH_ACCESS_TOKEN_YOU_OBTAINED' with a valid OAuth Access Token.")
    exit() # Stop execution if the token isn't set

print(f"Connecting to {API_URL}...")
try:
    # 1. Connect to WebSocket
    # ws = websocket.create_connection(API_URL, sslopt={"cert_reqs": ssl.CERT_NONE}) # Uncomment if needed
    ws = websocket.create_connection(API_URL)
    print("Connected successfully.")

    # 2. Authorize the connection using the OAuth Access Token
    auth_request = {
        "authorize": OAUTH_ACCESS_TOKEN # Use the OAuth token here
    }
    print(f"Sending Authorize Request (using OAuth Token)...") # Don't log the full token in production
    # print(f"Sending Authorize Request: {json.dumps(auth_request)}") # Avoid logging token
    ws.send(json.dumps(auth_request))

    # 3. Wait for and process the Authorization Response
    auth_result_str = ws.recv()
    print(f"Received Authorize Response: {auth_result_str}")
    auth_result = json.loads(auth_result_str)

    # Check for authorization errors
    if 'error' in auth_result:
        print(f"Authorization Failed: {auth_result['error']['message']}")
        # Check if the error is related to an invalid or expired token
        if auth_result['error']['code'] == 'InvalidToken':
             print("The OAuth token might be invalid or expired. You may need to refresh it or re-authenticate.")
    elif auth_result.get('msg_type') == 'authorize' and auth_result.get('authorize'):
        print("Authorization Successful (OAuth).")
        user_info = auth_result.get('authorize', {})
        print(f"Authorized for User ID: {user_info.get('loginid')}")
        print(f"Scopes Granted: {user_info.get('scopes')}")


        # 4. Request User Settings (only if authorized)
        settings_request = {
            "get_settings": 1
        }
        print(f"Sending Get Settings Request: {json.dumps(settings_request)}")
        ws.send(json.dumps(settings_request))

        # 5. Wait for and process the Settings Response
        settings_result_str = ws.recv()
        print(f"Received Settings Response: {settings_result_str}")
        settings_result = json.loads(settings_result_str)

        # 6. Process the settings data
        if 'error' in settings_result:
            print(f"Failed to get settings: {settings_result['error']['message']}")
        elif settings_result.get('msg_type') == 'get_settings' and 'get_settings' in settings_result:
            user_settings = settings_result['get_settings']
            print("\n--- User Account Settings ---")
            print(f"Email: {user_settings.get('email', 'N/A')}")
            print(f"Country: {user_settings.get('country', 'N/A')}")
            print(f"Preferred Language: {user_settings.get('preferred_language', 'N/A')}")
            print(f"Name: {user_settings.get('first_name', '')} {user_settings.get('last_name', '')}")
            # Add more fields as needed...
            # print("\n--- All Settings Data ---")
            # print(json.dumps(user_settings, indent=2))
        else:
            print("Unexpected response format received for settings.")
    else:
        print("Authorization failed or unexpected response format.")


except websocket.WebSocketException as wse:
    print(f"WebSocket Error: {wse}")
except ConnectionRefusedError:
     print(f"Connection Refused: Could not connect to {API_URL}. Check network or endpoint.")
except json.JSONDecodeError as jde:
    print(f"JSON Parsing Error: {jde}")
    # Determine which response string caused the error if possible
    problematic_data = 'Unknown'
    if 'auth_result_str' in locals() and not isinstance(auth_result_str, dict):
        problematic_data = auth_result_str
    elif 'settings_result_str' in locals() and not isinstance(settings_result_str, dict):
         problematic_data = settings_result_str
    print(f"Problematic data received: {problematic_data}")
except Exception as e:
    print(f"An unexpected error occurred: {type(e).__name__} - {e}")

finally:
    # 7. Close the connection gracefully
    if ws and ws.connected:
        print("Closing WebSocket connection.")
        ws.close()
    else:
        print("WebSocket connection was not established or already closed.")