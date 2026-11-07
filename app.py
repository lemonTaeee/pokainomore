import calendar
from datetime import datetime
import os
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import extract, func, text
from sqlalchemy.engine.url import make_url

app = Flask(__name__)

# ----------------------------------------------------------------------
# DATABASE CONFIGURATION & STALE CONNECTION FIX
# ----------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set.")

# Automatically direct Supabase pooler connection to port 6543 if set to 5432
if "pooler.supabase.com:5432" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace(
        "pooler.supabase.com:5432", "pooler.supabase.com:6543"
    )

# Ensure SQLAlchemy uses the psycopg2 driver
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://", "postgresql+psycopg2://", 1
    )
elif DATABASE_URL.startswith(
    "postgresql://"
) and not DATABASE_URL.startswith("postgresql+"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://", "postgresql+psycopg2://", 1
    )

# Ensure SSL mode is explicitly required
if "sslmode=" not in DATABASE_URL:
    separator = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL += f"{separator}sslmode=require"

# Log target for verification
try:
    db_url_parsed = make_url(DATABASE_URL)
    print(
        f"Database target: host={db_url_parsed.host}, port={db_url_parsed.port}, "
        f"username={db_url_parsed.username}, database={db_url_parsed.database}",
        flush=True,
    )
except Exception as e:
    print(f"Database URL parsing note: {e}", flush=True)

# SQLAlchemy Configuration
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = (
    os.environ.get("SECRET_KEY") or "pokainomore_secret_session_key_2026"
)

# Fix timeouts: Pre-ping connections and recycle idle connections every 5 mins
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_timeout": 30,
}

db = SQLAlchemy(app)


# ----------------------------------------------------------------------
# DATABASE MODELS
# ----------------------------------------------------------------------
class Student(db.Model):
    __tablename__ = "student"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    monthly_budget = db.Column(db.Float, nullable=False, default=1000.0)
    transactions = db.relationship(
        "Transaction", backref="student", lazy=True, cascade="all, delete-orphan"
    )


class Transaction(db.Model):
    __tablename__ = "transaction"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("student.id"), nullable=False
    )
    flow_type = db.Column(db.String(20), nullable=False, default="Expense")
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.now)


# ----------------------------------------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------------------------------------
def get_active_student_id():
    """Retrieves the active student ID from session, defaulting to 1."""
    return session.get("student_id", 1)


def get_budget_metrics(student_id):
    """Calculates dynamic spending metrics for the given student."""
    today = datetime.now()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_passed = max(1, today.day)
    days_left = max(1, days_in_month - today.day + 1)

    student = db.session.get(Student, student_id)
    if not student:
        student = Student(id=student_id, name="Student", monthly_budget=1000.0)
        db.session.add(student)
        db.session.commit()

    # Total expenses this month
    current_spent = (
        db.session.query(func.sum(Transaction.amount))
        .filter(
            Transaction.student_id == student_id,
            Transaction.flow_type == "Expense",
            extract("month", Transaction.date) == today.month,
            extract("year", Transaction.date) == today.year,
        )
        .scalar()
        or 0.0
    )

    # Total income/allowance added this month
    total_income = (
        db.session.query(func.sum(Transaction.amount))
        .filter(
            Transaction.student_id == student_id,
            Transaction.flow_type == "Income",
            extract("month", Transaction.date) == today.month,
            extract("year", Transaction.date) == today.year,
        )
        .scalar()
        or 0.0
    )

    effective_budget = student.monthly_budget + total_income
    remaining_budget = effective_budget - current_spent
    avg_daily_spend = current_spent / days_passed
    current_daily_limit = max(0.0, remaining_budget / days_left)

    return {
        "student": student,
        "current_spent": current_spent,
        "remaining_budget": remaining_budget,
        "avg_daily_spend": avg_daily_spend,
        "current_daily_limit": current_daily_limit,
        "days_left": days_left,
        "days_in_month": days_in_month,
        "days_passed": days_passed,
    }


# ----------------------------------------------------------------------
# AUTO-INITIALIZE & SYNC DB SCHEMA
# ----------------------------------------------------------------------
with app.app_context():
    try:
        # Validate table columns against current model definition
        db.session.execute(text("SELECT id, name, monthly_budget FROM student LIMIT 1;"))
    except Exception as e:
        db.session.rollback()
        print(f"Database schema mismatch detected ({e}). Rebuilding tables...", flush=True)
        db.drop_all()
        db.create_all()
        print("Database schema synchronized successfully!", flush=True)


# ----------------------------------------------------------------------
# CLEAN ROUTES (SESSION-BASED)
# ----------------------------------------------------------------------
@app.route("/")
@app.route("/dashboard")
def dashboard():
    student_id = get_active_student_id()
    session["student_id"] = student_id

    metrics = get_budget_metrics(student_id)

    recent_transactions = (
        Transaction.query.filter_by(student_id=student_id)
        .order_by(Transaction.date.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "dashboard.html",
        data=metrics,
        transactions=recent_transactions,
        student_id=student_id,
    )


@app.route("/add-transaction", methods=["GET", "POST"])
def add_transaction():
    student_id = get_active_student_id()
    session["student_id"] = student_id

    if request.method == "POST":
        flow_type = request.form.get("flow_type", "Expense")
        category = request.form.get("transaction_type", "General")
        amount_raw = request.form.get("amount", "0")
        description = request.form.get("description", "").strip()

        try:
            amount = float(amount_raw)
            if amount <= 0:
                raise ValueError("Amount must be greater than zero.")

            new_tx = Transaction(
                student_id=student_id,
                flow_type=flow_type,
                category=category,
                amount=amount,
                description=description,
                date=datetime.now(),
            )
            db.session.add(new_tx)
            db.session.commit()
            return redirect(url_for("dashboard"))
        except Exception as e:
            db.session.rollback()
            print(f"Error adding transaction: {e}")

    metrics = get_budget_metrics(student_id)
    return render_template(
        "add_transaction.html",
        remaining_budget=metrics["remaining_budget"],
        days_left_in_month=metrics["days_left"],
        avg_daily_spend=metrics["avg_daily_spend"],
        student_id=student_id,
    )


@app.route("/history")
def history():
    student_id = get_active_student_id()
    session["student_id"] = student_id

    transactions = (
        Transaction.query.filter_by(student_id=student_id)
        .order_by(Transaction.date.desc())
        .all()
    )

    return render_template(
        "history.html", transactions=transactions, student_id=student_id
    )


# ----------------------------------------------------------------------
# LEGACY REDIRECT HANDLERS (URL Clean-up)
# ----------------------------------------------------------------------
@app.route("/dashboard/<int:student_id>")
def legacy_dashboard(student_id):
    session["student_id"] = student_id
    return redirect(url_for("dashboard"))


@app.route("/add-transaction/<int:student_id>")
def legacy_add_transaction(student_id):
    session["student_id"] = student_id
    return redirect(url_for("add_transaction"))


@app.route("/history/<int:student_id>")
def legacy_history(student_id):
    session["student_id"] = student_id
    return redirect(url_for("history"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)