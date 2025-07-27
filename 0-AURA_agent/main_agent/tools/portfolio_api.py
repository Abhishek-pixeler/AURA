from google.adk.tools import FunctionTool, ToolContext
import subprocess
import sys
import json
import firebase_admin
from firebase_admin import credentials, db
import threading
import time
import schedule


from messaging import send_message_user


if not firebase_admin._apps:
    cred = credentials.Certificate(r"C:\Abhishek\0-AURA_agent\main_agent\aura-fb80a-firebase-adminsdk-fbsvc-9f19078156.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://aura-fb80a-default-rtdb.firebaseio.com/'
    })
ref = db.reference("/")

def get_persistent_user_id(session_unique_key):
    user_ref = ref.child(f"users/{session_unique_key}/user_id")
    return user_ref.get()

def set_persistent_user_id(session_unique_key, user_id):
    user_ref = ref.child(f"users/{session_unique_key}")
    user_ref.update({"user_id": user_id})

def fetch_latest_server_data(user_id: str):
    try:
        result = subprocess.run(
            [sys.executable, r"C:\Abhishek\0-AURA_agent\mcp_script.py", user_id],
            capture_output=True, text=True, check=True, timeout=300
        )
        stdout = result.stdout
        first_brace = stdout.find('{')
        last_brace = stdout.rfind('}')
        if first_brace == -1 or last_brace == -1:
            print(f"[fetch] Failed to parse MCP output for user {user_id}")
            return None
        return json.loads(stdout[first_brace:last_brace + 1])
    except Exception as e:
        print(f"[fetch] MCP error for user {user_id}: {e}")
        return None

def get_current_firebase_data(user_id: str):
    user_ref = ref.child(f"financial_data/{user_id}")
    return user_ref.get()

def save_new_data_to_firebase(user_id: str, data: dict):
    user_ref = ref.child(f"financial_data/{user_id}")
    user_ref.set(data)

def compare_and_update(user_id):
    """
    Fetch latest server data and compare with Firebase.
    If different, alert user and update Firebase.
    """
    server_data = fetch_latest_server_data(user_id)
    if server_data is None:
        print(f"[compare] Could not fetch server data for user {user_id}")
        return

    firebase_data = get_current_firebase_data(user_id)

    if json.dumps(server_data, sort_keys=True) == json.dumps(firebase_data, sort_keys=True):
        print(f"[compare] No new data for user {user_id}. Skipping update.")
        return

    print(f"[compare] Data changed for user {user_id}. Updating Firebase and alerting user.")
    alert_message = "Your finance data was updated from the server with the latest information."
    send_message_user(user_id, alert_message)

    formatted_data = json.dumps(server_data, indent=2)
    send_message_user(user_id, f"Latest financial data:\n{formatted_data}")

    save_new_data_to_firebase(user_id, server_data)
    print(f"[compare] Firebase updated and alert sent for user {user_id}.")

# Maintain a live list of active users for polling.
active_user_ids = []

def add_active_user(user_id: str):
    if user_id not in active_user_ids:
        active_user_ids.append(user_id)

def load_active_users_from_firebase():
    users_snapshot = ref.child("users").get()
    if users_snapshot:
        for _, val in users_snapshot.items():
            user_id = val.get('user_id')
            if user_id:
                add_active_user(user_id)
load_active_users_from_firebase()

def poll_all_users():
    print("Background Polling: Checking updates for active users...")
    for user_id in active_user_ids:
        compare_and_update(user_id)

def run_scheduler():
    schedule.every(2).minutes.do(poll_all_users)
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_background_polling():
    thread = threading.Thread(target=run_scheduler, daemon=True)
    thread.start()
start_background_polling()

# On-demand portfolio flow (user-triggered)
def refresh_user_data(user_id: str):
    """
    Fetch latest data from server and update Firebase.
    Used in interactive chat flow.
    """
    try:
        result = subprocess.run(
            [sys.executable, r"C:\Abhishek\0-AURA_agent\mcp_script.py", user_id],
            capture_output=True, text=True, check=True, timeout=300
        )
        stdout = result.stdout
        first_brace = stdout.find('{')
        last_brace = stdout.rfind('}')
        if first_brace == -1 or last_brace == -1:
            print(f"Failed to parse MCP output for user {user_id}. Output:\n{stdout}")
            return False

        json_raw = stdout[first_brace:last_brace + 1]
        parsed = json.loads(json_raw)
        save_new_data_to_firebase(user_id, parsed)
        print(f"Data refreshed successfully for user {user_id}")
        return True
    except Exception as e:
        print(f"Error refreshing data for user {user_id}: {e}")
        return False

def run_portfolio_flow(tool_context: ToolContext, force_refresh: bool = False) -> str:
    """
    Interactive flow: use a persistent user id across sessions.
    Prompts on first use, stores persistently, always fetches fresh data.
    """
    session_key = tool_context.state.get('session_unique_key')
    if not session_key:
        session_key = "unique_user_key"
        tool_context.state['session_unique_key'] = session_key

    user_id = tool_context.state.get('user_id')
    if not user_id:
        user_id = get_persistent_user_id(session_key)

    if not user_id:
        user_id = input("Welcome! Please enter your user ID to fetch your finance data: ").strip()
        tool_context.state['user_id'] = user_id
        set_persistent_user_id(session_key, user_id)
        add_active_user(user_id)
    else:
        tool_context.state['user_id'] = user_id
        add_active_user(user_id)

    success = refresh_user_data(user_id)
    if not success:
        return "Failed to fetch your latest financial data, please try again later."

    data_ref = ref.child(f"financial_data/{user_id}")
    latest_data = data_ref.get()
    if latest_data:
        return json.dumps(latest_data, indent=2)
    else:
        return "No financial data found for your user."

portfolio_flow_tool = FunctionTool(
    func=run_portfolio_flow
)
