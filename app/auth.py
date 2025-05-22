from flask import Blueprint, request, jsonify
from argon2 import PasswordHasher
from app.utils.database import get_db_connection
from app.utils.email import send_email

auth_bp = Blueprint('auth', __name__, url_prefix='/api')
# Create an Argon2 PasswordHasher instance
ph = PasswordHasher()
#  login register functions
@auth_bp.route('/login', methods=['POST'])
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


@auth_bp.route('/api/register', methods=['POST'])
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



@auth_bp.route('/api/verify', methods=['POST'])
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
