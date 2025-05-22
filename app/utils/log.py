from flask import Blueprint, request, jsonify


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
