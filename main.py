import time

import requests
from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import Error
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
# email verification code
import random
import smtplib  # Or any email-sending library like `flask-mail`
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
# from dotenv import load_dotenv

# load_dotenv()

app = Flask(__name__)
# Create an Argon2 PasswordHasher instance
ph = PasswordHasher()

# Database connection function
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host='127.0.0.1',  # Replace with your MySQL host
            user='root',  # Replace with your MySQL username
            password='root',  # Replace with your MySQL password
            database='TriathlonForge',# Replace with your database name
            port="8889"
        )
        return conn
    except Error as e:
        print(f"Error: {e}")
        return None


@app.route('/api/data', methods=['POST'])
def receive_data():
    # Get data from the request's JSON body
    data = request.get_json()

    # Extract the input data sent from Flutter
    input_data = data.get('input')

    print(input_data)

    # Process the data as needed
    return jsonify({'message': f'Received input: {input_data}'})

#  login register functions

@app.route('/api/login', methods=['POST'])
def login():
    # Get the data from the request
    data = request.get_json()

    # Extract the username
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email or password is missing.'}), 400

    # Connect to the database
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection failed.'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        # Query to check if the username exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            # Compare the hashed password from the database with the one provided
            try:
                # The hashed password stored in the database
                stored_password_hash = user['password_hash']  # Adjust according to your column name
                ph.verify(stored_password_hash, password)

                # If password matches
                return jsonify({'success': True, 'message': 'Login successful!'})

            except Exception as e:
                # If password doesn't match
                return jsonify({'success': False, 'message': 'Invalid username or password.'}), 401
        else:
            return jsonify({'success': False, 'message': 'Invalid username.'}), 401

    except Error as e:
        return jsonify({'success': False, 'message': f'Database query failed: {e}'}), 500

    finally:
        cursor.close()
        conn.close()


