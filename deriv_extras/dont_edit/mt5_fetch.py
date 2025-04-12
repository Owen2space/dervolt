import websocket
import json
import threading


# Deriv WebSocket endpoint
DERIV_WS = "wss://ws.derivws.com/websockets/v3?app_id=70951"  # Replace with your own app_id if registered

def get_mt5_data(DERIV_TOKEN):
    """Fetch MT5 account data and return it as JSON"""
    result = {
        "success": False,
        "account": None,
        "mt5_accounts": []
    }
    
    # Event to signal when the fetch is complete
    fetch_complete = threading.Event()
    
    def on_message(ws, message):
        response = json.loads(message)

        if response.get("msg_type") == "authorize":
            # Capture account information
            is_virtual = response['authorize'].get('is_virtual', 'Unknown')
            account_type = "VIRTUAL" if is_virtual == 1 else "REAL"
            
            # Store account info in result
            result["account"] = {
                "id": response['authorize'].get('loginid'),
                "balance": response['authorize'].get('balance'),
                "type": account_type,
                "is_virtual": is_virtual,
                "name": response['authorize'].get('fullname', ''),
                "email": response['authorize'].get('email', '')
            }
            
            result["success"] = True
            
            # Request account list to check available accounts
            ws.send(json.dumps({
                "account_list": 1
            }))
        
        elif response.get("msg_type") == "account_list":
            result["available_accounts"] = []
            for account in response.get("account_list", []):
                account_type = "VIRTUAL" if account.get('is_virtual', False) else "REAL"
                result["available_accounts"].append({
                    "id": account.get('loginid', 'Unknown'),
                    "currency": account.get('currency', 'Unknown'),
                    "type": account_type,
                    "is_virtual": account.get('is_virtual', False)
                })
            
            # Now request MT5 login list
            ws.send(json.dumps({
                "mt5_login_list": 1
            }))

        elif response.get("msg_type") == "mt5_login_list":
            accounts = response.get("mt5_login_list", [])

            if accounts:
                for acc in accounts:
                    result["mt5_accounts"].append({
                        "login": acc.get('login'),
                        "name": acc.get('name'),
                        "balance": acc.get('balance'),
                        "currency": acc.get('currency'),
                        "leverage": acc.get('leverage'),
                        "type": acc.get('account_type'),
                        "group": acc.get('group'),
                        "server": acc.get('server')
                    })
            
            fetch_complete.set()
            ws.close()

        elif response.get("error"):
            result["success"] = False
            result["error"] = response["error"]["message"]
            fetch_complete.set()
            ws.close()

    def on_error(ws, error):
        result["success"] = False
        result["error"] = str(error)
        fetch_complete.set()

    def on_close(ws, close_status_code, close_msg):
        if not fetch_complete.is_set():
            fetch_complete.set()

    def on_open(ws):
        # Step 1: Authorize using session token
        ws.send(json.dumps({
            "authorize": DERIV_TOKEN
        }))

    websocket.enableTrace(False)
    ws = websocket.WebSocketApp(DERIV_WS,
                            on_open=on_open,
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close)

    # Run the WebSocket in a thread
    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()
    
    # Wait for the fetch to complete
    fetch_complete.wait(timeout=30)  # 30 second timeout
    
    return result

if __name__ == "__main__":
    # When run directly, fetch data and print as JSON
    mt5_data = get_mt5_data()
    print(json.dumps(mt5_data, indent=2))
