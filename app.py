from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import random
import time
import sqlite3
import datetime
import smtplib

app = Flask(__name__)
app.secret_key = "fintrack_secret_key"

def get_db_connection():

    conn = sqlite3.connect("fintrackai.db")
    conn.row_factory = sqlite3.Row

    return conn


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "user_email" not in session:
            return redirect("/login")

        return f(*args, **kwargs)

    return decorated_function

pending_users = {}
registered_users = {}

OTP_EXPIRY_SECONDS = 300


def generate_otp():
    return str(random.randint(1000, 9999))


# ================= HOME =================

@app.route("/")
def home():
    return render_template("index.html")


# ================= SIGNUP PAGE =================

@app.route("/signup")
def signup_page():
    return render_template("signup.html")


# ================= LOGIN PAGE =================

@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")


# ================= DASHBOARD PAGE =================

@app.route("/dashboard")
def dashboard():

    if "user_email" not in session:
        return redirect("/login")

    return render_template("dashboard.html")


# ================= LOGIN =================

@app.route("/login", methods=["POST"])
def login():

    data = request.get_json()

    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    conn = sqlite3.connect("fintrackai.db")
    cur = conn.cursor()

    cur.execute("SELECT EMAIL, PASSWORD_HASH FROM USER")

    users = dict(cur.fetchall())

    conn.close()

    if email in users:

        if check_password_hash(users[email], password):

            session["user_email"] = email

            return jsonify({
                "success": True,
                "email": email
            })

        else:

            return jsonify({
                "success": False,
                "message": "Invalid password"
            })

    else:

        return jsonify({
            "success": False,
            "message": "Invalid email"
        })

# ================= SIGN OUT =================
@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


# ================= SESSION CHECK =================

@app.route("/api/me")
def api_me():

    if "user_email" in session:

        return jsonify({
            "success": True,
            "email": session["user_email"]
        })

    return jsonify({
        "success": False
    })



# ================= SEND OTP =================

@app.route("/send-otp", methods=["POST"])
def send_otp():

    try:

        data = request.get_json()

        name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        gender = data.get("gender", "").strip()
        password = data.get("password", "")
        confirm_password = data.get("confirmPassword", "")

        if not name or not email or not gender or not password or not confirm_password:

            return jsonify({
                "success": False,
                "message": "All fields required"
            })


        if password != confirm_password:

            return jsonify({
                "success": False,
                "message": "Passwords do not match"
            })


        conn = sqlite3.connect("fintrackai.db")
        cur = conn.cursor()

        cur.execute("SELECT EMAIL FROM USER WHERE EMAIL=?", (email,))
        existing = cur.fetchone()

        conn.close()

        if existing:

            return jsonify({
                "success": False,
                "message": "User already exists"
            })


        otp = generate_otp()

        expires_at = time.time() + OTP_EXPIRY_SECONDS


        pending_users[email] = {

            "name": name,
            "email": email,
            "gender": gender,
            "password": password,
            "otp": otp,
            "expires_at": expires_at

        }


        print("=" * 50)
        print("OTP:", otp)
        print("=" * 50)


        sender_email = "smurfgaming263@gmail.com"
        app_password = "lyspeollzyqombvw"


        subject = "OTP Verification"
        body = f"Your OTP is: {otp}"

        message = f"Subject:{subject}\n\n{body}"


        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, email, message)
        server.quit()


        return jsonify({
            "success": True,
            "message": "OTP sent successfully"
        })


    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        })


# ================= VERIFY OTP =================
@app.route("/verify-otp", methods=["POST"])
def verify_otp():

    try:

        data = request.get_json()

        email = data.get("email", "").strip().lower()
        otp = data.get("otp", "").strip()

        if email not in pending_users:

            return jsonify({
                "success": False,
                "message": "Signup session expired"
            })


        stored_data = pending_users[email]


        if time.time() > stored_data["expires_at"]:

            del pending_users[email]

            return jsonify({
                "success": False,
                "message": "OTP expired"
            })


        if otp != stored_data["otp"]:

            return jsonify({
                "success": False,
                "message": "Incorrect OTP"
            })


        hashed_password = generate_password_hash(
            stored_data["password"]
        )


        conn = sqlite3.connect("fintrackai.db")
        cur = conn.cursor()


        # ================= INSERT INTO USER =================

        cur.execute("SELECT MAX(USER_ID) FROM USER")

        last_user_id = cur.fetchone()[0]

        user_id = 1 if last_user_id is None else last_user_id + 1


        cur.execute("""

            INSERT INTO USER

            VALUES (?, ?, ?, ?, ?, ?)

        """, (

            user_id,
            stored_data["name"],
            stored_data["gender"],
            stored_data["email"],
            hashed_password,
            datetime.datetime.now()

        ))


        # ================= INSERT INTO VERIFICATION =================

        cur.execute("SELECT MAX(OTP_ID) FROM VERIFICATION")

        last_otp_id = cur.fetchone()[0]

        otp_id = 1 if last_otp_id is None else last_otp_id + 1


        cur.execute("""

            INSERT INTO VERIFICATION

            VALUES (?, ?, ?, ?, ?, ?)

        """, (

            otp_id,
            user_id,
            stored_data["otp"],
            stored_data["expires_at"],
            datetime.datetime.now(),
            "VERIFIED"

        ))


        conn.commit()
        conn.close()


        del pending_users[email]


        return jsonify({
            "success": True,
            "message": "Signup completed successfully"
        })


    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        })

