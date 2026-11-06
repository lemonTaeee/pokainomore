# PokaiNoMore

A financial tracking web application designed for university students to manage monthly budgets, track expenses and predict when their available funds may run out (the "_Pokai_" date) based on daily spending patterns.

## Features

- **Pokai Date Prediction:** Estimates when the remaining budget is expected to reach zero based on daily spending trends.
- **Income & Expense Tracking:** Records allowances, additional income and expenses by category, including Food & Drink, Transportation, Yuran and Groceries.
- **Budget Overview:** Allows users to set a monthly budget and monitor their remaining balance, including additional income.
- **Spending Trends:** Displays daily balance changes throughout the active month using an interactive line chart.
- **Quick Analytics:** Shows the highest expense, lowest expense and top spending category for the current month.
- **Survival Mode:** Provides a recommended daily spending limit to help users manage their remaining budget.
- **Timezone Synchronisation:** Uses Malaysia Time (MYT / UTC+8) for transaction timestamps.

## Tech Stack

- **Backend:** Python, Flask, SQLAlchemy
- **Database:** PostgreSQL (Supabase)
- **Frontend:** HTML, Tailwind CSS, JavaScript, Chart.js
- **Deployment:** Render

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/lemonTaeee/pokainomore.git
cd pokainomore
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate the environment on Windows:

```bash
venv\Scripts\activate
```

For macOS/Linux:

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install flask flask-sqlalchemy psycopg2-binary werkzeug gunicorn
```

### 4. Configure environment variables

Set up the required environment variables for your Supabase PostgreSQL database connection before running the application.

### 5. Run the application

```bash
python app.py
```

Open the application in your browser:

```text
http://127.0.0.1:5000
```

## Deployment

The application is deployed using Render.

**Live Demo:** https://pokainomore.onrender.com

## Updating the Repository (Example)

After making changes to the project files, run the following commands to push updates to GitHub:

```bash
git add README.md
git commit -m "Update README"
git push origin main
```
