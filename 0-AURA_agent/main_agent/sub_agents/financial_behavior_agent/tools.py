# tools.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google.generativeai import GenerativeModel # Assuming you pass the model here or it's globally available
import os

# Define a mock model for local testing if you don't want to hit the API constantly during development of analysis functions
# This is just for the _generate_behavioral_recommendations, which needs an LLM.
# In the actual ADK agent, the `model` would be the Gemini model configured for the agent.
# For this tool, it's better to make the LLM call within the tool itself or pass a callable model.
# For simplicity, we'll instantiate it here, assuming GOOGLE_API_KEY is set in .env
try:
    _mock_model = GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest"))
except Exception as e:
    print(f"Warning: Could not initialize GenerativeModel in tools.py. Ensure GOOGLE_API_KEY and GEMINI_MODEL are set. Error: {e}")
    _mock_model = None # Fallback for local testing without API key

# Helper functions (can be private methods within a class or just standalone)
def _analyze_temporal_patterns(df: pd.DataFrame) -> Dict:
    """Analyze spending patterns across different time periods."""
    # Ensure 'date' is datetime type
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'])

    # Filter for expenses only for temporal patterns
    expenses_df = df[df['type'] == 'expense']
    if expenses_df.empty:
        return {
            "day_of_week_spending": {},
            "hourly_patterns": {},
            "monthly_trends": {}
        }

    # Ensure all days/hours are represented, even with 0 spending, for complete patterns
    all_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_of_week_avg = expenses_df.groupby(expenses_df['date'].dt.day_name())['amount'].mean().reindex(all_days).fillna(0)

    all_hours = range(24)
    hourly_avg = expenses_df.groupby(expenses_df['date'].dt.hour)['amount'].mean().reindex(all_hours).fillna(0)

    monthly_sum = expenses_df.set_index('date').resample('M')['amount'].sum()
    # Convert Timestamp to string for JSON serialization
    monthly_trends_dict = {str(k.to_period('M')): v for k, v in monthly_sum.items()}

    return {
        "day_of_week_spending": day_of_week_avg.to_dict(),
        "hourly_patterns": hourly_avg.to_dict(),
        "monthly_trends": monthly_trends_dict
    }

def _detect_impulse_spending(df: pd.DataFrame) -> Dict:
    """Detect potential impulse spending patterns."""
    # Filter for expenses only
    expenses_df = df[df['type'] == 'expense']
    if expenses_df.empty:
        return {
            "impulse_score": 0,
            "quick_transaction_count": 0,
            "total_impulse_amount": 0.0,
            "risk_level": "low",
            "example_transactions": []
        }

    df_sorted = expenses_df.sort_values('date')
    df_sorted['time_diff'] = df_sorted['date'].diff().dt.total_seconds() / 60  # Minutes

    quick_transactions = df_sorted[df_sorted['time_diff'].notna() & (df_sorted['time_diff'] < 30)]  # Within 30 minutes, exclude first transaction

    impulse_score = len(quick_transactions) / len(expenses_df) * 100 if len(expenses_df) > 0 else 0

    return {
        "impulse_score": round(impulse_score, 2),
        "quick_transaction_count": len(quick_transactions),
        "total_impulse_amount": round(quick_transactions['amount'].sum(), 2),
        "risk_level": "high" if impulse_score > 20 else "medium" if impulse_score > 10 else "low",
        "example_transactions": quick_transactions.head(3).to_dict(orient='records') # Show first 3 examples
    }


