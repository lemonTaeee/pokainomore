import calendar
from collections import defaultdict
from datetime import datetime, timedelta
import os
from flask import Flask, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

MYT = timezone(timedelta(hours=8))
app = Flask(__name__)

# ----------------------------------------------------------------------
# DATABASE CONFIGURATION & SECRET KEY
# ----------------------------------------------------------------------
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "postgresql+psycopg2://postgres.qdijmccwmoxakkngfsjv:3gGs6QfPXyLqfPfl@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.urandom(24).hex()

db = SQLAlchemy(app)

# ----------------------------------------------------------------------
# DATABASE MODELS
# ----------------------------------------------------------------------

class Student(db.Model):
    __tablename__ = "student"
    student_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    transactions = db.relationship("Transaction", backref="student", lazy=True)
    budgets = db.relationship("Budget", backref="student", lazy=True)

class Transaction(db.Model):
    __tablename__ = "transaction"
    transaction_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.student_id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    transaction_type = db.Column(db.String(50), default="Expense")
    created_at = db.Column(
        db.String(50), default=lambda: datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S")
    )

class Budget(db.Model):
    __tablename__ = "budget"
    budget_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.student_id"), nullable=False)
    total_budget = db.Column(db.Float, nullable=False, default=500.0)
    month = db.Column(db.String(20), default=lambda: datetime.now().strftime("%B %Y"))

# ----------------------------------------------------------------------
# AUTHENTICATION ROUTES
# ----------------------------------------------------------------------

@app.route("/")
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        student = Student.query.filter_by(username=username).first()

        if student and check_password_hash(student.password, password):
            return redirect(url_for("show_dashboard", student_id=student.student_id))
        else:
            return render_template("login.html", error="Invalid username or password.")

    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            return render_template("signup.html", error="Passwords do not match.")

        existing_user = Student.query.filter_by(username=username).first()
        if existing_user:
            return render_template("signup.html", error="Username already taken.")

        hashed_password = generate_password_hash(password, method="scrypt")
        new_student = Student(username=username, password=hashed_password)
        db.session.add(new_student)
        db.session.commit()

        default_budget = Budget(student_id=new_student.student_id, total_budget=500.00)
        db.session.add(default_budget)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("signup.html")

# ----------------------------------------------------------------------
# BUDGET & DASHBOARD ROUTES
# ----------------------------------------------------------------------

@app.route("/set-budget/<int:student_id>", methods=["POST"])
def set_budget(student_id):
    new_amount = float(request.form.get("total_budget", 500.0))
    student_budget = Budget.query.filter_by(student_id=student_id).first()
    
    if student_budget:
        student_budget.total_budget = new_amount
    else:
        student_budget = Budget(student_id=student_id, total_budget=new_amount)
        db.session.add(student_budget)
        
    db.session.commit()
    return redirect(url_for("show_dashboard", student_id=student_id))

