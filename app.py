from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import calendar
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SECRET_KEY'] = 'your_secret_key_here'
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
    month = db.Column(db.String(40), nullable=False, unique=True)
    amount = db.Column(db.Float, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    mode = db.Column(db.String(10), nullable=False)

class ExpenseHistory(db.Model):
    __tablename__ = 'ExpenseHistory'
    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.String(40), nullable=False, unique=True)
    data = db.Column(db.Text, nullable=False)
    total = db.Column(db.Float, nullable=False)
    budget = db.Column(db.Float, nullable=False)
    mode = db.Column(db.String(10), nullable=False)

with app.app_context():
    db.create_all()

def get_current_month():
    now = datetime.now()
    return now.strftime('%B-%Y')

def should_archive():
    now = datetime.now().date()
    budget = Budget.query.first()
    return budget and now > budget.end_date

def archive_expenses():
    budget = Budget.query.first()
    if not budget:
        return

    existing = ExpenseHistory.query.filter_by(month=budget.month).first()
    if existing:
        return

    expenses = Expense.query.all()
    if expenses:
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
            for e in expenses
        ]
        total = sum(e['amount'] for e in expense_data)

        history = ExpenseHistory(
            month=budget.month,
            data=json.dumps(expense_data),
            total=total,
            budget=budget.amount,
            mode=budget.mode
        )
        db.session.add(history)
        db.session.delete(budget)
        Expense.query.delete()
        db.session.commit()

@app.route('/')
def index():
    if should_archive():
        archive_expenses()
    budget_entry = Budget.query.first()
    budget = budget_entry.amount if budget_entry else None
    current_month = budget_entry.month if budget_entry else get_current_month()
    mode_display = budget_entry.mode if budget_entry else ""
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    total = sum(e.amount for e in expenses)

    budgets = Budget.query.with_entities(Budget.month).all()
    histories = ExpenseHistory.query.with_entities(ExpenseHistory.month).all()
    existing_budgets = [b.month for b in budgets] + [h.month for h in histories]

    return render_template('index.html',
                           expenses=expenses,
                           total=total,
                           budget=budget,
                           current_month=current_month,
                           mode_display=mode_display,
                           now=datetime.now,
                           calendar=calendar,
                           str=str,
                           existing_budgets=existing_budgets)

@app.route('/check_duplicate', methods=['POST'])
def check_duplicate():
    month = request.json.get('month')
    exists_in_budget = Budget.query.filter_by(month=month).first() is not None
    exists_in_history = ExpenseHistory.query.filter_by(month=month).first() is not None
    return jsonify({'exists': exists_in_budget or exists_in_history})

@app.route('/set_budget', methods=['POST'])
def set_budget():
    mode = request.form['mode']
    amount = float(request.form['budget'])

    if mode == 'current':
        month = get_current_month()
        year = datetime.now().year
        month_number = datetime.now().month
        end_day = calendar.monthrange(year, month_number)[1]
        end_date = datetime(year, month_number, end_day).date()
    elif mode == 'range':
        from_date = datetime.strptime(request.form['from'], '%Y-%m-%d').date()
        to_date = datetime.strptime(request.form['to'], '%Y-%m-%d').date()
        month = f"{from_date} to {to_date}"
        end_date = to_date
    elif mode == 'select':
        month_number = int(request.form['month'])
        year = int(request.form['year'])
        month_name = calendar.month_name[month_number]
        month = f"{month_name}-{year}"
        end_day = calendar.monthrange(year, month_number)[1]
        end_date = datetime(year, month_number, end_day).date()
    else:
        month = get_current_month()
        end_date = datetime.now().date()

    exists_in_budget = Budget.query.filter_by(month=month).first()
    exists_in_history = ExpenseHistory.query.filter_by(month=month).first()
    if exists_in_budget or exists_in_history:
        flash(f"Budget for '{month}' is already set or archived. Please choose a different month or range.")
        return redirect(url_for('index'))

    db.session.query(Budget).delete()

    new_budget = Budget(month=month, amount=amount, end_date=end_date, mode=mode)
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

        if quantity and rate:
            amount = float(quantity) * float(rate)
        elif not amount:
            return "Amount is required if Quantity and Rate are not provided."
        else:
            amount = float(amount)

        category = request.form['category']
        date_str = request.form['date']
        date = datetime.strptime(date_str, '%Y-%m-%d').date()

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
        flash("Expense added successfully.")
        return redirect('/')
    return render_template('add.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    exp = Expense.query.get_or_404(id)
    if request.method == 'POST':
        exp.title = request.form['title']
        quantity = request.form.get('quantity')
        rate = request.form.get('rate')
        amount = request.form.get('amount')

        if quantity and rate:
            exp.amount = float(quantity) * float(rate)
        elif not amount:
            return "Amount is required if Quantity and Rate are not provided."
        else:
            exp.amount = float(amount)

        exp.quantity = float(quantity) if quantity else None
        exp.rate = float(rate) if rate else None
        exp.category = request.form['category']
        exp.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        db.session.commit()
        flash("Expense updated successfully.")
        return redirect('/')
    return render_template('edit.html', expense=exp)

@app.route('/delete/<int:id>')
def delete(id):
    exp = Expense.query.get_or_404(id)
    db.session.delete(exp)
    db.session.commit()
    flash("Expense deleted.")
    return redirect('/')

@app.route('/history')
def history():
    records = ExpenseHistory.query.order_by(ExpenseHistory.id.desc()).all()
    history_data = {}
    for r in records:
        history_data[r.month] = {
            "budget": r.budget,
            "total": r.total,
            "expenses": json.loads(r.data),
            "mode": r.mode
        }
    return render_template('history.html', history=history_data)

@app.route('/store_expenses')
def store_expenses():
    archive_expenses()
    db.session.query(Budget).delete()
    db.session.commit()
    flash("Expenses have been archived and budget reset. Please set a new budget.")
    return redirect('/')

@app.route('/reset_budget')
def reset_budget():
    db.session.query(Budget).delete()
    db.session.commit()
    flash("Budget has been reset.")
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
