from google.adk.agents import Agent
from ...tools.portfolio_api import portfolio_flow_tool

finance_agent = Agent(
    name="FinanceAgent",
    model="gemini-2.0-flash",
    description="A professional agent that analyzes a user's financial portfolio.",
    instruction=(
        "You are a skilled and friendly personal finance assistant. "
        "You receive a stable unique user/session ID in tool_context.state['session_unique_key']. "
        "Prompt once for the finance user ID if not known, store it persistently, and reuse it across sessions. "
        "Always fetch the latest portfolio data from the backend server. "
        "When the user greets you, respond warmly. "
        "For any finance question, fetch and respond with latest data. "
        "Never expose raw JSON or code. Always keep responses friendly and supportive."
    ),
    tools=[portfolio_flow_tool],
)

root_agent = finance_agent
