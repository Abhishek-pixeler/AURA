
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any


script_dir = Path(__file__).parent.resolve()
LOCAL_DATA_FILE = script_dir/"fetch_bank_transactions.json"


TRANSACTION_TYPE_MAP = {
    1: 'income',   
    2: 'expense',  
    3: 'income',   
    4: 'income',   
    5: 'expense',  
    6: 'expense',  
    7: 'expense',  
    8: 'other'     
}

def _load_local_data() -> Dict:
    """Loads data from the local_data.json file."""
    if not LOCAL_DATA_FILE.exists():
        print(f"Error: Local data file not found at {LOCAL_DATA_FILE}")
        return {"transactions": [], "financial_goals": []}
    try:
        with open(LOCAL_DATA_FILE, 'r') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        print(f"Error decoding local data JSON: {e}")
        return {"transactions": [], "financial_goals": []}
    except Exception as e:
        print(f"An unexpected error occurred while reading local data: {e}")
        return {"transactions": [], "financial_goals": []}

async def get_local_transaction_history(days: int = 60) -> List[Dict[str, Any]]:
    """Fetches transaction history from local file for a given user, filtered by days."""
    print(f"Tool: Reading transaction history from local file for user  for {days} days.")
    data = _load_local_data()
    all_transactions = data.get("transactions", [])

    
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_transactions = []
    for t in all_transactions:
        try:
            
            transaction_date = datetime.strptime(t['date'], '%Y-%m-%d')
            if transaction_date >= cutoff_date:
                recent_transactions.append(t)
        except ValueError:
            print(f"Warning: Invalid date format in transaction: {t.get('date')}. Skipping.")
            continue 

   
    recent_transactions.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d'), reverse=True)

    return recent_transactions

async def get_local_user_goals() -> List[Dict[str, Any]]:
    """Fetches financial goals from local file for user."""
    print(f"Tool: Reading financial goals from local file for user ''.")
    data = _load_local_data()
    return data.get("financial_goals", [])