@app.route("/dashboard/<int:student_id>")
def show_dashboard(student_id):
    student = Student.query.get_or_404(student_id)
    now = datetime.now(MYT)

    # 1. Fetch budget
    student_budget = Budget.query.filter_by(student_id=student_id).first()
    total_budget = student_budget.total_budget if student_budget else 500.00

    # 2. Fetch current month transactions ONLY
    current_month_str = now.strftime("%Y-%m")
    all_transactions = (
        Transaction.query.filter_by(student_id=student_id)
        .order_by(Transaction.created_at.asc())
        .all()
    )

    transactions = [
        t for t in all_transactions
        if t.created_at and t.created_at.startswith(current_month_str)
    ]

    # Calculate Expenses (anything not Income) vs Income
    total_spent = sum(t.amount for t in transactions if t.transaction_type != "Income")
    total_income = sum(t.amount for t in transactions if t.transaction_type == "Income")
    
    effective_budget = total_budget + total_income
    remaining_balance = effective_budget - total_spent

    # 3. Dynamic Chart Trajectory (Strictly Chronological)
    sorted_txs = []
    for tx in transactions:
        try:
            tx_dt = datetime.strptime(tx.created_at, "%Y-%m-%d %H:%M:%S")
        except Exception:
            tx_dt = now
        # Positive for Income, Negative for Expenses
        change = tx.amount if tx.transaction_type == "Income" else -tx.amount
        sorted_txs.append((tx_dt, change))

    sorted_txs.sort(key=lambda item: item[0])

    daily_balances = {}
    running_balance = total_budget

    for tx_dt, change in sorted_txs:
        running_balance += change
        date_label = tx_dt.strftime("%b %d")
        daily_balances[date_label] = round(running_balance, 2)

    chart_labels = [f"{now.strftime('%b')} 01"]
    chart_values = [total_budget]

    for label, val in daily_balances.items():
        if label == chart_labels[0]:
            chart_values[0] = val
        else:
            chart_labels.append(label)
            chart_values.append(val)

    # 4. Time & Pokai Calculations
    _, total_days_in_month = calendar.monthrange(now.year, now.month)
    days_passed = now.day
    days_left_in_month = max(1, total_days_in_month - days_passed + 1)

    recommended_daily_limit = (
        max(0.0, remaining_balance / days_left_in_month)
        if remaining_balance > 0
        else 0.0
    )

    avg_daily_spend = (
        total_spent / days_passed if days_passed > 1 and total_spent > 0 else 0
    )

    if avg_daily_spend > 0 and remaining_balance > 0:
        days_until_pokai = int(remaining_balance // avg_daily_spend)
        pokai_dt = now + timedelta(days=days_until_pokai)
        pokai_date_str = pokai_dt.strftime("%Y-%m-%d")
    elif remaining_balance <= 0:
        days_until_pokai = 0
        pokai_date_str = "Already Pokai!"
    else:
        days_until_pokai = days_left_in_month
        pokai_date_str = "Safe for now"

    # 5. Dynamic Spending Insights Calculations
    highest_expense = None
    lowest_expense = None
    top_category = None

    expense_txs = [t for t in transactions if t.transaction_type != "Income"]
    if expense_txs:
        sorted_by_amount = sorted(expense_txs, key=lambda t: t.amount, reverse=True)
        highest_expense = {
            "title": sorted_by_amount[0].description or sorted_by_amount[0].transaction_type,
            "amount": float(sorted_by_amount[0].amount),
        }
        lowest_expense = {
            "title": sorted_by_amount[-1].description or sorted_by_amount[-1].transaction_type,
            "amount": float(sorted_by_amount[-1].amount),
        }

        category_totals = defaultdict(float)
        for t in expense_txs:
            cat_name = t.transaction_type or t.description or "General"
            category_totals[cat_name] += float(t.amount)

        if category_totals and total_spent > 0:
            top_cat_name = max(category_totals, key=category_totals.get)
            top_cat_amount = category_totals[top_cat_name]
            top_cat_percentage = (top_cat_amount / total_spent) * 100
            top_category = {
                "name": top_cat_name,
                "amount": top_cat_amount,
                "percentage": top_cat_percentage,
            }

    prediction_data = {
        "student_name": student.username,
        "total_budget": total_budget,
        "total_income": total_income,
        "current_spent": total_spent,
        "remaining_budget": remaining_balance,
        "pokai_date": pokai_date_str,
        "days_left": days_until_pokai,
        "recommended_daily_limit": round(recommended_daily_limit, 2),
        "chart_labels": chart_labels,
        "chart_values": chart_values,
        "current_month_name": now.strftime("%B %Y"),
        "highest_expense": highest_expense,
        "lowest_expense": lowest_expense,
        "top_category": top_category,
    }

    return render_template(
        "dashboard.html",
        data=prediction_data,
        student_id=student_id,
        active_page="dashboard",
    )

@app.route("/history/<int:student_id>")
def show_history(student_id):
    tx_list = Transaction.query.filter_by(student_id=student_id).all()
    return render_template(
        "history.html",
        transactions=tx_list,
        student_id=student_id,
        active_page="history",
    )

@app.route("/add-transaction/<int:student_id>", methods=["GET", "POST"])
def add_transaction(student_id):
    if request.method == "POST":
        amount = float(request.form.get("amount", 0))
        description = request.form.get("description")
        flow_type = request.form.get("flow_type", "Expense")
        
        transaction_type = "Income" if flow_type == "Income" else request.form.get("transaction_type", "General")

        new_tx = Transaction(
            student_id=student_id,
            amount=amount,
            description=description,
            transaction_type=transaction_type,
        )
        db.session.add(new_tx)
        db.session.commit()

        return redirect(url_for("show_dashboard", student_id=student_id))

    return render_template(
        "add_transaction.html",
        student_id=student_id,
        active_page="add_transaction",
    )

# ----------------------------------------------------------------------
# DATABASE INITIALIZATION
# ----------------------------------------------------------------------
with app.app_context():
    try:
        db.create_all()
        print("--> Database synchronized successfully!")
    except Exception as e:
        print(f"--> Database Notice: {e}")

if __name__ == "__main__":
    app.run(debug=True, port=5000)