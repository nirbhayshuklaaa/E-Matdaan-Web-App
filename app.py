from flask import Flask, render_template, request, redirect, flash, jsonify, session
import mysql.connector
from werkzeug.security import generate_password_hash
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

# GET SELECTED STATE DATABASE
def get_state_db(state_code):

    main_db = get_main_db()
    cursor = main_db.cursor(dictionary=True)

    cursor.execute(
        "SELECT db_name FROM states WHERE state_code=%s",
        (state_code,)
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

@app.route("/admin_login")
def admin_login():
    return render_template("admin_login.html")

# REGISTER USER IN SELECTED STATE DB
@app.route("/register", methods=["POST"])
def register():

    try:
        name = request.form.get("name")
        father_name=request.form.get("father_name")
        constituency=request.form.get("constituency")
        phone = request.form.get("phone")
        password = request.form.get("password")
        epic_no = request.form.get("epic_no")
        adhar_no = request.form.get("adhar_no")
        state_code = request.form.get("state")

        # Connect selected state DB
        db = get_state_db(state_code)

        if not db:
            flash("❌ Invalid State Selected")
            return redirect("/register_page")

        cursor = db.cursor()

        # Check voter exists in voter table
        cursor.execute(
            "SELECT epic_no FROM Eci_voters WHERE epic_no=%s",
            (epic_no,)
        )

        if not cursor.fetchone():
            flash("❌ EPIC not found in voter database")
            return redirect("/register_page")

        # Hash Password
        hashed_pass = generate_password_hash(password)

        # Insert into users table
        cursor.execute("""
            INSERT INTO voters
            (name, father_name,constituency, phone, password, epic_no, adhar_no)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (name, father_name, constituency, phone, hashed_pass, epic_no, adhar_no))

        db.commit()

        cursor.close()
        db.close()

        flash("✅ Registration Successful")
        return redirect("/login_page")

    except mysql.connector.Error as err:

        if err.errno == errorcode.ER_DUP_ENTRY:
            flash("❌ Already Registered with this EPIC / Phone")
        else:
            print(err)
            flash("❌ Database Error")

        return redirect("/register_page")

    except Exception as e:
        print(e)
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