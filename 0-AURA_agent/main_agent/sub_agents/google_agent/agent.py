from google.adk.agents import Agent
from google.adk.tools import google_search


google_agent = Agent(
    name="google_agent",
    model="gemini-2.0-flash",
    description="Tool agent",
    instruction="""
    You are a helpful assistant that can use the following tools:
    - google_search and fetch the latest information from the web.
    """,
    tools=[google_search],

)