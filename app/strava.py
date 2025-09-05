import os
import requests
import time

from flask import Blueprint, request, redirect, jsonify

from app.utils.database import get_db_connection

strava_bp = Blueprint('strava', __name__, url_prefix='/api/strava')

# Strava part of api
STRAVA_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REDIRECT_URI = os.getenv("STRAVA_REDIRECT_URI")#"https://22064563c47f.ngrok-free.app"
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
        return redirect(f"callback://home?code={code}")


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
    Fetches all the user's activities from Strava using pagination
    and stores them in the database (including location).
    """
    user_id = request.args.get("id")
    if not user_id:
        return jsonify({"success": False, "message": "Missing user id"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    try:
        # 1. Dohvati Strava tokene
        cursor.execute("""
            SELECT strava_access_token, strava_refresh_token, strava_token_expires_at
            FROM users WHERE user_id = %s
        """, (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        access_token = user["strava_access_token"]
        refresh_token = user["strava_refresh_token"]
        expires_at = user["strava_token_expires_at"]

        # 2. Refresh token ako je istekao
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
                return jsonify({
                    "success": False,
                    "message": "Failed to fetch activities",
                    "status_code": response.status_code,
                    "error": response.text
                }), 500

            tokens = response.json()
            access_token = tokens["access_token"]
            refresh_token = tokens["refresh_token"]
            expires_at = tokens["expires_at"]

            cursor.execute("""
                UPDATE users 
                SET strava_access_token = %s, strava_refresh_token = %s, strava_token_expires_at = %s 
                WHERE user_id = %s
            """, (access_token, refresh_token, expires_at, user_id))
            conn.commit()

        # 3. Povuci sve aktivnosti sa Strave (paginacija)
        all_activities = []
        page = 1
        per_page = 200

        while True:
            url = f"https://www.strava.com/api/v3/athlete/activities?per_page={per_page}&page={page}"
            resp = requests.get(url, headers={"Authorization": f"Bearer {access_token}"})
            if resp.status_code != 200:
                return jsonify({
                    "success": False,
                    "message": "Failed to fetch activities",
                    "status_code": resp.status_code,
                    "error": resp.text
                }), 500

            activities = resp.json()
            if not activities:
                break

            all_activities.extend(activities)
            page += 1

        # 4. Ubaci u bazu
        for act in all_activities:
            strava_id = act.get("id")
            activity_type = act.get("type", "Other")
            activity_name = act.get("name")
            distance = act.get("distance", 0.0)
            duration = act.get("moving_time", 0)
            pace = None
            speed = act.get("average_speed", None)
            calories = act.get("calories", None)
            hr_avg = act.get("average_heartrate", None)
            hr_max = act.get("max_heartrate", None)
            elevation = act.get("total_elevation_gain", 0.0)
            date = act.get("start_date_local", "").split("T")[0]

            # ⚠️ Povuci detalje da bi dobio lokaciju
            detail_url = f"https://www.strava.com/api/v3/activities/{strava_id}"
            detail_resp = requests.get(detail_url, headers={"Authorization": f"Bearer {access_token}"})
            location_city, location_country = None, None
            gear_name, device_name, polyline = None, None, None
            if detail_resp.status_code == 200:
                details = detail_resp.json()
                location_city = details.get("location_city")
                location_country = details.get("location_country")
                gear_name = details.get("gear", {}).get("name") if details.get("gear") else None
                device_name = details.get("device_name")
                polyline = details.get("map", {}).get("summary_polyline")
                calories = details.get("calories", None)

            # Ubaci u activities
            cursor.execute("""
                INSERT INTO activities 
                    (user_id, stravaActivityID, activity_type,activity_name ,distance, duration, pace, speed, calories_burned, 
                     heart_rate_avg, heart_rate_max, elevation_gain, date, location_city, location_country)
                VALUES (%s, %s, %s, %s ,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    distance = VALUES(distance),
                    duration = VALUES(duration),
                    pace = VALUES(pace),
                    speed = VALUES(speed),
                    calories_burned = VALUES(calories_burned),
                    heart_rate_avg = VALUES(heart_rate_avg),
                    heart_rate_max = VALUES(heart_rate_max),
                    elevation_gain = VALUES(elevation_gain),
                    date = VALUES(date),
                    location_city = VALUES(location_city),
                    location_country = VALUES(location_country)
            """, (
                user_id, strava_id, activity_type, activity_name, distance, duration, pace, speed,
                calories, hr_avg, hr_max, elevation, date, location_city, location_country
            ))
            conn.commit()

            # 🔑 Uzmi lokalni ID
            cursor.execute("SELECT activity_id FROM activities WHERE stravaActivityID = %s", (strava_id,))
            activity_row = cursor.fetchone()
            if activity_row:
                local_activity_id = activity_row["activity_id"]

                # Ubaci u activity_details
                cursor.execute("""
                    INSERT INTO activity_details 
                        (activity_id, max_speed, average_cadence, average_watts, max_watts, kilojoules, calories, gear_name, device_name, polyline)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        max_speed = VALUES(max_speed),
                        average_cadence = VALUES(average_cadence),
                        average_watts = VALUES(average_watts),
                        max_watts = VALUES(max_watts),
                        kilojoules = VALUES(kilojoules),
                        calories = VALUES(calories),
                        gear_name = VALUES(gear_name),
                        device_name = VALUES(device_name),
                        polyline = VALUES(polyline)
                """, (
                    local_activity_id,
                    act.get("max_speed"),
                    act.get("average_cadence"),
                    act.get("average_watts"),
                    act.get("max_watts"),
                    act.get("kilojoules"),
                    calories,  # 🔥 ovde dodaješ kalorije
                    gear_name,
                    device_name,
                    polyline
                ))
                conn.commit()

        return jsonify({"success": True, "message": f"Synced {len(all_activities)} activities"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@strava_bp.route('/get_activities', methods=['POST'])
def get_activities():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        limit = int(data.get('limit', 15))
        offset = int(data.get('offset', 0))

        if not user_id:
            return jsonify({"success": False, "message": "Missing user_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT a.activity_id, a.user_id, a.stravaActivityID, a.activity_type, a.distance,
                   a.duration, a.pace, a.speed, a.calories_burned, a.heart_rate_avg,
                   a.heart_rate_max, a.elevation_gain, a.date,
                   u.first_name, u.last_name
            FROM activities a
            JOIN users u ON a.user_id = u.user_id
            WHERE a.user_id = %s
            ORDER BY a.date DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, (user_id, limit, offset))
        activities = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "data": activities,
            "limit": limit,
            "offset": offset,
            "count": len(activities)
        })

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@strava_bp.route("/get_activity", methods=["POST"])
def get_activity():
    """
    Vraća detalje jedne aktivnosti po activity_id.
    Body zahteva JSON:
    {
        "activity_id": 123
    }
    """
    data = request.get_json()
    if not data or "activity_id" not in data:
        return jsonify({"success": False, "message": "Missing activity_id"}), 400

    activity_id = data["activity_id"]
    conn = get_db_connection()

    try:
        # Koristi buffered cursor da pročita sve rezultate odmah
        cursor = conn.cursor(dictionary=True, buffered=True)

        cursor.execute("SELECT * FROM activities WHERE activity_id = %s", (activity_id,))
        activity = cursor.fetchone()

        if not activity:
            cursor.close()
            return jsonify({"success": False, "message": "Activity not found"}), 404

        cursor.execute("SELECT * FROM activity_details WHERE activity_id = %s", (activity_id,))
        details = cursor.fetchone()
        cursor.close()

        if details:
            activity.update(details)

        return jsonify({"success": True, "data": activity})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()
