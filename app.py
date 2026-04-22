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

@app.route("/login", methods=["POST"])
def login():

    try:
        epic_no = request.form.get("epic_no")
        state_name = request.form.get("state_name")
        password = request.form.get("password")

        db = get_state_db(state_name)

        if not db:
            flash("❌ Inctive State Selected")
            return redirect("/login_page")

        cursor = db.cursor(dictionary=True)

        # fetch full user
        cursor.execute(
            "SELECT password_hash FROM reg_voters WHERE epic_no=%s",
            (epic_no,)
        )

        result = cursor.fetchone()

        if not result:
            flash("❌ EPIC not found in voter database")
            return redirect("/login_page")

        stored_hash = result["password_hash"]


        if check_password_hash(stored_hash, password):
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

@app.route("/user_dashboard",methods=['GET','POST'])
def user_dashboard():
    try:
        return render_template("user_dashboard.html")
        epic_no=request.form.get("name")
        
    


    except Exception as e :
        print("Something went wrong !")
        return redirect("/login")

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