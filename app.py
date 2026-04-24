from flask import Flask, render_template, request, redirect, flash, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import os
import mysql.connector
from mysql.connector import errorcode
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "secret123")


# ==========================================
# CENTRAL DATABASE CONNECTION (RAILWAY FIXED)
# ==========================================
import os
import mysql.connector
from urllib.parse import urlparse

def get_main_db():
    try:
        url = os.getenv("DATABASE_URL")

        if not url:
            raise Exception("DATABASE_URL not found")

        u = urlparse(url)

        conn = mysql.connector.connect(
            host=u.hostname,
            user=u.username,
            password=u.password,
            database=u.path[1:],   # removes /
            port=u.port
        )

        print("Database Connected Successfully")
        return conn

    except Exception as e:
        print("DB ERROR:", e)
        raise

# ==========================================
# STATE DATABASE CONNECTION
# ==========================================
def get_state_db(state_name):
    try:
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

        db_name = row["db_name"]

        db_url = os.getenv("DATABASE_URL")

        if db_url:
            data = urlparse(db_url)

            return mysql.connector.connect(
                host=data.hostname,
                user=data.username,
                password=data.password,
                database=db_name,
                port=data.port
            )

        return mysql.connector.connect(
            host=os.getenv("MYSQLHOST", "localhost"),
            user=os.getenv("MYSQLUSER", "root"),
            password=os.getenv("MYSQLPASSWORD", ""),
            database=db_name,
            port=int(os.getenv("MYSQLPORT", 3306))
        )

    except Exception as e:
        print("STATE DB ERROR:", e)
        return None


# ==========================================
# NOTICES
# ==========================================
def get_notices():
    try:
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

    except:
        return []


# ==========================================
# HOME
# ==========================================
@app.route("/")
@app.route("/home")
def home():
    notices = get_notices()
    return render_template("index.html", notices=notices)


# ==========================================
# PAGES
# ==========================================
@app.route("/register_page")
def register_page():
    return render_template("register.html")


@app.route("/login_page")
def login_page():
    return render_template("login.html")


@app.route("/admin_login")
def admin_login():
    return render_template("admin_login.html")


# ==========================================
# REGISTER
# ==========================================
@app.route("/register", methods=["POST"])
def register():
    try:
        name = request.form.get("name")
        state_name = request.form.get("state_name")
        constituency = request.form.get("constituency")
        phone = request.form.get("phone")
        epic_no = request.form.get("epic_no")
        password = request.form.get("password")

        if not all([name, state_name, constituency, phone, epic_no, password]):
            flash("❌ All fields are required")
            return redirect("/register_page")

        db = get_main_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT epic_no FROM eci_voters WHERE epic_no=%s",
            (epic_no,)
        )

        if cursor.fetchone() is None:
            flash("❌ EPIC not found")
            cursor.close()
            db.close()
            return redirect("/register_page")

        hashed_pass = generate_password_hash(password)

        cursor.execute("""
            INSERT INTO users
            (name, state_name, constituency, phone, password, epic_no)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (name, state_name, constituency, phone, hashed_pass, epic_no))

        db.commit()

        cursor.close()
        db.close()

        flash("✅ Registration Successful")
        return redirect("/login_page")

    except mysql.connector.Error as err:
        print(err)

        if err.errno == errorcode.ER_DUP_ENTRY:
            flash("❌ Already Registered")
        else:
            flash("Database Error")

        return redirect("/register_page")

    except Exception as e:
        print("REGISTER ERROR:", e)
        flash("❌ Something Went Wrong")
        return redirect("/register_page")


# ==========================================
# LOGIN
# ==========================================
@app.route("/login", methods=["POST"])
def login():
    try:
        epic_no = request.form.get("epic_no")
        state_name = request.form.get("state_name")
        password = request.form.get("password")

        if not epic_no or not state_name or not password:
            flash("❌ All fields required")
            return redirect("/login_page")

        db = get_state_db(state_name)

        if not db:
            flash("❌ Invalid State")
            return redirect("/login_page")

        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT name,password_hash,constituency
            FROM reg_voters
            WHERE epic_no=%s
            LIMIT 1
        """, (epic_no,))

        user = cursor.fetchone()

        if not user:
            flash("❌ EPIC Not Found")
            return redirect("/login_page")

        if check_password_hash(user["password_hash"], password):

            session.clear()
            session["logged_in"] = True
            session["name"] = user["name"]
            session["epic_no"] = epic_no
            session["state_name"] = state_name
            session["constituency"] = user["constituency"]

            flash("✅ Login Successful")
            return redirect("/user_dashboard")

        flash("❌ Wrong Password")
        return redirect("/login_page")

    except Exception as e:
        print("LOGIN ERROR:", e)
        flash("❌ Something Went Wrong")
        return redirect("/login_page")


# ==========================================
# USER DASHBOARD
# ==========================================
@app.route("/user_dashboard")
def user_dashboard():

    if "logged_in" not in session:
        flash("❌ Login First")
        return redirect("/login_page")

    try:
        db = get_state_db(session["state_name"])
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT id,name,party_name,symbol,constituency
            FROM candidates
            WHERE constituency=%s
            AND status='active'
            ORDER BY name
        """, (session["constituency"],))

        candidates = cursor.fetchall()

        return render_template(
            "user_dashboard.html",
            name=session["name"],
            epic_no=session["epic_no"],
            state_name=session["state_name"],
            constituency=session["constituency"],
            candidates=candidates
        )

    except Exception as e:
        print("DASHBOARD ERROR:", e)
        flash("❌ Unable to load dashboard")
        return redirect("/login_page")


# ==========================================
# LOGOUT
# ==========================================
@app.route("/logout")
def logout():
    session.clear()
    flash("✅ Logged Out")
    return redirect("/home")


# ==========================================
# RUN
# ==========================================
if __name__ == "__main__":
    app.run(debug=True)