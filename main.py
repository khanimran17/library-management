from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import requests

app = Flask(__name__)

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
db = SQLAlchemy(app)


# Define the Book model
class Book(db.Model):
    __tablename__ = 'book'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    stock = db.Column(db.Integer, default=0)
    deleted = db.Column(db.Boolean, default=False)


# Define the Member model
class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    debt = db.Column(db.Float, default=0.0)  # Add the 'debt' column


# Define the Transaction model
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    issued_date = db.Column(db.DateTime, nullable=False)
    return_date = db.Column(db.DateTime, nullable=True)
    book = db.relationship('Book', backref=db.backref('transactions', lazy=True, cascade='all, delete-orphan'))
    member = db.relationship('Member', backref=db.backref('transactions', lazy=True))
    due_date = db.Column(db.DateTime)


# Define the index route
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        member_id = request.form['member_id']
        book_id = request.form['book_id']

        result = issue_book(member_id, book_id)

        if result == "Out of stock":
            return "Out of stock"
        else:
            return redirect(url_for('list_books'))

    return render_template('index.html')


# Define the list_books route
@app.route('/books')
def list_books():
    books = Book.query.all()
    return render_template('list_books.html', books=books)


# Define the list_members route
@app.route('/members')
def list_members():
    members = Member.query.all()
    return render_template('list_members.html', members=members)


# Define the add_member route
@app.route('/members/add', methods=['GET', 'POST'])
def add_member():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        debt = request.form['debt']

        new_member = Member(name=name, email=email, debt=debt)
        db.session.add(new_member)
        db.session.commit()

        return redirect(url_for('list_members'))

    return render_template('add_member.html')


# Define the edit_member route
@app.route('/members/edit/<int:id>', methods=['GET', 'POST'])
def edit_member(id):
    member = Member.query.get_or_404(id)

    if request.method == 'POST':
        member.name = request.form['name']
        member.email = request.form['email']
        member.debt = request.form['debt']

        db.session.commit()
        return redirect(url_for('list_members'))

    return render_template('edit_member.html', member=member)


# Define the delete_member route
@app.route('/members/delete/<int:id>', methods=['GET', 'POST'])
def delete_member(id):
    if request.method == 'POST':
        member = Member.query.get_or_404(id)
        db.session.delete(member)
        db.session.commit()
        return redirect(url_for('list_members'))


# Define the add_book route
@app.route('/books/add', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        stock = request.form['stock']

        new_book = Book(title=title, author=author, stock=stock)
        db.session.add(new_book)
        db.session.commit()

        return redirect(url_for('list_books'))

    return render_template('add_book.html')


# Define the edit_book route
@app.route('/books/edit/<int:id>', methods=['GET', 'POST'])
def edit_book(id):
    book = Book.query.get_or_404(id)

    if request.method == 'POST':
        book.title = request.form['title']
        book.author = request.form['author']
        book.stock = request.form['stock']

        db.session.commit()
        return redirect(url_for('list_books'))

    return render_template('edit_book.html', book=book)


# Define the delete_book route
@app.route('/books/delete/<int:id>', methods=['POST'])
def delete_book(id):
    book = Book.query.get_or_404(id)
    db.session.delete(book)
    db.session.commit()
    return redirect(url_for('list_books'))


# Define the issue_book function
def issue_book(member_id, book_id):
    book = Book.query.get(book_id)
    if book:
        member = Member.query.get(member_id)
        if member:
            if book.stock > 0:
                if member.debt <= 500:
                    issued_date = datetime.now()
                    transaction = Transaction(
                        member_id=member_id,
                        book_id=book_id,
                        issued_date=issued_date,
                        return_date=None
                    )

                    book.stock -= 1
                    db.session.add(transaction)
                    db.session.commit()
                    return "Issued successfully"
                else:
                    return "Member has outstanding debt exceeding Rs. 500"
            else:
                return "Out of stock"
        else:
            return "Member not found"
    else:
        return "Book not found"


# Define the issue_book_route route
@app.route('/issue_book', methods=['POST'])
def issue_book_route():
    if request.method == 'POST':
        member_id = request.form['member_id']
        book_id = request.form['book_id']

        result = issue_book(member_id, book_id)

        if result == "Out of stock":
            return "Out of stock"
        else:
            return result


# Define the late fee rate
LATE_FEE_RATE = 10


# Define the return_book function
def return_book(transaction_id):
    transaction = Transaction.query.get(transaction_id)
    if transaction:
        book = Book.query.get(transaction.book_id)
        if book:
            if transaction.return_date is None:
                transaction.return_date = datetime.now()
                db.session.commit()
                if transaction.due_date and transaction.return_date > transaction.due_date:
                    days_late = (transaction.return_date - transaction.due_date).days
                    late_fees = days_late * LATE_FEE_RATE

                    member = Member.query.get(transaction.member_id)
                    member.debt += late_fees
                    db.session.commit()

                    return "Book returned successfully with late fees of Rs. {}".format(late_fees)
                else:
                    return "Book returned successfully"
            else:
                return "Book already returned"
        else:
            return "Book not found"
    else:
        return "Transaction not found"


# Define the return_book_route route
@app.route('/return_book', methods=['POST'])
def return_book_route():
    if request.method == 'POST':
        transaction_id = request.form['transaction_id']

        result = return_book(transaction_id)

        if result == "Invalid transaction or book already returned":
            return "Invalid transaction or book already returned"
        else:
            return result


# Define the import_books_form route
@app.route('/import_books_form', methods=['GET'])
def import_books_form():
    return render_template('import_books.html')


# Define the import_books route
@app.route('/import_books', methods=['POST'])
def import_books():
    num_books_to_import = int(request.form['num_books'])

    # API URL
    api_url = 'https://frappe.io/api/method/frappe-library?page=2&title=and'
    response = requests.get(api_url)

    if response.status_code != 200:
        return "Failed to fetch data from the API", 500

    try:
        books_data = response.json()['message']
    except ValueError:
        return "Invalid JSON data in API response", 500

    for i, book_data in enumerate(books_data[:num_books_to_import], start=1):
        title = book_data.get('title', 'Unknown Title')
        author = book_data.get('authors', 'Unknown Author')

        new_book = Book(title=title, author=author, stock=1)
        db.session.add(new_book)

    db.session.commit()
    return f"Successfully imported {num_books_to_import} books into the database"


# Run the app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        app.run(debug=True)
