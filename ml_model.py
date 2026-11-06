import calendar
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def predict_pokai_status(transactions, total_budget, student_id=None):
    today = datetime.now().date()
    _, total_days_in_month = calendar.monthrange(today.year, today.month)
    days_left_in_month = max(1, total_days_in_month - today.day + 1)

    # 1. Empty/Invalid state guard
    if not transactions or total_budget <= 0:
        return {
            "total_budget": float(total_budget),
            "current_spent": 0.0,
            "remaining_budget": float(total_budget),
            "daily_burn_rate": 0.0,
            "recommended_daily_limit": round(
                total_budget / days_left_in_month, 2
            ),
            "days_remaining_until_pokai": 999,
            "predicted_date": "N/A",
            "pokai_warning": False,
            "message": "No transactions recorded yet.",
        }

    df = pd.DataFrame(transactions)

    # Ensure amount is float
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    # 2. Robust Datetime Conversion
    # Convert 'created_at' column explicitly into datetime64 dtype
    created_at_dt = pd.to_datetime(df["created_at"], errors="coerce")

    # If parsing completely failed for all rows, fall back to row sequence
    if created_at_dt.isnull().all():
        df["day_index"] = np.arange(1, len(df) + 1)
    else:
        # Fill missing single dates with current timestamp
        created_at_dt = created_at_dt.fillna(pd.Timestamp.now())
        df["created_at_dt"] = created_at_dt
        df = df.sort_values("created_at_dt")

        # Extract pure Python date objects safely
        df["date_only"] = df["created_at_dt"].dt.date
        min_date = df["date_only"].min()

        # Calculate day index offset (Day 1, Day 2, etc.)
        df["day_index"] = (
            df["date_only"].apply(lambda d: (d - min_date).days) + 1
        )

    current_spent = float(df["amount"].sum())
    remaining_budget = max(0.0, total_budget - current_spent)
    recommended_daily_limit = round(remaining_budget / days_left_in_month, 2)

    # 3. Daily aggregation for Linear Regression
    daily_df = (
        df.groupby("day_index")["amount"]
        .sum()
        .cumsum()
        .reset_index(name="cumulative_spending")
    )

    X = daily_df[["day_index"]].values
    y = daily_df["cumulative_spending"].values

    model = LinearRegression()
    model.fit(X, y)

    daily_burn_rate = float(model.coef_[0])

    if daily_burn_rate <= 0:
        return {
            "total_budget": float(total_budget),
            "current_spent": round(current_spent, 2),
            "remaining_budget": round(remaining_budget, 2),
            "daily_burn_rate": 0.0,
            "recommended_daily_limit": recommended_daily_limit,
            "days_remaining_until_pokai": 999,
            "predicted_date": "N/A",
            "pokai_warning": False,
            "message": "Spending rate is secure.",
        }

    intercept = float(model.intercept_)
    target_day_index = (total_budget - intercept) / daily_burn_rate
    current_day_index = daily_df["day_index"].max()

    days_remaining_until_pokai = max(
        0, int(np.ceil(target_day_index - current_day_index))
    )
    predicted_depletion_date = today + timedelta(
        days=days_remaining_until_pokai
    )

    is_pokai_warning = days_remaining_until_pokai < days_left_in_month

    return {
        "total_budget": float(total_budget),
        "current_spent": round(current_spent, 2),
        "remaining_budget": round(remaining_budget, 2),
        "daily_burn_rate": round(daily_burn_rate, 2),
        "recommended_daily_limit": recommended_daily_limit,
        "days_remaining_until_pokai": days_remaining_until_pokai,
        "predicted_date": predicted_depletion_date.strftime("%Y-%m-%d"),
        "pokai_warning": is_pokai_warning,
    }