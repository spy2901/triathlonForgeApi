from flask import Blueprint, request, redirect,jsonify
from app.utils.database import get_db_connection
import os, time, requests

strava_bp = Blueprint('strava', __name__, url_prefix='/api/strava')

# Strava part of api
STRAVA_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REDIRECT_URI = "https://4ede-178-148-58-77.ngrok-free.app"
STRAVA_CALLBACK_PATH = "/api/strava/callback"  # Append this dynamically


@strava_bp.route('/auth', methods=['GET'])
def strava_auth():
    """
    Redirects the user to Strava's authorization page.
    """
    # URL encode the redirect URI to ensure special characters are handled properly
    redirect_uri = f"{STRAVA_REDIRECT_URI}{STRAVA_CALLBACK_PATH}"
    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={STRAVA_ID}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"  # No path appended
        f"&scope=read,activity:read_all"
    )
    return redirect(auth_url)


@strava_bp.route('/callback', methods=['GET'])
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
        "client_id": STRAVA_ID,
        "client_secret": STRAVA_SECRET,
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

@strava_bp.route('/', methods=['GET'])
def base_redirect():
    """
    Handle Strava callback when redirected to base URL without a path.
    """
    code = request.args.get('code')
    if not code:
        return jsonify({"success": False, "message": "Authorization code is missing."}), 400

    # Handle the callback logic here, e.g., exchange code for tokens
    return strava_callback()  # Call your existing callback logic

@strava_bp.route('/activities', methods=['GET'])
def get_strava_activities():
    """
    Fetches the user's activities from Strava.
    """
    user_id = request.args.get('id')  # Replace this with the authenticated user's ID

    # Retrieve the user's tokens from the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT strava_access_token, strava_refresh_token, strava_token_expires_at FROM users WHERE user_id = %s", (user_id,))
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
                "client_id": STRAVA_ID,
                "client_secret": STRAVA_SECRET,
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
                "UPDATE users SET strava_access_token = %s, strava_refresh_token = %s, strava_token_expires_at = %s WHERE user_id = %s",
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

