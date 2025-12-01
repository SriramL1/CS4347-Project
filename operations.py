# operations.py
import sqlite3
from datetime import date
from database import create_connection

def search_books(query: str):
    """
    Returns ALL books where the query appears in ISBN, Title, or ANY Author name
    Case-insensitive substring search (exactly as required)
    """
    conn = create_connection()
    c = conn.cursor()

    pattern = f"%{query.strip()}%"

    sql = """
    SELECT 
        b.Isbn,
        b.Title,
        GROUP_CONCAT(DISTINCT a.Name) AS authors,
        CASE 
            WHEN EXISTS(SELECT 1 FROM BOOK_LOANS bl 
                        WHERE bl.Isbn = b.Isbn AND bl.Date_in IS NULL)
            THEN 'OUT'
            ELSE 'IN'
        END AS availability
    FROM BOOK b
    LEFT JOIN BOOK_AUTHORS ba ON b.Isbn = ba.Isbn
    LEFT JOIN AUTHORS a ON ba.Author_id = a.Author_id
    WHERE LOWER(b.Isbn) LIKE LOWER(?)
       OR LOWER(b.Title) LIKE LOWER(?)
       OR LOWER(a.Name) LIKE LOWER(?)
    GROUP BY b.Isbn, b.Title
    ORDER BY b.Isbn
    """

    c.execute(sql, (pattern, pattern, pattern))
    rows = c.fetchall()
    conn.close()

    results = []
    for row in rows:
        authors = row[2] if row[2] else "Unknown"
        results.append({
            "isbn": row[0],
            "title": row[1],
            "authors": authors,
            "availability": row[3]
        })
    return results

# Teammates will implement these

def checkout_book(isbn, card_id): return "[Pending] Teammate"

def checkin_book(query):    # Teammate : Kimberly (Grace) Niemiec
    
    conn = create_connection()
    c = conn.cursor()

    pattern = f"%{query.strip()}%"

    # Find active loans for ISBN / card number / borrower name / substring

    sql1 = """
    SELECT bl.Loan_id, bl.Isbn, b.Title, br.Card_id, br.Name, bl.Due_date
    FROM BOOK_LOANS bl
    JOIN BOOK b ON bl.Isbn = b.Isbn
    JOIN BORROWER br ON bl.Card_id = br.Card_id
    WHERE bl.Date_in IS NULL
        AND (
            LOWER(bl.Isbn) LIKE LOWER(?)
            OR LOWER(br.Card_id) LIKE LOWER(?)
            OR LOWER(br.Name) LIKE LOWER(?)
        );
    """
    
    c.execute(sql1, (pattern, pattern, pattern))
    
    active_loans = c.fetchall()
    
    if len(active_loans) == 0:
        conn.close()
        return "Checkin failed. No active loans found matching this search."
    
    # Display active loans if found

    print("\nActive loans matching your search : ")
    print("- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -")

    for r, row in enumerate(active_loans, start=1):
        loan_id,isbn, title, card_id, name, due = row
        print(f"{r}. ISBN: {isbn} | Title: {title}")
        print(f"    Borrower: {name} (Card {card_id}) | Due: {due}")
        print("- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -")

    # Prompt user to select which active loan to checkin
    
    if len(active_loans) == 1:  # One active loan

        selection = 1

        print("Selecting current active loan . . .")

    else:                       # Multiple active loands

        while True:

            uInput = input(f"Enter the number of the loan you want to checkin (1-{len(active_loans)}): ")
            
            if uInput.isdigit():

                selection = int(uInput)
                
                if 1 <= selection <= len(active_loans):

                    break

            print("Checkin failed. Please enter a valid active loan number.")

    load_id = active_loans[selected_index - 1][0]   # Get loan_id of selected active loan

    # Process checkin / return for book
    
    return_date = date.today()
    
    sql2 = """
    UPDATE BOOK_LOANS
    SET Date_in = ?
    WHERE Loan_id = ?;
    """
    
    c.execute(sql2, (return_date, load_id))

    conn.commit()
    conn.close()

    return "Checkin successful"

def add_borrower(ssn, name, address, phone=None): return "[Pending] Teammate"

def pay_fines(card_id): return "[Pending] Teammate"

def refresh_fines(): pass
