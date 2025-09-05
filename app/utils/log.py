from flask import Blueprint, request, jsonify
import os
from datetime import datetime

LOG_DIR = "logs"
log_bp = Blueprint('log', __name__, url_prefix='/api')
@log_bp.route('/data', methods=['POST'])
def receive_data():
    # Get data from the request's JSON body
    data = request.get_json()

    # Extract the input data sent from Flutter
    input_data = data.get('input')

    print(input_data)

    # Process the data as needed
    return jsonify({'message': f'Received input: {input_data}'})


def log_action(action: str):
    """Zapisuje akciju u fajl logs/log_YYYY-MM-DD.txt"""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    filename = f"log_{datetime.now().strftime('%Y-%m-%d')}.txt"
    filepath = os.path.join(LOG_DIR, filename)

    with open(filepath, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {action}\n")