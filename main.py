# Standard libraries
import os
import random
import smtplib
import urllib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Third-party libraries
from flask import Flask, request, jsonify, redirect
from flasgger import Swagger
import mysql.connector
from mysql.connector import Error
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import requests

app = Flask(__name__)
swagger = Swagger(app, template={
    "info": {
        "title": "My Flask API",
        "description": "An example API using Flask and Swagger",
        "version": "1.0.0"
    }
})
# Create an Argon2 PasswordHasher instance
ph = PasswordHasher()


# Database connection function
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host='127.0.0.1',  # Replace with your MySQL host
            user='root',  # Replace with your MySQL username
            password='root',  # Replace with your MySQL password
            database='TriathlonForge',  # Replace with your database name
            port=8889
        )
        return conn
    except Error as e:
        print(f"Database connection Error: {e}")
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
    """
        User Login
        ---
        tags:
          - Authentication
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - email
                - password
              properties:
                email:
                  type: string
                  example: user@example.com
                password:
                  type: string
                  example: MySecurePassword
        responses:
          200:
            description: Successful login
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                message:
                  type: string
                  example: "Login successful!"
          401:
            description: Invalid credentials
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: false
                message:
                  type: string
                  example: "Invalid username or password."
        """
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
    """
        User Registration
        ---
        tags:
          - Authentication
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - first_name
                - last_name
                - email
                - password
                - birth_year
              properties:
                first_name:
                  type: string
                  example: John
                last_name:
                  type: string
                  example: Doe
                email:
                  type: string
                  format: email
                  example: john.doe@example.com
                password:
                  type: string
                  format: password
                  example: MySecurePassword123
                bio:
                  type: string
                  example: "A passionate triathlete and runner."
                birth_year:
                  type: integer
                  example: 1985
                strava_profile:
                  type: string
                  example: https://www.strava.com/athletes/12345
                garmin_profile:
                  type: string
                  example: https://connect.garmin.com/profile/johndoe
        responses:
          200:
            description: Successful registration
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                message:
                  type: string
                  example: "Registration successful. Please verify your email."
          400:
            description: Bad Request
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: false
                message:
                  type: string
                  example: "Missing required fields."
          500:
            description: Internal Server Error
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: false
                message:
                  type: string
                  example: "Database connection failed."
        """

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
        print("Database connection failed. Please check configuration.")
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
    """
    Send Verification Email

    Sends an email containing a verification code to the specified email address
    using SMTP with a styled HTML template.

    Parameters:
    ----------
    to_email : str
        The recipient's email address.
    verification_code : str
        The verification code to include in the email.

    Environment Variables:
    ----------------------
    - SMTP_SERVER : str
        The address of the SMTP server.
    - SMTP_PORT : int
        The port number of the SMTP server.
    - SMTP_USER : str
        The username for the SMTP server authentication.
    - SMTP_PASSWORD : str
        The password for the SMTP server authentication.

    Email Content:
    --------------
    - Subject: "Verify Your Registration"
    - HTML Body: Includes a verification code, styled with inline CSS.

    Returns:
    --------
    None

    Raises:
    -------
    smtplib.SMTPException:
        If an error occurs during email sending.
    EnvironmentError:
        If required environment variables are not set.

    Example:
    --------
    >>> send_email("user@example.com", "123456")

    Notes:
    ------
    - Ensure that the SMTP environment variables are configured properly.
    - This function currently uses `smtplib` for email sending and does not support
      asynchronous operations.
    """
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
    """
    Verify Email Verification Code
    ---
    tags:
          - Authentication

    description: |
        Verifies the user's email address by checking the provided verification code
        against the one stored in the database. If the code matches, the user's account is
        marked as verified.

    parameters:
      - name: email
        in: body
        required: true
        description: The email address of the user requesting verification.
        schema:
          type: string
      - name: verification_code
        in: body
        required: true
        description: The verification code sent to the user's email.
        schema:
          type: string

    responses:
      200:
        description: Email successfully verified.
      400:
        description: Invalid or missing verification code.
      500:
        description: Database connection or server error.

    """
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