@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()

    # Extract fields
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    password = data.get('password')
    bio = data.get('bio')
    birth_year = data.get('birth_year')
    strava_profile = data.get('strava_profile')
    garmin_profile = data.get('garmin_profile')

    if not all([first_name, last_name, email, password, birth_year]):
        return jsonify({'success': False, 'message': 'Missing required fields.'}), 400

    # Hash password
    hashed_password = ph.hash(password)

    # Generate a 6-digit verification code
    verification_code = f"{random.randint(100000, 999999)}"

    # Connect to the database
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection failed.'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        # Check if email already exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Email already registered.'}), 400

        # Insert the user with a verification code
        cursor.execute("""
            INSERT INTO users (first_name, last_name, email, password_hash, bio, birth_year, strava_profile, garmin_profile, verification_code)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (first_name, last_name, email, hashed_password, bio, birth_year, strava_profile, garmin_profile,
              verification_code))
        conn.commit()

        # Send the verification email (simple example)
        send_email(email, verification_code)

        return jsonify({'success': True, 'message': 'Registration successful. Please verify your email.'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {e}'}), 500

    finally:
        cursor.close()
        conn.close()


def send_email(to_email, verification_code):
    """Send verification code via email (example with smtplib)."""
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = os.getenv("SMTP_PORT")
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

    subject = "Verify Your Registration"
    # Define the HTML body with the verification code
    body = f"""
    <html>
    <head>
      <title>Verify Your Registration</title>
      <style>
        body {{
          font-family: 'Arial', sans-serif;
          margin: 0;
          padding: 0;
          background-color: #e9ecef;
          text-align: center;
        }}
        .container {{
          width: 100%;
          max-width: 600px;
          margin: 20px auto;
          padding: 0;
          background-color: #ffffff;
          border-radius: 8px;
          box-shadow: 0 0 15px rgba(0, 0, 0, 0.1);
          overflow: hidden;
        }}
        .header {{
          background-color: #007bff;
          color: #ffffff;
          padding: 15px;
          border-top-left-radius: 8px;
          border-top-right-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          background-size: cover;
          background-repeat: no-repeat;
        }}
        .header img {{
          width: 50px;
          margin-right: 15px;
        }}
        .header h2 {{
          margin: 0;
          font-size: 24px;
          letter-spacing: 1px;
        }}
        .content {{
          padding: 20px;
          text-align: left;
          background-size: cover;
          background-repeat: no-repeat;
        }}
        h2 {{
          color: #333333;
          margin-top: 0;
        }}
        p {{
          color: #666666;
          line-height: 1.6;
        }}
        .code {{
          font-size: 24px;
          font-weight: bold;
          color: #ffffff;
          background-color: #dc3545;
          padding: 10px;
          border-radius: 4px;
          display: inline-block;
        }}
        .footer {{
          margin-top: 20px;
          padding: 10px;
          background-color: #007bff;
          border-bottom-left-radius: 8px;
          border-bottom-right-radius: 8px;
          font-size: 12px;
          color: #ffffff;
          text-align: center;
        }}
        .footer p {{
          margin: 0;
        }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <img src="https://media.istockphoto.com/id/961624146/vector/triathlon-event-illustration.jpg?s=612x612&w=0&k=20&c=7uf1-wrSTDphrwxqvrskwNrhDTY56TDTeeeOGqA5BIc=" alt="Sport Logo">
          <h2>Verify Your Registration</h2>
        </div>
        <div class="content">
          <p>Dear User,</p>
          <p>Your verification code is: <span class="code">{verification_code}</span></p>
          <p>Please enter this code to complete your registration.</p>
          <p>Best regards,<br>Triathlon Forge</p>
        </div>
        <div class="footer">
          <p>If you did not request this code, please ignore this email.</p>
        </div>
      </div>
    </body>
    </html>
    """

    # Create a multipart message
    message = MIMEMultipart()
    message['From'] = SMTP_USER
    message['To'] = to_email
    message['Subject'] = subject

    # Attach the HTML body to the email
    message.attach(MIMEText(body, 'html'))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, message.as_string())


@app.route('/api/verify', methods=['POST'])
def verify_code():
    data = request.get_json()

    email = data.get('email')
    verification_code = data.get('verification_code')

    if not email or not verification_code:
        return jsonify({'success': False, 'message': 'Missing email or verification code.'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection failed.'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        # Check the verification code
        cursor.execute("SELECT * FROM users WHERE email = %s AND verification_code = %s", (email, verification_code))
        user = cursor.fetchone()

        if not user:
            return jsonify({'success': False, 'message': 'Invalid verification code.'}), 400

        # Mark the user as verified
        cursor.execute("UPDATE users SET verified = TRUE, verification_code = NULL WHERE email = %s", (email,))
        conn.commit()

        return jsonify({'success': True, 'message': 'Email verified successfully.'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {e}'}), 500

    finally:
        cursor.close()
        conn.close()

# Strava part of api

STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_REDIRECT_URI = os.getenv("STRAVA_REDIRECT_URI")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")

@app.route('/api/strava/auth', methods=['GET'])
def strava_auth():
    """
    Redirects the user to Strava's authorization page.
    """



    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={STRAVA_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={STRAVA_REDIRECT_URI}"
        f"&scope=read,activity:read_all"
    )
    return jsonify({"auth_url": auth_url})

@app.route('/api/strava/callback', methods=['GET'])
def strava_callback():
    """
    Handles Strava's callback and exchanges the authorization code for an access token.
    """
    code = request.args.get('code')
    if not code:
        return jsonify({"success": False, "message": "Authorization code is missing."}), 400

    # Exchange the authorization code for an access token
    token_url = "https://www.strava.com/oauth/token"
    payload = {
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code"
    }

    response = requests.post(token_url, data=payload)
    if response.status_code != 200:
        return jsonify({"success": False, "message": "Failed to retrieve access token."}), 500

    tokens = response.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_at = tokens.get("expires_at")

    # Store tokens in the database
    user_id = 1  # Replace this with the authenticated user's ID
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "UPDATE users SET strava_access_token = %s, strava_refresh_token = %s, strava_token_expires_at = %s WHERE id = %s",
            (access_token, refresh_token, expires_at, user_id)
        )
        conn.commit()
    except Exception as e:
        return jsonify({"success": False, "message": f"Database error: {e}"}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify({"success": True, "message": "Strava connected successfully."})

@app.route('/api/strava/activities', methods=['GET'])
def get_strava_activities():
    """
    Fetches the user's activities from Strava.
    """
    user_id = 1  # Replace this with the authenticated user's ID

    # Retrieve the user's tokens from the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT strava_access_token, strava_refresh_token, strava_token_expires_at FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"success": False, "message": "User not found."}), 404

        access_token = user["strava_access_token"]
        refresh_token = user["strava_refresh_token"]
        expires_at = user["strava_token_expires_at"]

        # Refresh the access token if it has expired
        if time.time() > expires_at:
            refresh_url = "https://www.strava.com/oauth/token"
            payload = {
                "client_id": STRAVA_CLIENT_ID,
                "client_secret": STRAVA_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }
            response = requests.post(refresh_url, data=payload)
            if response.status_code != 200:
                return jsonify({"success": False, "message": "Failed to refresh access token."}), 500

            tokens = response.json()
            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")
            expires_at = tokens.get("expires_at")

            # Update tokens in the database
            cursor.execute(
                "UPDATE users SET strava_access_token = %s, strava_refresh_token = %s, strava_token_expires_at = %s WHERE id = %s",
                (access_token, refresh_token, expires_at, user_id)
            )
            conn.commit()

        # Fetch activities from Strava
        activities_url = "https://www.strava.com/api/v3/athlete/activities"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(activities_url, headers=headers)

        if response.status_code != 200:
            return jsonify({"success": False, "message": "Failed to fetch activities."}), 500

        activities = response.json()
        return jsonify({"success": True, "activities": activities})

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5001)
