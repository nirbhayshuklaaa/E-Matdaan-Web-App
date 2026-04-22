from flask import Flask, render_template, request, redirect, flash, jsonify, session
import mysql.connector
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from mysql.connector import errorcode

app = Flask(__name__)
app.secret_key = "secret123"

# Access The Central db
def get_main_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Nir@1234",
        database="central_eci_db"
    )

def get_notices():
    conn = get_main_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT notice 
        FROM notice
        WHERE is_active = 1 
        ORDER BY n_id DESC
    """)

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return data

# HOME PAGE
@app.route("/")
@app.route("/home")
def home():
    notices = get_notices()
    return render_template("index.html", notices=notices)

# PAGES

@app.route("/register_page")
def register_page():
    return render_template("register.html")

@app.route("/login_page")
def login_page():
    return render_template("login.html")

@app.route("/login", methods=["POST","GET"])
def login():
    try:
        epic_no = request.form.get("epic_no")
        state_name = request.form.get("state_name")
        password = request.form.get("password")

        # Basic validation
        if not epic_no or not state_name or not password:
            flash("❌ All fields are required")
            return redirect("/login_page")

        # Get state database
        db = get_state_db(state_name)

        if not db:
            flash("❌ Inactive State Selected")
            return redirect("/login_page")

        cursor = db.cursor(dictionary=True)

        # Fetch voter details
        cursor.execute(
            """
            SELECT name, password_hash, constituency
            FROM reg_voters
            WHERE epic_no = %s
            LIMIT 1
            """,
            (epic_no,)
        )

        result = cursor.fetchone()

        # User not found
        if not result:
            flash("❌ EPIC not found in voter database")
            return redirect("/login_page")

        # Extract values after checking result
        name = result["name"]
        stored_hash = result["password_hash"]
        constituency = result["constituency"]

        # Password verification
        if check_password_hash(stored_hash, password):

            # Session create
            session.clear()
            session["name"] = name
            session["epic_no"] = epic_no
            session["state_name"] = state_name
            session["constituency"] = constituency
            session["logged_in"] = True

            flash("✅ Login Successful!")
            return redirect("/user_dashboard")

        else:
            flash("❌ Wrong Password")
            return redirect("/login_page")

    except Exception as e:
        print("LOGIN ERROR:", e)
        flash("❌ Something Went Wrong")
        return redirect("/login_page")

@app.route("/admin_login")
def admin_login():
    return render_template("admin_login.html")


@app.route("/cast_vote", methods=["POST"])
def cast_vote():
    try:
        state_name = request.form.get("state_name")
        epic_no = request.form.get("epic_no")
        party_name = request.form.get("party_name")
        constituency = request.form.get("constituency")

        db = get_state_db(state_name)

        if not db:
            flash("Database Failed To Load!")
            return redirect("/user_dashboard")

        cursor = db.cursor()

        # Correct SQL Query
        cursor.execute(
            "INSERT INTO votes (epic_no, party_name, constituency) VALUES (%s, %s, %s)",
            (epic_no, party_name, constituency)
        )

        db.commit()   # Important

        cursor.close()
        db.close()

        flash("✅ Vote Cast Successfully!")
        return redirect("/user_dashboard")

    except mysql.connector.Error as err:
        print("MYSQL ERROR:", err)

        if err.errno == errorcode.ER_DUP_ENTRY:
            flash("❌ Already Voted")
        else:
            flash("Database Error!")

        return redirect("/user_dashboard")

    except Exception as e:
        print("Something went wrong!", e)
        flash("Something Went Wrong!")
        return redirect("/login")


# USER DASHBOARD
@app.route("/user_dashboard")
def user_dashboard():

    # Login check
    if "logged_in" not in session:
        flash("❌ Please login first")
        return redirect("/login_page")

    try:
        state_name = session["state_name"]
        constituency = session["constituency"]

        db = get_state_db(state_name)
        cursor = db.cursor(dictionary=True)

        # Fetch only candidates of logged in user's constituency
        cursor.execute("""
            SELECT 
                id,
                name,
                party_name,
                symbol,
                constituency
            FROM candidates
            WHERE constituency = %s
            AND status='active'
            ORDER BY name ASC
        """, (constituency,))

        candidates = cursor.fetchall()

        return render_template(
            "user_dashboard.html",
            name=session["name"],
            epic_no=session["epic_no"],
            state_name=state_name,
            constituency=constituency,
            candidates=candidates
        )

    except Exception as e:
        print("DASHBOARD ERROR:", e)
        flash("❌ Unable to load dashboard")
        return redirect("/login_page")

# Logout Route
@app.route("/logout")
def logout():
    session.clear()
    flash("✅ Logged Out Successfully")
    return redirect("/home")

# GET SELECTED STATE DATABASE
def get_state_db(state_name):

    main_db = get_main_db()
    cursor = main_db.cursor(dictionary=True)

    cursor.execute(
        "SELECT db_name FROM states WHERE LOWER(state_name)=%s",
        (state_name.strip().lower(),)
    )

    row = cursor.fetchone()

    cursor.close()
    main_db.close()

    if not row:
        return None

    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Nir@1234",
        database=row["db_name"]
    )


# REGISTER ROUTE
@app.route("/register", methods=["POST"])
def register():

    try:
        name = request.form.get("name")
        state_name = request.form.get("state_name")
        constituency = request.form.get("constituency")
        phone = request.form.get("phone")
        epic_no = request.form.get("epic_no")
        password = request.form.get("password")

        # CONNECT STATE DB
        db = get_state_db(state_name)

        if not db:
            flash("❌ Invalid State Selected")
            return redirect("/register_page")

        cursor = db.cursor()

        # CHECK EPIC EXISTS
        cursor.execute(
                "SELECT epic_no FROM Eci_voters WHERE epic_no=%s",
                (epic_no,)
                )

        result = cursor.fetchone()

        if result is None:
            cursor.close()
            db.close()
            flash("❌ EPIC not found in voter database")
            return redirect("/register_page")

        # HASH PASSWORD
        hashed_pass = generate_password_hash(password)

        # INSERT USER
        cursor.execute("""
            INSERT INTO reg_voters
            (name, constituency, phone, password_hash, epic_no)
            VALUES (%s,%s,%s,%s,%s)
        """, (name, constituency, phone, hashed_pass, epic_no))

        db.commit()

        cursor.close()
        db.close()

        flash("✅ Registration Successful")
        return redirect("/login")

    except mysql.connector.Error as err:

        print("MYSQL ERROR:", err)

        if err.errno == errorcode.ER_DUP_ENTRY:
            flash("❌ Already Registered")
        else:
            flash("Database Error !")

        return redirect("/register_page")

    except Exception as e:
        print("GENERAL ERROR:", e)
        flash("❌ Something Went Wrong")
        return redirect("/register_page")

@app.route("/get_election/<state_code>")
def get_election(state_code):

    try:
        db = get_main_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT title, state_name, election_type,
                   constituency, seat_no, status
            FROM elections
            WHERE state_code=%s
            AND status IN ('active','upcoming')
            ORDER BY id DESC
            LIMIT 1
        """, (state_code,))

        row = cursor.fetchone()

        cursor.close()
        db.close()

        if row:
            return jsonify({
                "title": row["title"],
                "state": row["state_name"],
                "type": row["election_type"],
                "assembly": row["constituency"],
                "seat": row["seat_no"],
                "status": row["status"]
            })

        return jsonify({
            "title": "No Election Found",
            "state": "",
            "type": "",
            "assembly": "",
            "seat": "",
            "status": "No active election"
        })

    except Exception as e:
        print(e)
        return jsonify({
            "title": "Error",
            "state": "",
            "type": "",
            "assembly": "",
            "seat": "",
            "status": "Unable to load data"
        })
    
@app.route("/admin_login_d", methods=["POST"])
def admin_login_d():

    username = request.form.get("username").strip()
    password = request.form.get("password").strip()
    adhar_no = request.form.get("adhar_no").strip()

    db = get_main_db()
    cursor = db.cursor()

    query = """
    SELECT * FROM admins
    WHERE username=%s AND password=%s AND adhar_no=%s
    """

    cursor.execute(query, (username, password, adhar_no))

    admin = cursor.fetchone()

    cursor.close()
    db.close()

    if admin:

        session["admin_login"] = True
        session["admin_user"] = username

        return render_template("admin_dashboard.html")

    else:
        flash("Invalid Details")
        return redirect("/admin_login")


if __name__ == "__main__":
    app.run(debug=True)