from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from functools import wraps
import random
import time
import sqlite3
import datetime
import os

app = Flask(__name__)

# ================= SECRET KEY =================
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

# ================= EMAIL CONFIG =================
app.config['MAIL_SERVER']         = 'smtp.gmail.com'
app.config['MAIL_PORT']           = 587
app.config['MAIL_USE_TLS']        = True
app.config['MAIL_USERNAME']       = 'smurfgaming263@gmail.com'
app.config['MAIL_PASSWORD']       = 'lyspeollzyqombvw'
app.config['MAIL_DEFAULT_SENDER'] = 'smurfgaming263@gmail.com'

mail = Mail(app)

# ================= CONSTANTS =================
DB_PATH            = "fintrackai.db"
OTP_EXPIRY_SECONDS = 300   # 5 minutes
pending_users      = {}    # in-memory OTP store


# ╔══════════════════════════════════════════════════════╗
# ║               DATABASE INITIALISATION               ║
# ╚══════════════════════════════════════════════════════╝

def init_db():
    """Create all tables if they don't already exist."""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.executescript('''
        -- ── USER ──────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS USER (
            USER_ID       INTEGER PRIMARY KEY AUTOINCREMENT,
            USER_NAME     VARCHAR(60)  NOT NULL,
            GENDER        VARCHAR(20),
            EMAIL         VARCHAR(100) NOT NULL UNIQUE,
            PASSWORD_HASH TEXT         NOT NULL,
            CREATED_AT    DATETIME     NOT NULL
        );

        -- ── VERIFICATION ──────────────────────────────────────
        CREATE TABLE IF NOT EXISTS VERIFICATION (
            OTP_ID       INTEGER PRIMARY KEY AUTOINCREMENT,
            USER_ID      INT      NOT NULL,
            EMAIL_OTP    INT      NOT NULL,
            OTP_EXP      DATETIME NOT NULL,
            OTP_CREATION DATETIME NOT NULL,
            OTP_STATUS   VARCHAR(30) CHECK (OTP_STATUS IN ("VERIFIED", "NOT VERIFIED")),
            FOREIGN KEY (USER_ID) REFERENCES USER(USER_ID)
        );

        -- ── INCOME_PROFILES ───────────────────────────────────
        CREATE TABLE IF NOT EXISTS INCOME_PROFILES (
            PROFILE_ID                INTEGER  PRIMARY KEY AUTOINCREMENT,
            USER_ID                   INT      NOT NULL UNIQUE,
            INCOME_TYPE               VARCHAR(40) CHECK(INCOME_TYPE IN
                                          ("SALARIED","PROFESSIONAL","BUSINESS","OTHER")),
            MONTHLY_INCOME            FLOAT    DEFAULT 0,
            ADDITIONAL_INCOME_TYPE    VARCHAR(50) CHECK(ADDITIONAL_INCOME_TYPE IN
                                          ("STOCK","INVESTMENTS","BUSINESS","OTHERS")),
            ADDITIONAL_MONTHLY_INCOME FLOAT    DEFAULT 0,
            DEPENDANTS                INT      DEFAULT 0 CHECK(DEPENDANTS < 20),
            CREATED_AT                DATETIME NOT NULL,
            UPDATED_AT                DATETIME NOT NULL,
            FOREIGN KEY (USER_ID) REFERENCES USER(USER_ID)
        );

        -- ── EXPENSEPROFILE ────────────────────────────────────
        CREATE TABLE IF NOT EXISTS EXPENSEPROFILE (
            EXPENSE_ID    INTEGER  PRIMARY KEY AUTOINCREMENT,
            USER_ID       INT      NOT NULL UNIQUE,
            GROCERIES     FLOAT    DEFAULT 0,
            TRAVEL        FLOAT    DEFAULT 0,
            MEDFIT        FLOAT    DEFAULT 0,
            LEP           FLOAT    DEFAULT 0,
            MONTHLY_RENT  FLOAT    DEFAULT 0,
            M_BILLS       FLOAT    DEFAULT 0,
            FASHION       FLOAT    DEFAULT 0,
            ENTERTAINMENT FLOAT    DEFAULT 0,
            EDUCATION     FLOAT    DEFAULT 0,
            EMSAVING      FLOAT    DEFAULT 0,
            MISCELLANEOUS FLOAT    DEFAULT 0,
            CREATED_AT    DATETIME NOT NULL,
            UPDATED_AT    DATETIME NOT NULL,
            FOREIGN KEY (USER_ID) REFERENCES USER(USER_ID)
        );

        -- ── GOALS ─────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS GOALS (
            GOALID           INTEGER  PRIMARY KEY AUTOINCREMENT,
            USER_ID          INT      NOT NULL,
            GOAL_NAME        VARCHAR(100) NOT NULL,
            START_DATE       DATETIME NOT NULL,
            END_DATE         DATETIME NOT NULL,
            GOAL_AMOUNT      FLOAT    NOT NULL,
            MONTHLY_SAVING_T FLOAT    NOT NULL,
            GOAL_STATUS      VARCHAR(50) DEFAULT "ACTIVE"
                                 CHECK(GOAL_STATUS IN
                                     ("ACTIVE","PAUSED","ACHIEVED","EXPIRED","INACTIVE")),
            CREATED_AT       DATETIME NOT NULL,
            UPDATED_AT       DATETIME NOT NULL,
            FOREIGN KEY (USER_ID) REFERENCES USER(USER_ID)
        );

        -- ── GOAL_HISTORY ──────────────────────────────────────
        CREATE TABLE IF NOT EXISTS GOAL_HISTORY (
            HISTORY_ID INTEGER  PRIMARY KEY AUTOINCREMENT,
            GOALID     INT      NOT NULL,
            CREATED_AT DATETIME NOT NULL,
            SAVE_MONTH FLOAT    NOT NULL,
            FOREIGN KEY (GOALID) REFERENCES GOALS(GOALID)
        );
    ''')
    conn.commit()
    conn.close()