# ================= INCOME PAGE =================

@app.route("/income")
def income_page():

    if "user_email" not in session:
        return redirect("/login")

    return render_template("income.html")


# ================= SAVE INCOME =================

@app.route("/api/income", methods=["POST"])
def income():

    if "user_email" not in session:
        return jsonify({"success": False})

    data = request.get_json()

    conn = sqlite3.connect("fintrackai.db")
    cur = conn.cursor()

    cur.execute("SELECT USER_ID FROM USER WHERE EMAIL=?", (session["user_email"],))

    user_id = cur.fetchone()[0]

    cur.execute("SELECT MAX(PROFILE_ID) FROM INCOME_PROFILES")

    last = cur.fetchone()[0]

    profile_id = 1 if last is None else last + 1


    now = datetime.datetime.now()


    cur.execute("""

        INSERT INTO INCOME_PROFILES

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

    """, (

        profile_id,
        user_id,
        data["income_type"],
        float(data["monthly_income"]),
        data["additional_income_type"],
        float(data["additional_monthly_income"]),
        int(data["dependants"]),
        now,
        now

    ))

    conn.commit()
    conn.close()


    return jsonify({
        "success": True,
        "redirect": "/expense"
    })


# ================= EXPENSE =================
@app.route("/expense", methods=["GET", "POST"])
def expense():

    if "user_email" not in session:
        return redirect("/login")

    if request.method == "GET":
        return render_template("expense.html")

    data = request.get_json()

    email = session["user_email"]

    conn = sqlite3.connect("fintrackai.db")
    cur = conn.cursor()

    cur.execute(
        "SELECT USER_ID FROM USER WHERE LOWER(EMAIL)=LOWER(?)",
        (email,)
    )

    row = cur.fetchone()

    if not row:
        return jsonify({"success": False, "message": "User not found"})

    user_id = row[0]


    cur.execute("SELECT MAX(EXPENSE_ID) FROM EXPENSEPROFILE")
    last = cur.fetchone()[0]

    expense_id = 1 if last is None else last + 1


    cur.execute("""
        INSERT INTO EXPENSEPROFILE
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (

        expense_id,
        user_id,
        float(data.get("groceries", 0)),
        float(data.get("travel", 0)),
        float(data.get("medfit", 0)),
        float(data.get("lep", 0)),
        float(data.get("monthly_rent", 0)),
        float(data.get("m_bills", 0)),
        float(data.get("fashion", 0)),
        float(data.get("entertainment", 0)),
        float(data.get("education", 0)),
        float(data.get("emsaving", 0)),
        float(data.get("miscellaneous", 0)),
        datetime.datetime.now()
    ))

    conn.commit()
    conn.close()

    return jsonify({"success": True})



# ================= DASHBOARD DATA =================

@app.route("/api/dashboard")
def api_dashboard():

    if "user_email" not in session:
        return jsonify({"success": False}), 401

    email = session["user_email"]

    conn = sqlite3.connect("fintrackai.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()


    # ================= USER =================

    cur.execute("""
        SELECT USER_NAME, EMAIL
        FROM USER
        WHERE LOWER(EMAIL)=LOWER(?)
    """, (email,))

    user = cur.fetchone()


    # ================= USER ID =================

    cur.execute("""
        SELECT USER_ID
        FROM USER
        WHERE LOWER(EMAIL)=LOWER(?)
    """, (email,))

    uid = cur.fetchone()[0]


    # ================= INCOME PROFILE =================

    cur.execute("""
        SELECT *
        FROM INCOME_PROFILES
        WHERE USER_ID=?
        ORDER BY PROFILE_ID DESC
        LIMIT 1
    """, (uid,))

    income = cur.fetchone()


    # ================= EXPENSE PROFILE =================

    cur.execute("""
        SELECT *
        FROM EXPENSEPROFILE
        WHERE USER_ID=?
        ORDER BY EXPENSE_ID DESC
        LIMIT 1
    """, (uid,))

    expense = cur.fetchone()


    # ================= GOALS SNAPSHOT =================

    cur.execute("""
        SELECT
            GOALID,
            GOAL_NAME,
            GOAL_AMOUNT,
            MONTHLY_SAVING_T,
            GOAL_STATUS
        FROM GOALS
        WHERE USER_ID=?
        ORDER BY CREATED_AT DESC
        LIMIT 3
    """, (uid,))

    goals = cur.fetchall()


    conn.close()


    return jsonify({

        "success": True,

        "dashboard": {

            "user": dict(user) if user else None,

            "income_profile":
                dict(income) if income else None,

            "expense_profile":
                dict(expense) if expense else None,

            "goals":
                [dict(g) for g in goals]

        }

    })


# ================= GOALS =================

@app.route("/goals")
@login_required
def goals_page():
    return render_template("goals.html")


@app.route("/api/goals/create", methods=["POST"])
@login_required
def create_goal():

    data = request.get_json()

    goal_name = data.get("goal_name")
    goal_amount = data.get("goal_amount")
    monthly_saving = data.get("monthly_saving_t")
    start_date = data.get("start_date")
    end_date = data.get("end_date")

    conn = get_db_connection()

    # get USER_ID from email session
    user = conn.execute(
        "SELECT USER_ID FROM USER WHERE EMAIL=?",
        (session["user_email"],)
    ).fetchone()

    user_id = user["USER_ID"]

    # generate next GOALID manually
    last_goal = conn.execute(
        "SELECT MAX(GOALID) FROM GOALS"
    ).fetchone()[0]

    goal_id = 1 if last_goal is None else last_goal + 1

    conn.execute("""
        INSERT INTO GOALS
        (
            GOALID,
            USER_ID,
            GOAL_NAME,
            START_DATE,
            END_DATE,
            GOAL_AMOUNT,
            MONTHLY_SAVING_T,
            GOAL_STATUS,
            CREATED_AT
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', CURRENT_TIMESTAMP)
    """,
    (
        goal_id,
        user_id,
        goal_name,
        start_date,
        end_date,
        goal_amount,
        monthly_saving
    ))

    conn.commit()
    conn.close()

    return jsonify({"success": True})


@app.route("/api/goals/list")
@login_required
def list_goals():

    conn = get_db_connection()

    # Get USER_ID
    user = conn.execute(
        "SELECT USER_ID FROM USER WHERE EMAIL=?",
        (session["user_email"],)
    ).fetchone()

    user_id = user["USER_ID"]

    goals = conn.execute("""
        SELECT g.*,
        IFNULL(SUM(h.SAVE_MONTH),0) AS TOTAL_SAVED

        FROM GOALS g

        LEFT JOIN GOAL_HISTORY h
        ON g.GOALID = h.GOALID

        WHERE g.USER_ID = ?

        GROUP BY g.GOALID

        ORDER BY g.CREATED_AT DESC
    """, (user_id,)).fetchall()

    conn.close()

    return jsonify({
        "goals": [dict(row) for row in goals]
    })
    
    
@app.route("/api/goals/save-progress", methods=["POST"])
@login_required
def save_goal_progress():

    data = request.get_json()

    goal_id = data.get("goal_id")
    save_month = data.get("save_month")

    if not goal_id or not save_month:
        return jsonify({
            "success": False,
            "message": "Missing goal_id or save_month"
        })

    conn = get_db_connection()

    # Generate HISTORY_ID manually
    last_history = conn.execute(
        "SELECT MAX(HISTORY_ID) FROM GOAL_HISTORY"
    ).fetchone()[0]

    history_id = 1 if last_history is None else last_history + 1

    # Insert progress
    conn.execute("""
        INSERT INTO GOAL_HISTORY
        (HISTORY_ID, GOALID, SAVE_MONTH, CREATED_AT)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        history_id,
        goal_id,
        save_month
    ))

    # Calculate total saved
    total_saved = conn.execute("""
        SELECT IFNULL(SUM(SAVE_MONTH),0)
        FROM GOAL_HISTORY
        WHERE GOALID = ?
    """, (goal_id,)).fetchone()[0]

    # Get goal amount
    goal = conn.execute("""
        SELECT GOAL_AMOUNT
        FROM GOALS
        WHERE GOALID = ?
    """, (goal_id,)).fetchone()

    goal_amount = goal["GOAL_AMOUNT"]

    goal_achieved = False

    if total_saved >= goal_amount:

        conn.execute("""
            UPDATE GOALS
            SET GOAL_STATUS='ACHIEVED'
            WHERE GOALID=?
        """, (goal_id,))

        goal_achieved = True

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "goal_achieved": goal_achieved
    }) 
    
@app.route("/api/goals/delete", methods=["POST"])
@login_required
def delete_goal():

    data = request.get_json()

    goal_id = data.get("goal_id")

    conn = get_db_connection()

    # Get USER_ID
    user = conn.execute(
        "SELECT USER_ID FROM USER WHERE EMAIL=?",
        (session["user_email"],)
    ).fetchone()

    user_id = user["USER_ID"]

    # Delete history first
    conn.execute(
        "DELETE FROM GOAL_HISTORY WHERE GOALID=?",
        (goal_id,)
    )

    # Delete goal securely
    conn.execute(
        "DELETE FROM GOALS WHERE GOALID=? AND USER_ID=?",
        (goal_id, user_id)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True
    })   
    
# ================= RUN SERVER =================

if __name__ == "__main__":
    app.run(debug=True)