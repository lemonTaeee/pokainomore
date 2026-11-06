from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Student(db.Model):
    __tablename__ = "student"
    student_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)


class Budget(db.Model):
    __tablename__ = "budget"
    budget_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("student.student_id"), nullable=False
    )
    amount = db.Column(db.Float, nullable=False)


class Transaction(db.Model):
    __tablename__ = "transaction"
    transaction_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("student.student_id"), nullable=False
    )
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(50))
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)