async def analyze_spending_patterns(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyzes user transaction data to identify spending patterns,
    categories of overspending/underspending, and recurring habits.
    This tool provides a comprehensive overview of financial behavior.

    Args:
        transactions: A list of dictionaries, where each dictionary represents a transaction
                      with keys like 'date', 'amount', 'category', 'description', 'type' (e.g., 'income', 'expense').

    Returns:
        A dictionary containing various spending insights:
        - summary: A general summary string.
        - total_spending_by_category: Sum of expenses per category.
        - average_daily_spending: Average spending per day.
        - high_frequency_categories: Categories with many small transactions.
        - temporal_patterns: Spending trends by day of week, hour, and month.
        - impulse_indicators: Data related to quick successive purchases.
    """
    if not transactions:
        return {"summary": "No transactions provided for analysis."}

    df = pd.DataFrame(transactions)
    df['date'] = pd.to_datetime(df['date'])
    df['amount'] = pd.to_numeric(df['amount'])

    expenses_df = df[df['type'] == 'expense']
    if expenses_df.empty:
        return {"summary": "No expenses found for detailed analysis."}

    # Total spending by category
    spending_by_category = expenses_df.groupby('category')['amount'].sum().sort_values(ascending=False).to_dict()

    # Average daily spending
    daily_spending = expenses_df.groupby(expenses_df['date'].dt.date)['amount'].sum().mean()

    # Identify categories with many transactions (potential frequent small purchases)
    transaction_counts_by_category = expenses_df.groupby('category')['amount'].count().sort_values(ascending=False)
    high_frequency_categories = transaction_counts_by_category[transaction_counts_by_category > (len(expenses_df) * 0.05)].index.tolist() # More than 5% of total transactions

    insights = {
        "summary": "Detailed spending patterns analyzed.",
        "total_spending_by_category": {k: round(v, 2) for k, v in spending_by_category.items()},
        "average_daily_spending": round(daily_spending, 2),
        "high_frequency_categories": high_frequency_categories,
        "temporal_patterns": _analyze_temporal_patterns(df), # Use the helper
        "impulse_indicators": _detect_impulse_spending(df) # Use the helper
    }
    return insights


async def identify_emotional_triggers(transactions: List[Dict[str, Any]], user_text_input: Optional[str] = None) -> Dict[str, Any]:
    """
    Identifies potential emotional spending triggers by analyzing spending patterns
    around specific times (e.g., weekends, late nights) and correlating with user text input.

    Args:
        transactions: A list of dictionaries representing transactions.
        user_text_input: Optional. A string from the user, e.g., from a journaling feature,
                         to detect explicit emotional mentions.

    Returns:
        A dictionary indicating potential emotional triggers and associated behaviors.
    """
    if not transactions:
        return {"summary": "No transactions provided for emotional trigger analysis."}

    df = pd.DataFrame(transactions)
    df['date'] = pd.to_datetime(df['date'])
    df['amount'] = pd.to_numeric(df['amount'])
    df['day_of_week'] = df['date'].dt.day_name()
    df['hour'] = df['date'].dt.hour
    df['is_weekend'] = df['date'].dt.weekday >= 5

    triggers = []

    
    weekend_spending = df[df['is_weekend']]['amount'].sum()
    weekday_spending = df[~df['is_weekend']]['amount'].sum()
    weekend_days_count = df['is_weekend'].sum()
    weekday_days_count = len(df) - weekend_days_count

    avg_weekend_daily = weekend_spending / max(1, weekend_days_count) if weekend_days_count > 0 else 0
    avg_weekday_daily = weekday_spending / max(1, weekday_days_count) if weekday_days_count > 0 else 0

    if avg_weekend_daily > avg_weekday_daily * 1.3 and avg_weekday_daily > 0: # 30% higher on weekends
        triggers.append({
            "trigger": "weekend_emotional_spending",
            "description": "Higher average spending on weekends suggests emotional or social spending patterns.",
            "impact_details": f"Average weekend daily spending: ₹{avg_weekend_daily:.2f}, Weekday: ₹{avg_weekday_daily:.2f}",
            "recommendation": "Consider setting weekend spending limits or finding alternative weekend activities to manage emotional spending."
        })

    # Late night spending analysis (after 10 PM, before 6 AM)
    late_night_spending_df = df[(df['hour'] >= 22) | (df['hour'] < 6)]
    daytime_spending_df = df[(df['hour'] >= 6) & (df['hour'] < 22)]

    late_night_total = late_night_spending_df['amount'].sum()
    daytime_total = daytime_spending_df['amount'].sum()

    if late_night_total > daytime_total * 0.1 and late_night_total > 500: # Significant late night spending
        triggers.append({
            "trigger": "late_night_impulse_spending",
            "description": "Noticeable spending late at night often indicates potential impulse purchases or boredom-driven spending.",
            "impact_details": f"Total late-night spending: ₹{late_night_total:.2f}",
            "recommendation": "Implement a '24-hour rule' for non-essential purchases after 10 PM to curb impulse buys. Consider disengaging from online shopping during these hours."
        })

   
    if user_text_input:
        user_input_lower = user_text_input.lower()
        if "stressed" in user_input_lower or "anxious" in user_input_lower or "down" in user_input_lower:
            triggers.append({
                "trigger": "self_reported_stress_anxiety",
                "description": "You mentioned feeling stressed/anxious, which can often lead to comfort or retail therapy spending.",
                "recommendation": "Be mindful of shopping as a coping mechanism. Explore non-financial stress-relief activities."
            })
        if "happy" in user_input_lower or "excited" in user_input_lower or "celebrating" in user_input_lower:
            triggers.append({
                "trigger": "self_reported_happiness_celebration",
                "description": "You mentioned feeling happy/celebratory. While good, this can sometimes lead to overspending on celebrations or treats.",
                "recommendation": "Enjoy your successes, but try to pre-plan celebratory spending to avoid exceeding your budget."
            })

    if not triggers:
        return {"summary": "No prominent emotional triggers identified from spending patterns or provided text."}
    return {"summary": "Potential emotional triggers identified.", "triggers": triggers}


async def identify_financial_biases(transactions: List[Dict[str, Any]], financial_goals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Detects common cognitive biases in user's financial behavior based on
    spending patterns and stated goals.

    Args:
        transactions: List of transaction dictionaries.
        financial_goals: List of financial goals, e.g., [{'name': 'Retirement', 'target_amount': 500000, 'saved': 10000, 'type': 'savings'}].

    Returns:
        A dictionary detailing identified biases and examples.
    """
    if not transactions:
        return {"summary": "No transactions provided for bias identification."}

    df = pd.DataFrame(transactions)
    df['amount'] = pd.to_numeric(df['amount'])
    df['date'] = pd.to_datetime(df['date'])
    biases = []

    
    total_income = df[df['type'] == 'income']['amount'].sum()
    total_discretionary_expense = df[~df['category'].isin(['Rent', 'Utilities', 'Groceries', 'Health', 'Education', 'Salary', 'Savings'])]['amount'].sum()

    if total_income > 0 and (total_discretionary_expense / total_income) > 0.4: # More than 40% of income on discretionary items
        # Check savings progress
        under_saved_goals = [g for g in financial_goals if g.get('type') == 'savings' and g.get('saved', 0) < g.get('target_amount', 0) * 0.2] # Less than 20% achieved
        if under_saved_goals:
            biases.append({
                "bias": "present_bias",
                "description": "A tendency to prioritize immediate gratification over long-term goals. High discretionary spending while long-term savings are lagging.",
                "impact": f"You spend a high percentage ({total_discretionary_expense/total_income*100:.1f}%) on discretionary items, and some savings goals are significantly behind.",
                "recommendation": "Consider automating savings transfers immediately after receiving income to 'pay yourself first'."
            })

    
    round_number_transactions = df[df['amount'].apply(lambda x: x % 100 == 0 or x % 10 == 0)]
    if len(round_number_transactions) > len(df) * 0.20 and len(df) > 10: # More than 20% are round numbers
        biases.append({
            "bias": "anchoring_bias_round_numbers",
            "description": "Spending frequently in round numbers may indicate an unconscious 'anchoring' to specific price points rather than evaluating true value.",
            "impact": f"{len(round_number_transactions)/len(df)*100:.1f}% of your transactions are at round numbers.",
            "recommendation": "Before making a purchase, pause and evaluate if the item's value truly matches its price, rather than being influenced by a simple, round figure. Try setting budgets with non-round numbers."
        })

    
    subscription_categories = ['Subscription', 'Streaming', 'Software', 'Membership', 'Service Fee']
    recent_subscriptions = df[df['category'].isin(subscription_categories) & (df['type'] == 'expense')]

    if len(recent_subscriptions.drop_duplicates(subset='description')) > 3: # More than 3 distinct active subscriptions
        total_sub_cost = recent_subscriptions['amount'].sum()
        biases.append({
            "bias": "loss_aversion_subscriptions",
            "description": "You seem to have multiple recurring subscriptions. People often hold onto subscriptions even when unused due to the 'pain' of losing access, a form of loss aversion.",
            "impact": f"Estimated total subscription spending over 3 months: ₹{total_sub_cost:.2f}. Reviewing them could save money.",
            "recommendation": "Conduct a 'subscription audit'. For each subscription, ask if you truly use and value it enough to justify the cost. Cancel anything you don't actively use."
        })

    if not biases:
        return {"summary": "No prominent financial biases identified based on current data."}
    return {"summary": "Financial biases identified.", "biases": biases}



async def generate_financial_nudge(
    identified_biases: Optional[List[Dict[str, Any]]] = None,
    spending_insights: Optional[Dict[str, Any]] = None,
    financial_goals: Optional[List[Dict[str, Any]]] = None,
    user_preference: str = "gentle"
) -> Dict[str, Any]:
    """
    Generates personalized "nudges" to encourage better financial behavior,
    based on identified biases, spending patterns, and goals.

    Args:
        identified_biases: List of identified biases from identify_financial_biases.
        spending_insights: Insights from analyze_spending_patterns.
        financial_goals: User's financial goals.
        user_preference: User's preference for nudge style (e.g., "gentle", "direct", "informative").

    Returns:
        A dictionary containing the generated nudge message.
    """
    nudges = []

    
    if identified_biases:
        for bias_info in identified_biases:
            nudges.append(bias_info.get("recommendation", f"Consider action related to {bias_info['bias']}."))

    
    if spending_insights:
        if spending_insights.get("impulse_indicators", {}).get("risk_level") == "high":
            nudges.append("Your impulse spending seems a bit high. Try implementing a '24-hour rule' for non-essential purchases: if you want something, wait a day before buying it. You might find you no longer need it!")
        if spending_insights.get("average_daily_spending", 0) > 1000 and spending_insights.get("total_spending_by_category", {}).get("Dining", 0) > 2000: # Example threshold
             nudges.append("Dining out is a significant part of your spending. Perhaps try cooking at home more often, or look for budget-friendly meal options, to save a bit more.")
        if spending_insights.get("high_frequency_categories"):
            freq_cats = ", ".join(spending_insights["high_frequency_categories"][:2]) 
            nudges.append(f"You have many small, frequent purchases in categories like {freq_cats}. Small amounts add up quickly! Try setting a daily or weekly limit for these categories.")


    
    if financial_goals:
        for goal in financial_goals:
            if goal.get('type') == 'savings' and goal.get('target_amount', 0) > 0:
                progress = goal.get('saved', 0) / goal['target_amount']
                if progress < 0.2:
                    nudges.append(f"Your '{goal['name']}' goal is just getting started. Automating a small, consistent transfer to this goal each payday can make a huge difference over time, leveraging the power of compounding.")
                elif progress < 0.5:
                    nudges.append(f"You're making good progress on your '{goal['name']}' goal! Keep going. Review if you can slightly increase your contributions to reach it faster.")
                elif progress >= 0.9 and progress < 1.0:
                    nudges.append(f"You're almost at your '{goal['name']}' goal! A final push could get you there soon. Well done!")

    if not nudges:
        return {"nudge": "Great job with your financial awareness! Keep up the mindful money practices."}

    
    if user_preference == "direct" and nudges:
        return {"nudge": f"Direct suggestion: {nudges[0]}"}
    elif user_preference == "informative" and nudges:
        return {"nudge": "Here are some personalized suggestions based on your financial patterns:\n" + "\n".join([f"- {n}" for n in nudges])}
    else: 
        return {"nudge": np.random.choice(nudges)}