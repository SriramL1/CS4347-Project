# views.py
from django.shortcuts import render
from django.db import connection, transaction
from datetime import date, timedelta


def search_view(request):
    """Search books by ISBN, title, or author name"""
    query = request.GET.get('q', '').strip()
    results = []

    if query:
        pattern = f"%{query}%"
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    b.Isbn,
                    b.Title,
                    GROUP_CONCAT(a.Name, ', ') AS authors,
                    CASE WHEN EXISTS(
                        SELECT 1 FROM BOOK_LOANS bl2 
                        WHERE bl2.Isbn = b.Isbn AND bl2.Date_in IS NULL
                    ) THEN 'Yes' ELSE 'No' END AS checked_out,
                    COALESCE(bl.Card_id, '-') AS borrower_id
                FROM BOOK b
                LEFT JOIN BOOK_AUTHORS ba ON b.Isbn = ba.Isbn
                LEFT JOIN AUTHORS a ON ba.Author_id = a.Author_id
                LEFT JOIN BOOK_LOANS bl ON b.Isbn = bl.Isbn AND bl.Date_in IS NULL
                WHERE LOWER(b.Isbn) LIKE LOWER(%s)
                   OR LOWER(b.Title) LIKE LOWER(%s)
                   OR LOWER(a.Name) LIKE LOWER(%s)
                GROUP BY b.Isbn, b.Title
                ORDER BY b.Isbn
            """, [pattern, pattern, pattern])

            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return render(request, 'search.html', {
        'query': query,
        'results': results,
    })


@transaction.atomic
def checkout_view(request):
    """Checkout a book to a borrower with validation"""
    message = ""
    success = False

    if request.method == "POST":
        isbn = request.POST.get('isbn', '').strip()
        card_id = request.POST.get('card_id', '').strip()

        if not isbn or not card_id:
            message = "Both ISBN and Card ID are required!"
        else:
            with connection.cursor() as cursor:
                # Check if book exists
                cursor.execute("SELECT Title FROM BOOK WHERE Isbn = %s", [isbn])
                book = cursor.fetchone()
                
                if not book:
                    message = f"Book with ISBN {isbn} not found!"
                else:
                    # Check if borrower exists
                    cursor.execute("SELECT Card_id FROM BORROWER WHERE Card_id = %s", [card_id])
                    borrower = cursor.fetchone()
                    
                    if not borrower:
                        message = f"Borrower with Card ID {card_id} not found!"
                    else:
                        # Check 3-book limit
                        cursor.execute(
                            "SELECT COUNT(*) FROM BOOK_LOANS WHERE Card_id = %s AND Date_in IS NULL",
                            [card_id]
                        )
                        active_loans = cursor.fetchone()[0]
                        
                        if active_loans >= 3:
                            message = f"Borrower {card_id} already has 3 books checked out!"
                        else:
                            # Check if already checked out
                            cursor.execute(
                                "SELECT Loan_id FROM BOOK_LOANS WHERE Isbn = %s AND Date_in IS NULL",
                                [isbn]
                            )
                            existing_loan = cursor.fetchone()
                            
                            if existing_loan:
                                message = f"Book {isbn} is already checked out!"
                            else:
                                # Checkout the book
                                today = date.today()
                                due_date = today + timedelta(days=2)  # Changed to 2 days
                                cursor.execute("""
                                    INSERT INTO BOOK_LOANS (Isbn, Card_id, Date_out, Due_date, Date_in)
                                    VALUES (%s, %s, %s, %s, NULL)
                                """, [isbn, card_id, today, due_date])
                                
                                message = (
                                    f"Book successfully checked out!<br>"
                                    f"Title: {book[0]}<br>"
                                    f"ISBN: {isbn}<br>"
                                    f"Borrower: {card_id}<br>"
                                    f"Due: {due_date}"
                                )
                                success = True

    return render(request, 'checkout.html', {
        'message': message,
        'success': success
    })


@transaction.atomic
def checkin_view(request):
    """Check in a book and calculate fines if overdue"""
    message = ""

    # Handle POST request first
    if request.method == "POST":
        loan_id = request.POST.get('loan_id')
        today = date.today()

        with connection.cursor() as cursor:
            # Get loan details before updating
            cursor.execute(
                "SELECT Due_date, Isbn FROM BOOK_LOANS WHERE Loan_id = %s AND Date_in IS NULL",
                [loan_id]
            )
            loan_info = cursor.fetchone()

            if not loan_info:
                message = "Invalid Loan ID or already checked in."
            else:
                due_date_str = loan_info[0]
                isbn = loan_info[1]
                
                # Parse due date (SQLite returns string)
                if isinstance(due_date_str, str):
                    due_date = date.fromisoformat(due_date_str)
                else:
                    due_date = due_date_str

                # Update Date_in
                cursor.execute(
                    "UPDATE BOOK_LOANS SET Date_in = %s WHERE Loan_id = %s",
                    [today, loan_id]
                )

                # Calculate and apply fine if overdue
                if today > due_date:
                    days_late = (today - due_date).days
                    fine_amount = round(days_late * 0.25, 2)
                    
                    cursor.execute("""
                        INSERT INTO FINES (Loan_id, Fine_amt, Paid)
                        VALUES (%s, %s, 0)
                        ON CONFLICT(Loan_id) DO UPDATE SET Fine_amt = excluded.Fine_amt
                    """, [loan_id, fine_amount])
                    
                    message = f"Book checked in. Overdue by {days_late} day(s) → ${fine_amount:.2f} fine applied."
                else:
                    message = "Book checked in successfully. No fine."

    # Load all currently checked-out books (after processing POST)
    loans = []
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                bl.Loan_id, 
                bl.Isbn, 
                b.Title, 
                bl.Card_id, 
                bl.Date_out, 
                bl.Due_date,
                CASE 
                    WHEN bl.Due_date < date('now') 
                    THEN CAST((julianday('now') - julianday(bl.Due_date)) * 0.25 AS REAL)
                    ELSE 0 
                END AS potential_fine
            FROM BOOK_LOANS bl
            JOIN BOOK b ON bl.Isbn = b.Isbn
            WHERE bl.Date_in IS NULL
            ORDER BY bl.Date_out DESC
        """)
        columns = [col[0] for col in cursor.description]
        loans = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return render(request, 'checkin.html', {
        'loans': loans,
        'message': message
    })


