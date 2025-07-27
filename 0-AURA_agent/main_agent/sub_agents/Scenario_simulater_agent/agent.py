import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools import google_search


Scenario_agent = Agent(
    name="Scenario_agent",
    model="gemini-2.0-flash",
    description="Scenario_agent",
    instruction="""
 'You are a helpful assistant that analyzes financial scenario assistant specialized in 'What-if' simulations.
Your job is to analyze financial situations based on hypothetical user inputs and provide short, clear guidance.
Use real-world logic and financial modeling techniques to simulate scenarios such as income change, retirement savings, inflation effects, and stress testing.
Make reasonable assumptions (e.g., inflation 5%, return 10%) unless user specifies.Give the actual numbers by doing the calculations and provide the appropriate 
data for the investment.
Summarize in max 6 or 7 lines with plain language and helpful suggestions.
Always end with: 'Would you like to explore this scenario in more detail?'
    """,
    tools=[google_search],
)

def simulate_scenarios(age, retirement_age, income, saving, goal) -> str:
    years = retirement_age - age
    months = years * 12
    r_annual = 0.10
    r_monthly = r_annual / 12

    # Scenario 1 – Flat savings
    flat_total = sum([
        saving * (1 + r_monthly) ** (months - i)
        for i in range(months)
    ])

    # Scenario 2 – 10% growth in savings each year
    total_growth = 0
    s = saving
    for y in range(years):
        for m in range(12):
            months_left = (years - y) * 12 - m
            total_growth += s * (1 + r_monthly) ** months_left
        s *= 1.10

    # Format output
    return f"""
📈 Retirement Projection Summary:
• Constant savings ₹{saving:,.0f}/mo → ₹{flat_total:,.0f} by age {retirement_age}
• 10% annual increase in savings → ₹{total_growth:,.0f}
• Goal: {goal}

Would you like to explore this scenario in more detail?
""".strip()


def get_user_inputs():
    print("👋 Welcome to the Financial What-if Scenario Planner (INR Version)\n")
    print("I'll ask you a few simple questions to simulate your retirement planning.")

    try:
        age = int(input("👉 Your current age: "))
        retirement_age = int(input("👉 At what age would you like to retire? "))
        income = float(input("👉 Your current monthly income (₹): "))
        saving = float(input("👉 How much do you save monthly (₹): "))
        goal = input("🎯 What is your retirement goal? (e.g., Passive income, ₹2 Cr corpus): ")

        print("\n🔍 Running your simulation...\n")
        result = simulate_scenarios(age, retirement_age, income, saving, goal)
        print(result)

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    get_user_inputs()


