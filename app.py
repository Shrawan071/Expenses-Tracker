# app.py (Flask backend)
from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import calendar
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
db = SQLAlchemy(app)

class Expense(db.Model):
    __tablename__ = 'Expenses'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, nullable=True)
    rate = db.Column(db.Float, nullable=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Budget(db.Model):
    __tablename__ = 'Budget'
    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.String(20), nullable=False, unique=True)
    amount = db.Column(db.Float, nullable=False)

class ExpenseHistory(db.Model):
    __tablename__ = 'ExpenseHistory'
    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.String(20), nullable=False, unique=True)
    data = db.Column(db.Text, nullable=False)  # JSON string of all expenses for the month
    total = db.Column(db.Float, nullable=False)
    budget = db.Column(db.Float, nullable=False)

with app.app_context():
    db.create_all()

# -------------- Helper -----------------

def get_current_month():
    now = datetime.now()
    return now.strftime('%B-%Y')

def archive_previous_month():
    current_month = get_current_month()
    existing_budget = Budget.query.filter_by(month=current_month).first()
    if not existing_budget:
        # archive old data
        last_month = datetime.now().replace(day=1) - timedelta(days=1)
        last_month_str = last_month.strftime('%B-%Y')
        last_expenses = Expense.query.all()
        if last_expenses:
            expense_data = [
                {
                    "title": e.title,
                    "quantity": e.quantity,
                    "rate": e.rate,
                    "amount": e.amount,
                    "category": e.category,
                    "date": e.date.strftime('%Y-%m-%d'),
                    "created_at": e.created_at.strftime('%Y-%m-%d %H:%M:%S')
                }
                for e in last_expenses
            ]

            total = sum([e['amount'] for e in expense_data])
            budget_obj = Budget.query.filter_by(month=last_month_str).first()
            budget_val = budget_obj.amount if budget_obj else 0

            # Store history
            history = ExpenseHistory(month=last_month_str, data=json.dumps(expense_data), total=total, budget=budget_val)
            db.session.add(history)

            # Clear current data
            Expense.query.delete()
            db.session.commit()

# ---------------- Routes ----------------

@app.route('/')
def index():
    archive_previous_month()
    current_month = get_current_month()
    budget_entry = Budget.query.filter_by(month=current_month).first()
    budget = budget_entry.amount if budget_entry else None
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    total = sum([e.amount for e in expenses])
    return render_template('index.html', expenses=expenses, total=total, budget=budget, current_month=current_month, mode_display="Current Month")

@app.route('/set_budget', methods=['POST'])
def set_budget():
    mode = request.form['mode']
    amount = float(request.form['budget'])
    if mode == 'current':
        month = get_current_month()
    elif mode == 'range':
        from_date = request.form['from']
        to_date = request.form['to']
        month = f"{from_date} to {to_date}"
    elif mode == 'select':
        month = f"{calendar.month_name[int(request.form['month'])]}-{request.form['year']}"
    else:
        month = get_current_month()

    existing = Budget.query.filter_by(month=month).first()
    if not existing:
        new_budget = Budget(month=month, amount=amount)
        db.session.add(new_budget)
        db.session.commit()
    return redirect('/')

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        title = request.form['title']
        quantity = request.form.get('quantity')
        rate = request.form.get('rate')
        amount = request.form.get('amount')

        if quantity and rate and not amount:
            amount = float(quantity) * float(rate)
        elif amount:
            amount = float(amount)
        else:
            amount = 0

        category = request.form['category']
        date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()

        new_expense = Expense(
            title=title,
            quantity=float(quantity) if quantity else None,
            rate=float(rate) if rate else None,
            amount=amount,
            category=category,
            date=date
        )
        db.session.add(new_expense)
        db.session.commit()
        return redirect('/')
    return render_template('add.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    exp = Expense.query.get_or_404(id)
    if request.method == 'POST':
        exp.title = request.form['title']
        exp.quantity = float(request.form['quantity']) if request.form.get('quantity') else None
        exp.rate = float(request.form['rate']) if request.form.get('rate') else None
        exp.amount = float(request.form['amount'])
        exp.category = request.form['category']
        exp.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        db.session.commit()
        return redirect('/')
    return render_template('edit.html', expense=exp)

@app.route('/delete/<int:id>')
def delete(id):
    exp = Expense.query.get_or_404(id)
    db.session.delete(exp)
    db.session.commit()
    return redirect('/')

@app.route('/history')
def history():
    records = ExpenseHistory.query.order_by(ExpenseHistory.id.desc()).all()
    history_data = {}
    for r in records:
        history_data[r.month] = {
            "budget": r.budget,
            "total": r.total,
            "expenses": json.loads(r.data)
        }
    return render_template('history.html', history=history_data)

if __name__ == '__main__':
    app.run(debug=True)