STRAVA_CLIENT_ID = 117855 #os.getenv("STRAVA_CLIENT_ID")
STRAVA_REDIRECT_URI = "https://4ede-178-148-58-77.ngrok-free.app"

STRAVA_CALLBACK_PATH = "/api/strava/callback"  # Append this dynamically
STRAVA_CLIENT_SECRET = "b94ac73033399f6ac146a91f1a755a2678909271" #os.getenv("STRAVA_CLIENT_SECRET")


@app.route('/api/strava/auth', methods=['GET'])
def strava_auth():
    """
    Redirects the user to Strava's authorization page.
    """
    # URL encode the redirect URI to ensure special characters are handled properly
    redirect_uri = f"{STRAVA_REDIRECT_URI}{STRAVA_CALLBACK_PATH}"
    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={STRAVA_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"  # No path appended
        f"&scope=read,activity:read_all"
    )
    return redirect(auth_url)


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
            "UPDATE users SET strava_access_token = %s, strava_refresh_token = %s, strava_token_expires_at = %s WHERE user_id = %s",
            (access_token, refresh_token, expires_at, user_id)
        )
        conn.commit()
    except Exception as e:
        return jsonify({"success": False, "message": f"Database error: {e}"}), 500
    finally:
        cursor.close()
        conn.close()

        # Redirect with a custom scheme
        return jsonify({
            "success": True,
            "message": "Strava connected successfully.",
            "redirect_url": f"callback://home?code={code}"
        })

@app.route('/', methods=['GET'])
def base_redirect():
    """
    Handle Strava callback when redirected to base URL without a path.
    """
    code = request.args.get('code')
    if not code:
        return jsonify({"success": False, "message": "Authorization code is missing."}), 400

    # Handle the callback logic here, e.g., exchange code for tokens
    return strava_callback()  # Call your existing callback logic

# @app.route('/api/strava/activities', methods=['GET'])
# def get_strava_activities():
#     """
#     Fetches the user's activities from Strava.
#     """
#     user_id = 1  # Replace this with the authenticated user's ID
#
#     # Retrieve the user's tokens from the database
#     conn = get_db_connection()
#     cursor = conn.cursor(dictionary=True)
#     try:
#         cursor.execute("SELECT strava_access_token, strava_refresh_token, strava_token_expires_at FROM users WHERE id = %s", (user_id,))
#         user = cursor.fetchone()
#         if not user:
#             return jsonify({"success": False, "message": "User not found."}), 404
#
#         access_token = user["strava_access_token"]
#         refresh_token = user["strava_refresh_token"]
#         expires_at = user["strava_token_expires_at"]
#
#         # Refresh the access token if it has expired
#         if time.time() > expires_at:
#             refresh_url = "https://www.strava.com/oauth/token"
#             payload = {
#                 "client_id": STRAVA_CLIENT_ID,
#                 "client_secret": STRAVA_CLIENT_SECRET,
#                 "refresh_token": refresh_token,
#                 "grant_type": "refresh_token"
#             }
#             response = requests.post(refresh_url, data=payload)
#             if response.status_code != 200:
#                 return jsonify({"success": False, "message": "Failed to refresh access token."}), 500
#
#             tokens = response.json()
#             access_token = tokens.get("access_token")
#             refresh_token = tokens.get("refresh_token")
#             expires_at = tokens.get("expires_at")
#
#             # Update tokens in the database
#             cursor.execute(
#                 "UPDATE users SET strava_access_token = %s, strava_refresh_token = %s, strava_token_expires_at = %s WHERE id = %s",
#                 (access_token, refresh_token, expires_at, user_id)
#             )
#             conn.commit()
#
#         # Fetch activities from Strava
#         activities_url = "https://www.strava.com/api/v3/athlete/activities"
#         headers = {"Authorization": f"Bearer {access_token}"}
#         response = requests.get(activities_url, headers=headers)
#
#         if response.status_code != 200:
#             return jsonify({"success": False, "message": "Failed to fetch activities."}), 500
#
#         activities = response.json()
#         return jsonify({"success": True, "activities": activities})
#
#     except Exception as e:
#         return jsonify({"success": False, "message": f"Error: {e}"}), 500
#     finally:
#         cursor.close()
#         conn.close()


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5001)
