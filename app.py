from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
db = SQLAlchemy(app)

class Expense(db.Model):
    __tablename__ = 'Expenses'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)

@app.route('/')
def index():
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    total = sum([e.amount for e in expenses])
    return render_template('index.html', expenses=expenses, total=total)

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        title = request.form['title']
        amount = float(request.form['amount'])
        category = request.form['category']
        date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        new_expense = Expense(title=title, amount=amount, category=category, date=date)
        db.session.add(new_expense)
        db.session.commit()
        return redirect('/')
    return render_template('add.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    exp = Expense.query.get_or_404(id)
    if request.method == 'POST':
        exp.title = request.form['title']
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

if __name__ == '__main__':
    app.run(debug=True)
