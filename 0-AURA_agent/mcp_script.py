import asyncio
import json
import sys
import firebase_admin
from firebase_admin import credentials, db
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import TextContent


if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-cred-file.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': "firebase data store URL here"
    })
ref = db.reference("/")

async def main():
    print("--- SCRIPT: Starting MCP fetch for user ---")
    try:
        
        if len(sys.argv) > 1:
            user_id = sys.argv[1]
        else:
            print(json.dumps({"error": "No user_id provided. Please pass user_id as argument."}))
            return

        endpoints = {
            'net_worth': 'fetch_net_worth',
            'credit_report': 'fetch_credit_report',
            'epf_details': 'fetch_epf_details',
            'mutual_fund_transactions': 'fetch_mf_transactions',
            'stock_transactions': 'fetch_stock_transactions',
            'bank_transactions': 'fetch_bank_transactions'
        }
        all_data = {}

        
        async with streamablehttp_client("http://localhost:8080/mcp/stream") as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                for key, tool_name in endpoints.items():
                    try:
                        # Pass user_id in tool call
                        tool_response = await session.call_tool(tool_name, {"user_id": user_id})
                        if tool_response.content and isinstance(tool_response.content[0], TextContent):
                            parsed = json.loads(tool_response.content[0].text)
                            all_data[key] = parsed
                        else:
                            all_data[key] = {}
                    except Exception as e:
                        print(f"--- SCRIPT: Error fetching {tool_name}: {e}. Skipping... ---")
                        all_data[key] = {}

        print("--- SCRIPT: Final data collected ---")
        print(json.dumps(all_data, indent=2))

        user_ref = ref.child(f"financial_data/{user_id}")
        user_ref.set(all_data)
        print(f"--- SCRIPT: Financial data saved to Firebase for user {user_id} ---")
    except Exception as e:
        print(json.dumps({"error": f"Script exception: {str(e)}"}))

if __name__ == "__main__":
    asyncio.run(main())