# ╔══════════════════════════════════════════════════════╗
# ║                    DB HELPERS                        ║
# ╚══════════════════════════════════════════════════════╝

def get_db():
    """Return a connection whose rows behave like dicts."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def row_to_dict(row):
    return dict(row) if row else None


# ╔══════════════════════════════════════════════════════╗
# ║               AUTH DECORATOR                         ║
# ╚══════════════════════════════════════════════════════╝

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"success": False, "message": "Unauthorised – please log in."}), 401
        return f(*args, **kwargs)
    return decorated


# ╔══════════════════════════════════════════════════════╗
# ║                  PAGE ROUTES                         ║
# ╚══════════════════════════════════════════════════════╝

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/signup")
def signup_page():
    return render_template("signup.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")

@app.route("/features")
def features():
    return render_template("features.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/about")
def about():
    return render_template("about.html")

# ╔══════════════════════════════════════════════════════╗
# ║              AUTHENTICATION ROUTES                   ║
# ╚══════════════════════════════════════════════════════╝

# ── SEND OTP ──────────────────────────────────────────
@app.route("/send-otp", methods=["POST"])
def send_otp():
    try:
        data             = request.get_json()
        name             = data.get("name", "").strip()
        email            = data.get("email", "").strip().lower()
        gender           = data.get("gender", "").strip()
        password         = data.get("password", "")
        confirm_password = data.get("confirmPassword", "")

        if not all([name, email, gender, password, confirm_password]):
            return jsonify({"success": False, "message": "All fields are required."}), 400

        if password != confirm_password:
            return jsonify({"success": False, "message": "Passwords do not match."}), 400

        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT USER_ID FROM USER WHERE EMAIL = ?", (email,))
        if cur.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "Email already registered."}), 400
        conn.close()

        otp        = str(random.randint(100000, 999999))
        expires_at = time.time() + OTP_EXPIRY_SECONDS

        pending_users[email] = {
            "name": name, "email": email, "gender": gender,
            "password": password, "otp": otp, "expires_at": expires_at
        }

        msg = Message(
            subject    = "FinTrack AI – Email Verification OTP",
            recipients = [email],
            body       = (
                f"Hello {name},\n\n"
                f"Your verification OTP is:\n\n{otp}\n\n"
                f"This OTP expires in 5 minutes.\n\n– FinTrack AI"
            )
        )
        mail.send(msg)

        return jsonify({"success": True, "message": "OTP sent. Check your email."}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── VERIFY OTP & REGISTER ─────────────────────────────
@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    try:
        data  = request.get_json()
        email = data.get("email", "").strip().lower()
        otp   = data.get("otp",   "").strip()

        if not email or not otp:
            return jsonify({"success": False, "message": "Email and OTP are required."}), 400

        if email not in pending_users:
            return jsonify({"success": False, "message": "No pending signup for this email."}), 400

        ud = pending_users[email]

        if time.time() > ud["expires_at"]:
            del pending_users[email]
            return jsonify({"success": False, "message": "OTP expired. Please sign up again."}), 400

        if otp != ud["otp"]:
            return jsonify({"success": False, "message": "Incorrect OTP."}), 400

        hashed = generate_password_hash(ud["password"])
        now    = datetime.datetime.now()

        conn = get_db()
        cur  = conn.cursor()

        # Insert the new user
        cur.execute("""
            INSERT INTO USER (USER_NAME, GENDER, EMAIL, PASSWORD_HASH, CREATED_AT)
            VALUES (?, ?, ?, ?, ?)
        """, (ud["name"], ud["gender"], email, hashed, now))
        user_id = cur.lastrowid

        # Log the verified OTP to VERIFICATION table
        otp_creation = datetime.datetime.fromtimestamp(ud["expires_at"] - OTP_EXPIRY_SECONDS)
        otp_exp      = datetime.datetime.fromtimestamp(ud["expires_at"])
        cur.execute("""
            INSERT INTO VERIFICATION (USER_ID, EMAIL_OTP, OTP_EXP, OTP_CREATION, OTP_STATUS)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, int(ud["otp"]), otp_exp, otp_creation, "VERIFIED"))

        conn.commit()
        conn.close()
        del pending_users[email]

        return jsonify({"success": True, "message": "Account created successfully. Please log in."}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── LOGIN ─────────────────────────────────────────────
@app.route("/api/login", methods=["POST"])
def login():
    try:
        data     = request.get_json()
        email    = data.get("email",    "").strip().lower()
        password = data.get("password", "")

        if not email or not password:
            return jsonify({"success": False, "message": "Email and password are required."}), 400

        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT * FROM USER WHERE EMAIL = ?", (email,))
        user = cur.fetchone()
        conn.close()

        if not user or not check_password_hash(user["PASSWORD_HASH"], password):
            return jsonify({"success": False, "message": "Invalid email or password."}), 401

        session["user_id"]   = user["USER_ID"]
        session["user_name"] = user["USER_NAME"]
        session["email"]     = user["EMAIL"]

        return jsonify({
            "success": True,
            "message": "Login successful.",
            "user": {
                "user_id":   user["USER_ID"],
                "user_name": user["USER_NAME"],
                "email":     user["EMAIL"],
                "gender":    user["GENDER"]
            }
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── LOGOUT ────────────────────────────────────────────
@app.route("/api/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out."}), 200


# ── CURRENT USER ──────────────────────────────────────
@app.route("/api/me", methods=["GET"])
@login_required
def get_me():
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            "SELECT USER_ID, USER_NAME, GENDER, EMAIL, CREATED_AT FROM USER WHERE USER_ID = ?",
            (session["user_id"],)
        )
        user = row_to_dict(cur.fetchone())
        conn.close()
        return jsonify({"success": True, "user": user}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ╔══════════════════════════════════════════════════════╗
# ║             INCOME PROFILE  ROUTES                   ║
# ╚══════════════════════════════════════════════════════╝

@app.route("/api/income-profile", methods=["GET"])
@login_required
def get_income_profile():
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT * FROM INCOME_PROFILES WHERE USER_ID = ?", (session["user_id"],))
        profile = row_to_dict(cur.fetchone())
        conn.close()
        return jsonify({"success": True, "profile": profile}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/income-profile", methods=["POST"])
@login_required
def create_income_profile():
    try:
        data = request.get_json()
        now  = datetime.datetime.now()
        uid  = session["user_id"]

        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT PROFILE_ID FROM INCOME_PROFILES WHERE USER_ID = ?", (uid,))
        if cur.fetchone():
            conn.close()
            return jsonify({"success": False,
                            "message": "Income profile already exists. Use PUT to update."}), 409

        cur.execute("""
            INSERT INTO INCOME_PROFILES
                (USER_ID, INCOME_TYPE, MONTHLY_INCOME, ADDITIONAL_INCOME_TYPE,
                 ADDITIONAL_MONTHLY_INCOME, DEPENDANTS, CREATED_AT, UPDATED_AT)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            uid,
            data.get("income_type"),
            data.get("monthly_income", 0),
            data.get("additional_income_type"),
            data.get("additional_monthly_income", 0),
            data.get("dependants", 0),
            now, now
        ))
        conn.commit()
        pid = cur.lastrowid
        conn.close()
        return jsonify({"success": True, "message": "Income profile created.", "profile_id": pid}), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/income-profile", methods=["PUT"])
@login_required
def update_income_profile():
    try:
        data = request.get_json()
        now  = datetime.datetime.now()
        uid  = session["user_id"]

        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT PROFILE_ID FROM INCOME_PROFILES WHERE USER_ID = ?", (uid,))
        if not cur.fetchone():
            conn.close()
            return jsonify({"success": False,
                            "message": "No income profile found. Use POST to create one."}), 404

        cur.execute("""
            UPDATE INCOME_PROFILES SET
                INCOME_TYPE               = COALESCE(?, INCOME_TYPE),
                MONTHLY_INCOME            = COALESCE(?, MONTHLY_INCOME),
                ADDITIONAL_INCOME_TYPE    = COALESCE(?, ADDITIONAL_INCOME_TYPE),
                ADDITIONAL_MONTHLY_INCOME = COALESCE(?, ADDITIONAL_MONTHLY_INCOME),
                DEPENDANTS                = COALESCE(?, DEPENDANTS),
                UPDATED_AT                = ?
            WHERE USER_ID = ?
        """, (
            data.get("income_type"),
            data.get("monthly_income"),
            data.get("additional_income_type"),
            data.get("additional_monthly_income"),
            data.get("dependants"),
            now, uid
        ))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Income profile updated."}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ╔══════════════════════════════════════════════════════╗
# ║            EXPENSE PROFILE  ROUTES                   ║
# ╚══════════════════════════════════════════════════════╝

# Expense column names (DB) ↔ JSON key mapping
EXPENSE_COLS = [
    ("GROCERIES",     "groceries"),
    ("TRAVEL",        "travel"),
    ("MEDFIT",        "medfit"),
    ("LEP",           "lep"),
    ("MONTHLY_RENT",  "monthly_rent"),
    ("M_BILLS",       "m_bills"),
    ("FASHION",       "fashion"),
    ("ENTERTAINMENT", "entertainment"),
    ("EDUCATION",     "education"),
    ("EMSAVING",      "emsaving"),
    ("MISCELLANEOUS", "miscellaneous"),
]


@app.route("/api/expense-profile", methods=["GET"])
@login_required
def get_expense_profile():
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT * FROM EXPENSEPROFILE WHERE USER_ID = ?", (session["user_id"],))
        profile = row_to_dict(cur.fetchone())
        conn.close()
        return jsonify({"success": True, "profile": profile}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/expense-profile", methods=["POST"])
@login_required
def create_expense_profile():
    try:
        data = request.get_json()
        now  = datetime.datetime.now()
        uid  = session["user_id"]

        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT EXPENSE_ID FROM EXPENSEPROFILE WHERE USER_ID = ?", (uid,))
        if cur.fetchone():
            conn.close()
            return jsonify({"success": False,
                            "message": "Expense profile already exists. Use PUT to update."}), 409

        col_names = ", ".join([c for c, _ in EXPENSE_COLS])
        placeholders = ", ".join(["?" for _ in EXPENSE_COLS])
        values = [data.get(jk, 0) for _, jk in EXPENSE_COLS]

        cur.execute(f"""
            INSERT INTO EXPENSEPROFILE
                (USER_ID, {col_names}, CREATED_AT, UPDATED_AT)
            VALUES (?, {placeholders}, ?, ?)
        """, [uid] + values + [now, now])
        conn.commit()
        eid = cur.lastrowid
        conn.close()
        return jsonify({"success": True, "message": "Expense profile created.", "expense_id": eid}), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/expense-profile", methods=["PUT"])
@login_required
def update_expense_profile():
    try:
        data = request.get_json()
        now  = datetime.datetime.now()
        uid  = session["user_id"]

        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT EXPENSE_ID FROM EXPENSEPROFILE WHERE USER_ID = ?", (uid,))
        if not cur.fetchone():
            conn.close()
            return jsonify({"success": False,
                            "message": "No expense profile found. Use POST to create one."}), 404

        set_clause = ", ".join([f"{col} = COALESCE(?, {col})" for col, _ in EXPENSE_COLS])
        values     = [data.get(jk) for _, jk in EXPENSE_COLS]

        cur.execute(
            f"UPDATE EXPENSEPROFILE SET {set_clause}, UPDATED_AT = ? WHERE USER_ID = ?",
            values + [now, uid]
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Expense profile updated."}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ╔══════════════════════════════════════════════════════╗
# ║                  GOALS  ROUTES                       ║
# ╚══════════════════════════════════════════════════════╝

def _enrich_goal(goal_dict, cur):
    """Attach TOTAL_SAVED and PROGRESS_PCT to a goal dict."""
    cur.execute(
        "SELECT COALESCE(SUM(SAVE_MONTH), 0) AS TS FROM GOAL_HISTORY WHERE GOALID = ?",
        (goal_dict["GOALID"],)
    )
    ts = cur.fetchone()["TS"]
    goal_dict["TOTAL_SAVED"]  = round(ts, 2)
    goal_dict["PROGRESS_PCT"] = (
        round((ts / goal_dict["GOAL_AMOUNT"]) * 100, 2)
        if goal_dict["GOAL_AMOUNT"] else 0
    )
    return goal_dict


# ── GET ALL GOALS ─────────────────────────────────────
@app.route("/api/goals", methods=["GET"])
@login_required
def get_goals():
    try:
        uid    = session["user_id"]
        status = request.args.get("status", "").upper()
        conn   = get_db()
        cur    = conn.cursor()

        if status:
            cur.execute(
                "SELECT * FROM GOALS WHERE USER_ID = ? AND GOAL_STATUS = ? ORDER BY CREATED_AT DESC",
                (uid, status)
            )
        else:
            cur.execute(
                "SELECT * FROM GOALS WHERE USER_ID = ? ORDER BY CREATED_AT DESC",
                (uid,)
            )

        goals = [_enrich_goal(row_to_dict(r), cur) for r in cur.fetchall()]
        conn.close()
        return jsonify({"success": True, "goals": goals, "count": len(goals)}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── CREATE GOAL ───────────────────────────────────────
@app.route("/api/goals", methods=["POST"])
@login_required
def create_goal():
    try:
        data        = request.get_json()
        uid         = session["user_id"]
        now         = datetime.datetime.now()
        goal_name   = data.get("goal_name",   "").strip()
        goal_amount = data.get("goal_amount")
        start_date  = data.get("start_date",  str(now.date()))
        end_date    = data.get("end_date")

        if not goal_name or goal_amount is None or not end_date:
            return jsonify({"success": False,
                            "message": "goal_name, goal_amount and end_date are required."}), 400

        # Auto-calculate monthly saving target
        try:
            s = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            e = datetime.datetime.strptime(end_date,   "%Y-%m-%d")
            months           = max(1, (e.year - s.year) * 12 + (e.month - s.month))
            monthly_saving_t = round(float(goal_amount) / months, 2)
        except Exception:
            monthly_saving_t = data.get("monthly_saving_t", 0)

        conn = get_db()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO GOALS
                (USER_ID, GOAL_NAME, START_DATE, END_DATE, GOAL_AMOUNT,
                 MONTHLY_SAVING_T, GOAL_STATUS, CREATED_AT, UPDATED_AT)
            VALUES (?, ?, ?, ?, ?, ?, "ACTIVE", ?, ?)
        """, (uid, goal_name, start_date, end_date,
              float(goal_amount), monthly_saving_t, now, now))
        conn.commit()
        goal_id = cur.lastrowid
        conn.close()

        return jsonify({
            "success": True, "message": "Goal created.",
            "goal_id": goal_id, "monthly_saving_t": monthly_saving_t
        }), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── GET SINGLE GOAL ───────────────────────────────────
@app.route("/api/goals/<int:goal_id>", methods=["GET"])
@login_required
def get_goal(goal_id):
    try:
        uid  = session["user_id"]
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT * FROM GOALS WHERE GOALID = ? AND USER_ID = ?", (goal_id, uid))
        goal = cur.fetchone()
        if not goal:
            conn.close()
            return jsonify({"success": False, "message": "Goal not found."}), 404

        goal = _enrich_goal(row_to_dict(goal), cur)
        conn.close()
        return jsonify({"success": True, "goal": goal}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── UPDATE GOAL ───────────────────────────────────────
@app.route("/api/goals/<int:goal_id>", methods=["PUT"])
@login_required
def update_goal(goal_id):
    try:
        data = request.get_json()
        uid  = session["user_id"]
        now  = datetime.datetime.now()

        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT GOALID FROM GOALS WHERE GOALID = ? AND USER_ID = ?", (goal_id, uid))
        if not cur.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "Goal not found."}), 404

        cur.execute("""
            UPDATE GOALS SET
                GOAL_NAME        = COALESCE(?, GOAL_NAME),
                END_DATE         = COALESCE(?, END_DATE),
                GOAL_AMOUNT      = COALESCE(?, GOAL_AMOUNT),
                MONTHLY_SAVING_T = COALESCE(?, MONTHLY_SAVING_T),
                GOAL_STATUS      = COALESCE(?, GOAL_STATUS),
                UPDATED_AT       = ?
            WHERE GOALID = ? AND USER_ID = ?
        """, (
            data.get("goal_name"),
            data.get("end_date"),
            data.get("goal_amount"),
            data.get("monthly_saving_t"),
            data.get("goal_status"),
            now, goal_id, uid
        ))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Goal updated."}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── UPDATE GOAL STATUS (PATCH) ────────────────────────
@app.route("/api/goals/<int:goal_id>/status", methods=["PATCH"])
@login_required
def update_goal_status(goal_id):
    try:
        data   = request.get_json()
        status = data.get("goal_status", "").upper()
        VALID  = {"ACTIVE", "PAUSED", "ACHIEVED", "EXPIRED", "INACTIVE"}

        if status not in VALID:
            return jsonify({"success": False,
                            "message": f"Invalid status. Must be one of: {', '.join(VALID)}"}), 400

        uid  = session["user_id"]
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT GOALID FROM GOALS WHERE GOALID = ? AND USER_ID = ?", (goal_id, uid))
        if not cur.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "Goal not found."}), 404

        cur.execute(
            "UPDATE GOALS SET GOAL_STATUS = ?, UPDATED_AT = ? WHERE GOALID = ? AND USER_ID = ?",
            (status, datetime.datetime.now(), goal_id, uid)
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"Goal status set to {status}."}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── DELETE GOAL ───────────────────────────────────────
@app.route("/api/goals/<int:goal_id>", methods=["DELETE"])
@login_required
def delete_goal(goal_id):
    try:
        uid  = session["user_id"]
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT GOALID FROM GOALS WHERE GOALID = ? AND USER_ID = ?", (goal_id, uid))
        if not cur.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "Goal not found."}), 404

        cur.execute("DELETE FROM GOAL_HISTORY WHERE GOALID = ?", (goal_id,))
        cur.execute("DELETE FROM GOALS WHERE GOALID = ? AND USER_ID = ?", (goal_id, uid))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Goal and its history deleted."}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ╔══════════════════════════════════════════════════════╗