def fines_view(request):
    """View and pay fines"""
    message = ""
    fines = []
    total_unpaid = 0.0

    if request.method == "POST":
        if 'pay' in request.POST:
            loan_id = request.POST.get('loan_id')
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE FINES SET Paid = 1 WHERE Loan_id = %s AND Paid = 0",
                    [loan_id]
                )
                if cursor.rowcount > 0:
                    message = "Fine paid successfully!"
                else:
                    message = "Fine not found or already paid."
        
        elif 'pay_all' in request.POST:
            card_id = request.POST.get('card_id')
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE FINES 
                    SET Paid = 1 
                    WHERE Loan_id IN (
                        SELECT Loan_id FROM BOOK_LOANS WHERE Card_id = %s
                    ) AND Paid = 0
                """, [card_id])
                count = cursor.rowcount
                if count > 0:
                    message = f"Successfully paid {count} fine(s) for borrower {card_id}!"
                else:
                    message = f"No unpaid fines found for borrower {card_id}."

    # Load all fines
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                f.Loan_id,
                bl.Isbn,
                b.Title,
                bl.Card_id,
                br.Bname,
                f.Fine_amt,
                CASE WHEN f.Paid = 1 THEN 'Paid' ELSE 'Unpaid' END AS status,
                bl.Date_out,
                bl.Due_date,
                bl.Date_in
            FROM FINES f
            JOIN BOOK_LOANS bl ON f.Loan_id = bl.Loan_id
            JOIN BOOK b ON bl.Isbn = b.Isbn
            JOIN BORROWER br ON bl.Card_id = br.Card_id
            ORDER BY f.Paid ASC, f.Fine_amt DESC
        """)
        columns = [col[0] for col in cursor.description]
        fines = [dict(zip(columns, row)) for row in cursor.fetchall()]

    total_unpaid = sum(f['Fine_amt'] for f in fines if f['status'] == 'Unpaid')

    return render(request, 'fines.html', {
        'fines': fines,
        'total_unpaid': total_unpaid,
        'message': message
    })


@transaction.atomic
def add_borrower_view(request):
    """Add a new borrower to the system"""
    message = ""
    success = False

    if request.method == "POST":
        ssn = request.POST.get('ssn', '').strip()
        bname = request.POST.get('bname', '').strip()
        address = request.POST.get('address', '').strip()
        phone = request.POST.get('phone', '').strip()

        if not all([ssn, bname, address]):
            message = "SSN, Name, and Address are required!"
        elif len(ssn) != 11 or ssn[3] != '-' or ssn[6] != '-':
            message = "SSN must be in format XXX-XX-XXXX"
        else:
            with connection.cursor() as cursor:
                # Check if SSN already exists
                cursor.execute("SELECT Card_id FROM BORROWER WHERE Ssn = %s", [ssn])
                existing = cursor.fetchone()
                
                if existing:
                    message = f"A borrower with SSN {ssn} already exists!"
                else:
                    # Generate next Card_id
                    cursor.execute(
                        "SELECT MAX(CAST(SUBSTR(Card_id, 3) AS INTEGER)) FROM BORROWER"
                    )
                    max_num = cursor.fetchone()[0]
                    next_num = (max_num or 0) + 1
                    card_id = f"ID{next_num:06d}"

                    # Insert new borrower
                    cursor.execute("""
                        INSERT INTO BORROWER (Card_id, Ssn, Bname, Address, Phone)
                        VALUES (%s, %s, %s, %s, %s)
                    """, [card_id, ssn, bname, address, phone or None])

                    message = f"Borrower successfully added!<br>Card ID: {card_id}<br>Name: {bname}"
                    success = True

    return render(request, 'add_borrower.html', {
        'message': message,
        'success': success
    })