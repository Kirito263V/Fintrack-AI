from flask import Flask, render_template, request, jsonify ,session
from werkzeug.security import generate_password_hash ,check_password_hash
import random
import time
import sqlite3
import datetime
import smtplib



app = Flask(__name__)
app.secret_key = "fintrack_secret_key"

pending_users = {}
registered_users = {}
conn = sqlite3.connect("fintrackai.db")
cur = conn.cursor()
cur.execute("select * from user")
x = cur.fetchall()
reg = []
for i in x:
    reg.append(i[3].lower())

OTP_EXPIRY_SECONDS = 300  # 5 minutes


def generate_otp():
    return str(random.randint(1000, 9999))


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/signup")
def signup_page():
    return render_template("signup.html")

@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

from flask import session, jsonify



@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    user_email = data.get("email", "").strip()
    user_password = data.get("password", "").strip()

    conn = sqlite3.connect("fintrackai.db")
    cur = conn.cursor()

    cur.execute("SELECT EMAIL, PASSWORD_HASH FROM USER")
    x = dict(cur.fetchall())

    conn.close()

    if user_email in x:
        if check_password_hash(x[user_email], user_password):
           session["user_email"] = user_email
           return jsonify({
        "success": True,
        "email": user_email
        })
        else:
            return jsonify({"success": False, "message": "Invalid password"})
    else:
        return jsonify({"success": False, "message": "Invalid email"})


@app.route("/api/me")
def api_me():
    if "user_email" in session:
        return jsonify({
            "success": True,
            "email": session["user_email"]
        })
    else:
        return jsonify({
            "success": False
        })
        
@app.route("/income")
def income_page():
    return render_template("income.html")        
        
@app.route("/api/income", methods=["POST"])
def income():

    if "user_email" not in session:
        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401

    data = request.get_json()

    income_type = data.get("income_type")
    monthly_income = data.get("monthly_income")
    additional_income_type = data.get("additional_income_type")
    additional_monthly_income = data.get("additional_monthly_income")
    dependants = data.get("dependants")

    conn = sqlite3.connect("fintrackai.db")
    cur = conn.cursor()

    # get user id from session email
    cur.execute(
        "SELECT USER_ID FROM USER WHERE EMAIL=?",
        (session["user_email"],)
    )

    row = cur.fetchone()

    if not row:
        return jsonify({
            "success": False,
            "message": "User not found"
        })

    user_id = row[0]

    now = datetime.datetime.now()

    cur.execute("SELECT MAX(PROFILE_ID) FROM INCOME_PROFILES")
    result = cur.fetchone()

    profile_id = 1 if result[0] is None else result[0] + 1

    cur.execute("""
        INSERT INTO INCOME_PROFILES (
            PROFILE_ID,
            USER_ID,
            INCOME_TYPE,
            MONTHLY_INCOME,
            ADDITIONAL_INCOME_TYPE,
            ADDITIONAL_MONTHLY_INCOME,
            DEPENDANTS,
            CREATED_AT,
            UPDATED_AT
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        profile_id,
        user_id,
        income_type,
        float(monthly_income),
        additional_income_type,
        float(additional_monthly_income),
        int(dependants),
        now,
        now
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Income profile saved successfully"
    })

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
            return jsonify({"success": False, "message": "All fields are required."}), 400

        if gender not in ["Male", "Female"]:
            return jsonify({"success": False, "message": "Invalid gender selected."}), 400

        if password != confirm_password:
            return jsonify({"success": False, "message": "Passwords do not match."}), 400

        if len(password) < 6:
            return jsonify({"success": False, "message": "Password must be at least 6 characters."}), 400
        print(email,reg)
        if email in reg:
            return jsonify({"success": False, "message": "User already registered with this email."}), 400

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

        print("\n" + "=" * 60)
        print(f"CORRECT OTP for {email}: {otp}")
        print("=" * 60 + "\n")
        sender_email = "smurfgaming263@gmail.com"
        app_password = "lyspeollzyqombvw"
        
        subject = "OTP Verification"
        body = f"Your OTP is: {otp}"
        message = f"Subject: {subject}\nTo: {email}\nFrom: {sender_email}\n\n{body}"
        
        subject = "OTP Verification"
        body = f"Your OTP is: {otp}"
        message = f"Subject: {subject}\nTo: {email}\nFrom: {sender_email}\n\n{body}"

        server = smtplib.SMTP("smtp.gmail.com",587)
        server.starttls()
        server.login(sender_email,app_password)
        server.sendmail(sender_email,email,message)
        server.quit()
        
        return jsonify({
            "success": True,
            "message": "OTP generated successfully. Please enter OTP."
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    try:
        data = request.get_json()

        email = data.get("email", "").strip().lower()
        otp = data.get("otp", "").strip()

        if not email or not otp:
            return jsonify({"success": False, "message": "Email and OTP are required."}), 400

        if email not in pending_users:
            return jsonify({"success": False, "message": "No pending signup found for this email."}), 400

        user_data = pending_users[email]

        if time.time() > user_data["expires_at"]:
            del pending_users[email]
            return jsonify({"success": False, "message": "OTP expired. Please sign up again."}), 400

        if otp != user_data["otp"]:
            return jsonify({"success": False, "message": "Incorrect OTP. User not registered."}), 400

        hashed_password = generate_password_hash(user_data["password"])

        registered_users[email] = {
            "name": user_data["name"],
            "email": user_data["email"],
            "gender": user_data["gender"],
            "password": hashed_password,
            "registered_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        print(registered_users)
        conn = sqlite3.connect("fintrackai.db")
        cur = conn.cursor()
        cur.execute("select max(user_id) from user")
        x1 = cur.fetchall()
        cur.execute(f'''
            INSERT INTO USER VALUES({x1[0][0]+1},"{registered_users[email]['name']}",
            "{registered_users[email]['gender']}","{registered_users[email]['email']}",
            "{registered_users[email]['password']}","{datetime.datetime.now()}")
            ''')
        conn.commit()

        print(pending_users)
        cur.execute("select max(otp_id) from VERIFICATION")
        x2 = cur.fetchall()
        cur.execute(f'''
            INSERT INTO VERIFICATION VALUES({x2[0][0]+1},{x1[0][0]+1},
            {pending_users[email]['otp']},"{pending_users[email]['expires_at']}",
            "{datetime.datetime.now()}","VERIFIED")
            ''')
        conn.commit()        
                    
        
        

        del pending_users[email]
        
        return jsonify({
            "success": True,
            "message": "User registered successfully."
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@app.route("/api/dashboard")
def api_dashboard():

    if "user_email" not in session:
        return jsonify({
            "success": False
        })

    user_email = session["user_email"]
    user_name = user_email.split("@")[0]

    return jsonify({
        "success": True,
        "dashboard": {
            "user": {   # ← THIS WAS MISSING OR WRONG LEVEL
                "USER_NAME": user_name,
                "EMAIL": user_email
            },
            "income_profile": None,
            "expense_profile": None,
            "goals": [],
            "stats": {
                "active_goals": 0,
                "achieved_goals": 0
            }
        }
    })

@app.route("/users", methods=["GET"])
def users():
    return jsonify({
        "success": True,
        "registered_users": registered_users
    }), 200


if __name__ == "__main__":
    app.run(debug=True)