# ║              GOAL HISTORY  ROUTES                    ║
# ╚══════════════════════════════════════════════════════╝

# ── GET GOAL HISTORY ──────────────────────────────────
@app.route("/api/goals/<int:goal_id>/history", methods=["GET"])
@login_required
def get_goal_history(goal_id):
    try:
        uid  = session["user_id"]
        conn = get_db()
        cur  = conn.cursor()

        cur.execute(
            "SELECT GOALID, GOAL_AMOUNT, GOAL_STATUS FROM GOALS WHERE GOALID = ? AND USER_ID = ?",
            (goal_id, uid)
        )
        goal = cur.fetchone()
        if not goal:
            conn.close()
            return jsonify({"success": False, "message": "Goal not found."}), 404

        cur.execute(
            "SELECT * FROM GOAL_HISTORY WHERE GOALID = ? ORDER BY CREATED_AT ASC",
            (goal_id,)
        )
        history = [row_to_dict(r) for r in cur.fetchall()]

        cur.execute(
            "SELECT COALESCE(SUM(SAVE_MONTH), 0) AS TS FROM GOAL_HISTORY WHERE GOALID = ?",
            (goal_id,)
        )
        total_saved = round(cur.fetchone()["TS"], 2)
        conn.close()

        return jsonify({
            "success": True,
            "history": history,
            "total_saved":  total_saved,
            "goal_amount":  goal["GOAL_AMOUNT"],
            "progress_pct": round((total_saved / goal["GOAL_AMOUNT"]) * 100, 2) if goal["GOAL_AMOUNT"] else 0
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── ADD MONTHLY SAVING ENTRY ──────────────────────────
@app.route("/api/goals/<int:goal_id>/history", methods=["POST"])
@login_required
def add_goal_history(goal_id):
    try:
        data       = request.get_json()
        save_month = data.get("save_month")
        uid        = session["user_id"]

        if save_month is None or float(save_month) <= 0:
            return jsonify({"success": False, "message": "save_month must be a positive number."}), 400

        conn = get_db()
        cur  = conn.cursor()

        cur.execute(
            "SELECT GOALID, GOAL_AMOUNT, GOAL_STATUS FROM GOALS WHERE GOALID = ? AND USER_ID = ?",
            (goal_id, uid)
        )
        goal = cur.fetchone()
        if not goal:
            conn.close()
            return jsonify({"success": False, "message": "Goal not found."}), 404

        if goal["GOAL_STATUS"] != "ACTIVE":
            conn.close()
            return jsonify({"success": False,
                            "message": f"Goal is {goal['GOAL_STATUS']}. Only ACTIVE goals accept savings."}), 400

        now = datetime.datetime.now()
        cur.execute(
            "INSERT INTO GOAL_HISTORY (GOALID, CREATED_AT, SAVE_MONTH) VALUES (?, ?, ?)",
            (goal_id, now, float(save_month))
        )

        # Check if goal is now achieved
        cur.execute(
            "SELECT COALESCE(SUM(SAVE_MONTH), 0) AS TS FROM GOAL_HISTORY WHERE GOALID = ?",
            (goal_id,)
        )
        total_saved = round(cur.fetchone()["TS"], 2)
        achieved    = total_saved >= goal["GOAL_AMOUNT"]

        if achieved:
            cur.execute(
                "UPDATE GOALS SET GOAL_STATUS = 'ACHIEVED', UPDATED_AT = ? WHERE GOALID = ?",
                (now, goal_id)
            )

        conn.commit()
        history_id = cur.lastrowid
        conn.close()

        return jsonify({
            "success":      True,
            "message":      "Saving recorded." + (" 🎉 Goal achieved!" if achieved else ""),
            "history_id":   history_id,
            "total_saved":  total_saved,
            "goal_achieved": achieved
        }), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── DELETE A HISTORY ENTRY ────────────────────────────
@app.route("/api/goals/<int:goal_id>/history/<int:history_id>", methods=["DELETE"])
@login_required
def delete_goal_history_entry(goal_id, history_id):
    try:
        uid  = session["user_id"]
        conn = get_db()
        cur  = conn.cursor()

        cur.execute("SELECT GOALID FROM GOALS WHERE GOALID = ? AND USER_ID = ?", (goal_id, uid))
        if not cur.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "Goal not found."}), 404

        cur.execute(
            "DELETE FROM GOAL_HISTORY WHERE HISTORY_ID = ? AND GOALID = ?",
            (history_id, goal_id)
        )
        if cur.rowcount == 0:
            conn.close()
            return jsonify({"success": False, "message": "History entry not found."}), 404

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "History entry deleted."}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ╔══════════════════════════════════════════════════════╗
# ║                  DASHBOARD ROUTE                     ║
# ╚══════════════════════════════════════════════════════╝

