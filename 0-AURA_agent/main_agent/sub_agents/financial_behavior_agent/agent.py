import os
from dotenv import load_dotenv
from pathlib import Path
import asyncio
from typing import List, Dict, Any, Optional

import random
from datetime import datetime, timedelta


script_dir = Path(__file__).parent.resolve()
print(f"DEBUG: Script directory: {script_dir}")

expected_env_path = script_dir.parent / '.env' 
print(f"DEBUG: Expected .env path: {expected_env_path}")
print(f"DEBUG: Does .env exist at expected path? {expected_env_path.exists()}")

load_dotenv(dotenv_path=expected_env_path)

print(f"DEBUG: Current working directory (where you run the command): {os.getcwd()}")
print(f"DEBUG: GOOGLE_API_KEY loaded: {'YES' if os.getenv('GOOGLE_API_KEY') else 'NO'}")
print(f"DEBUG: FIREBASE_SERVICE_ACCOUNT_KEY_PATH loaded: {os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY_PATH')}")
print(f"DEBUG: GEMINI_MODEL loaded: {os.getenv('GEMINI_MODEL')}")

from .fim_connector import get_local_transaction_history, get_local_user_goals # NEW import
from .tools import analyze_spending_patterns, identify_emotional_triggers, \
                            identify_financial_biases, generate_financial_nudge
from google.adk import Agent
from google.adk.tools import FunctionTool
from google.generativeai import GenerativeModel


print("Initializing Agent for local file deployment...")


gemini_api_key = os.getenv("GOOGLE_API_KEY")
gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")

if not gemini_api_key:
    raise ValueError("GOOGLE_API_KEY environment variable not set.")

llm = GenerativeModel(model_name=gemini_model_name)
print(f"Using Generative Model '{gemini_model_name}' for ADK Agent.")

all_tools = [
    FunctionTool(get_local_transaction_history), 
    FunctionTool(get_local_user_goals),         
    FunctionTool(analyze_spending_patterns),
    FunctionTool(identify_emotional_triggers),
    FunctionTool(identify_financial_biases),
    FunctionTool(generate_financial_nudge)
]

print(f"ADK Tools registered: {[tool.name for tool in all_tools]}.")


root_agent = Agent(
    model=gemini_model_name,
    name="FinancialBehavioralAgent", 
    tools=all_tools,
    description=(
        "You are an AI-powered financial behavior analyst and coach. "
        "Your primary goal is to help users understand their financial habits, "
        "identify psychological biases, and provide personalized 'nudges' "
        "to encourage healthier financial decisions. "
        "You have access to user transaction data and financial goals via tools to provide accurate and actionable insights. "
        "Your responses should be empathetic, clear, and actionable."
    ),
    instruction = """
    At the start of the session, automatically fetch the user's latest transaction history, account balances, recurring expenses, income streams, savings contributions, and financial goals using available tools.

    Do **not** prompt for the user's name or identity. Instead, rely solely on system-authorized data streams.

    Once the data is fetched, perform a rapid analysis to extract key financial behavior insights, including:

    - Top 3 spending categories over the past 30 days
    - Notable recurring expenses (subscriptions, bills)
    - Savings rate vs. income
    - Any unusual or impulsive transactions
    - Alignment of spending habits with stated financial goals
    - Presence of behavioral biases (e.g., present bias, loss aversion)

    Deliver the insights in a clear, empathetic tone, focused on **nudging** the user toward healthier financial habits with **concrete, personalized suggestions**. Avoid judgmental language. End the summary with an open-ended **nudge** or reflection question that encourages the user to think about one area to improve today.
    """

)
print("Global 'financial_behavior_agent' instance created and ready for ADK Web deployment with local data.")
agent = root_agent
