# database.py
import sqlite3
import csv
from pathlib import Path

DB_NAME = "library.db"
DATA_DIR = Path(__file__).parent / "data"

def create_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def create_schema(conn):
    c = conn.cursor()
    c.executescript('''
    DROP TABLE IF EXISTS FINES;
    DROP TABLE IF EXISTS BOOK_LOANS;
    DROP TABLE IF EXISTS BOOK_AUTHORS;
    DROP TABLE IF EXISTS BORROWER;
    DROP TABLE IF EXISTS BOOK;
    DROP TABLE IF EXISTS AUTHORS;

    CREATE TABLE AUTHORS (
        Author_id INTEGER PRIMARY KEY,
        Name TEXT NOT NULL
    );

    CREATE TABLE BOOK (
        Isbn TEXT PRIMARY KEY,
        Title TEXT NOT NULL
    );

    CREATE TABLE BOOK_AUTHORS (
        Author_id INTEGER REFERENCES AUTHORS(Author_id) ON DELETE CASCADE,
        Isbn TEXT REFERENCES BOOK(Isbn) ON DELETE CASCADE,
        PRIMARY KEY (Author_id, Isbn)
    );

    CREATE TABLE BORROWER (
        Card_id TEXT PRIMARY KEY,
        Ssn TEXT NOT NULL UNIQUE CHECK(length(Ssn) = 11),
        Bname TEXT NOT NULL,
        Address TEXT NOT NULL,
        Phone TEXT
    );

    CREATE TABLE BOOK_LOANS (
        Loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
        Isbn TEXT NOT NULL REFERENCES BOOK(Isbn),
        Card_id TEXT NOT NULL REFERENCES BORROWER(Card_id),
        Date_out DATE NOT NULL,
        Due_date DATE NOT NULL,
        Date_in DATE
    );

    CREATE TABLE FINES (
        Loan_id INTEGER PRIMARY KEY REFERENCES BOOK_LOANS(Loan_id) ON DELETE CASCADE,
        Fine_amt REAL NOT NULL DEFAULT 0.0,
        Paid INTEGER NOT NULL DEFAULT 0 CHECK(Paid IN (0,1))
    );

    CREATE INDEX idx_book_title ON BOOK(Title COLLATE NOCASE);
    CREATE INDEX idx_author_name ON AUTHORS(Name COLLATE NOCASE);
    CREATE INDEX idx_active_loans ON BOOK_LOANS(Date_in);
    ''')
    conn.commit()

def load_data(conn):
    c = conn.cursor()

    # Authors
    with open(DATA_DIR / "authors.csv", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        c.executemany("INSERT OR IGNORE INTO AUTHORS (Author_id, Name) VALUES (?, ?)", reader)

    # Book
    with open(DATA_DIR / "book.csv", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        c.executemany("INSERT OR IGNORE INTO BOOK (Isbn, Title) VALUES (?, ?)", reader)

    # Book_Authors
    with open(DATA_DIR / "book_authors.csv", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        c.executemany("INSERT OR IGNORE INTO BOOK_AUTHORS (Isbn, Author_id) VALUES (?, ?)", reader)

    # Borrower
    with open(DATA_DIR / "borrower.csv", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        c.executemany("INSERT OR IGNORE INTO BORROWER VALUES (?, ?, ?, ?, ?)", reader)

    conn.commit()
    print("All CSV data loaded successfully.")

def init_db():
    if not Path(DB_NAME).exists():
        conn = create_connection()
        create_schema(conn)
        load_data(conn)
        conn.close()
        print(f"Database '{DB_NAME}' created and populated.")
    else:
        print(f"Database '{DB_NAME}' already exists.")

if __name__ == "__main__":
    init_db()