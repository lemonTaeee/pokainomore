from app import app
from database import db, Student, Budget, Transaction
from datetime import date, timedelta

def seed_database():
    with app.app_context():
        # Clear existing data to avoid primary key conflicts
        db.session.query(Transaction).delete()
        db.session.query(Budget).delete()
        db.session.query(Student).delete()
        db.session.commit()

        # 1. Create a test student
        test_student = Student(
            username="student_test",
            password="password123"
        )
        db.session.add(test_student)
        db.session.commit()

        # 2. Add budget limit (e.g., RM 500 for October 2026)
        october_budget = Budget(
            amount="500.00",
            month_year="10-2026",
            student_id=test_student.student_id
        )
        db.session.add(october_budget)
        db.session.commit()

        # 3. Add mock daily expenses over the last 5 days
        today = date.today()
        sample_expenses = [
            (today - timedelta(days=4), "15.50", "Expense", "Nasi Kandar Lunch"),
            (today - timedelta(days=3), "8.00", "Expense", "Boba Tea"),
            (today - timedelta(days=2), "22.00", "Expense", "Groceries"),
            (today - timedelta(days=1), "12.00", "Expense", "Bus Fare & Snack"),
            (today, "18.50", "Expense", "Dinner with Friends"),
        ]

        for entry_date, amount, t_type, desc in sample_expenses:
            trx = Transaction(
                amount=amount,
                transaction_type=t_type,
                description=desc,
                student_id=test_student.student_id
            )
            db.session.add(trx)

        db.session.commit()
        print("Successfully seeded sample data into Supabase!")

if __name__ == "__main__":
    seed_database()