@app.route("/api/dashboard", methods=["GET"])
@login_required
def get_dashboard():
    try:
        uid  = session["user_id"]
        conn = get_db()
        cur  = conn.cursor()

        # User
        cur.execute(
            "SELECT USER_ID, USER_NAME, GENDER, EMAIL, CREATED_AT FROM USER WHERE USER_ID = ?",
            (uid,)
        )
        user = row_to_dict(cur.fetchone())

        # Income profile
        cur.execute("SELECT * FROM INCOME_PROFILES WHERE USER_ID = ?", (uid,))
        income = row_to_dict(cur.fetchone())

        # Expense profile
        cur.execute("SELECT * FROM EXPENSEPROFILE WHERE USER_ID = ?", (uid,))
        expense = row_to_dict(cur.fetchone())

        # Goals (with progress)
        cur.execute(
            "SELECT * FROM GOALS WHERE USER_ID = ? ORDER BY CREATED_AT DESC",
            (uid,)
        )
        goals = [_enrich_goal(row_to_dict(r), cur) for r in cur.fetchall()]

        # ── Aggregate stats ──
        total_goal_amount = sum(g["GOAL_AMOUNT"] for g in goals)
        total_saved       = sum(g["TOTAL_SAVED"]  for g in goals)
        active_goals      = sum(1 for g in goals if g["GOAL_STATUS"] == "ACTIVE")
        achieved_goals    = sum(1 for g in goals if g["GOAL_STATUS"] == "ACHIEVED")

        # Net disposable income
        net_disposable = 0
        if income and expense:
            total_income  = (income.get("MONTHLY_INCOME") or 0) + \
                            (income.get("ADDITIONAL_MONTHLY_INCOME") or 0)
            total_expense = sum((expense.get(col) or 0) for col, _ in EXPENSE_COLS)
            net_disposable = round(total_income - total_expense, 2)

        conn.close()

        return jsonify({
            "success": True,
            "dashboard": {
                "user":            user,
                "income_profile":  income,
                "expense_profile": expense,
                "goals":           goals,
                "stats": {
                    "total_goal_amount": total_goal_amount,
                    "total_saved":       round(total_saved, 2),
                    "active_goals":      active_goals,
                    "achieved_goals":    achieved_goals,
                    "net_disposable":    net_disposable
                }
            }
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ╔══════════════════════════════════════════════════════╗
# ║             VERIFICATION HISTORY ROUTE               ║
# ╚══════════════════════════════════════════════════════╝

@app.route("/api/verification-history", methods=["GET"])
@login_required
def get_verification_history():
    try:
        uid  = session["user_id"]
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            "SELECT * FROM VERIFICATION WHERE USER_ID = ? ORDER BY OTP_CREATION DESC",
            (uid,)
        )
        records = [row_to_dict(r) for r in cur.fetchall()]
        conn.close()
        return jsonify({"success": True, "records": records}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ╔══════════════════════════════════════════════════════╗
# ║                       MAIN                           ║
# ╚══════════════════════════════════════════════════════╝

if __name__ == "__main__":
    init_db()                  # Creates all tables on first run
    app.run(debug=True)