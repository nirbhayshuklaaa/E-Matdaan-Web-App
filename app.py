from flask import Flask, render_template, request, redirect, flash, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import os
import mysql.connector
from mysql.connector import errorcode
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "secret123")


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




# GET ACTIVE NOTICES
def get_notices():
    try:
        conn = get_main_db()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT 
                message
            FROM notices
            ORDER BY id DESC
        """

        cursor.execute(query)

        notice = cursor.fetchall()

        return notice if notice else []

    except mysql.connector.Error as err:
        print("MYSQL NOTICE ERROR:", err)
        return []

    except Exception as e:
        print("GENERAL NOTICE ERROR:", e)
        return []

    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except:
            pass



# HOME PAGE ROUTE
@app.route("/")
@app.route("/home")
def home():
    notice = get_notices()
    return render_template("index.html", notice=notice)


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



# REGISTER

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
            INSERT INTO reg_voters
            (name, state_name, constituency, phone, password, epic_no)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (name, state_name, constituency, phone, hashed_pass, epic_no))

        db.commit()

        cursor.close()
        db.close()

        flash("✅ Registration Successful")
        return redirect("/login_page")

    except mysql.connector.Error as err:

        if err.errno == errorcode.ER_DUP_ENTRY:
            flash("❌ Already Registered")
        else:
            flash("Database Error")

        return redirect("/register_page")

    except Exception as e:
        print("REGISTER ERROR:", e)
        flash("❌ Something Went Wrong")
        return redirect("/register_page")



# LOGIN

@app.route("/login", methods=["POST"])
def login():
    try:
        epic_no = request.form.get("epic_no")
        state_name = request.form.get("state_name")
        password = request.form.get("password")

        if not epic_no or not state_name or not password:
            flash("❌ All fields required")
            return redirect("/login_page")

        db = get_main_db()

        if not db:
            flash("❌ Database Error !")
            return redirect("/login_page")

        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT name,password,constituency
            FROM reg_voters
            WHERE epic_no=%s
            LIMIT 1
        """, (epic_no,))

        user = cursor.fetchone()

        if not user:
            flash("❌ Not Registeres or Invalid Epic_no")
            return redirect("/login_page")

        if check_password_hash(user["password"], password):

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



# USER DASHBOARD

@app.route("/user_dashboard")
def user_dashboard():

    if "logged_in" not in session:
        flash("❌ Login First")
        return redirect("/login_page")

    try:
        db = get_main_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT id,candidate_name,party_name,symbol,constituency,state_name
            FROM candidates
            WHERE constituency=%s
            AND status='active'
            ORDER BY candidate_name
        """, (session["constituency"],))

        candidates = cursor.fetchall()
        if not candidates:
            flash("No candidates available for your constituency")
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



# LOGOUT

@app.route("/logout")
def logout():
    session.clear()
    flash("✅ Logged Out")
    return redirect("/home")


# ADMIN LOGIN

@app.route("/admin", methods=["GET", "POST"])
def admin():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        adhar_no = request.form.get("adhar_no")

        if not all([username, password, adhar_no]):
            flash("❌ All fields are required")
            return redirect("/admin_login")

        conn = None
        cursor = None

        try:
            conn = get_main_db()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT username, password, adhar_no
                FROM admins
                WHERE username = %s
            """, (username,))

            admin = cursor.fetchone()

            if not admin:
                flash("❌ Admin not found")
                return redirect("/admin_login")

            # Password check
            if admin["password"] != password:
                flash("❌ Wrong password")
                return redirect("/admin_login")

            # Aadhaar check
            if admin["adhar_no"] != adhar_no:
                flash("❌ Aadhaar mismatch")
                return redirect("/admin_login")

            # ✅ Login success
            session.clear()
            session["admin_logged_in"] = True
            session["admin_user"] = username

            flash("✅ Admin Login Successful")
            return redirect("/admin_dashboard")

        except Exception as e:
            print("ADMIN LOGIN ERROR:", e)
            flash("❌ Something went wrong")
            return redirect("/admin_login")

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template("admin_login.html")


# Admin Dashboard

@app.route("/admin_dashboard")
def admin_dashboard():

    db = get_main_db()
    cursor = db.cursor(dictionary=True)

    # Total voters
    cursor.execute(
        "SELECT COUNT(*) total FROM reg_voters"
    )
    voters = cursor.fetchone()["total"]

    # Active elections
    cursor.execute(
        """
        SELECT COUNT(*) total
        FROM elections
        WHERE status='active'
        """
    )
    active_elections = cursor.fetchone()["total"]

    # Inactive states
    cursor.execute(
        """
        SELECT COUNT(*) total
        FROM states
        WHERE status='inactive'
        """
    )
    inactive_states = cursor.fetchone()["total"]

    cursor.close()
    db.close()

    return render_template(
        "admin_dashboard.html",
        voters=voters,
        active_elections=active_elections,
        inactive_states=inactive_states
    )

# RUN

if __name__ == "__main__":
    app.run(debug=True)