from flask import Flask, request, jsonify, redirect
from flasgger import Swagger

from app.utils.log import log_action


def create_app():
    app = Flask(__name__)
    swagger = Swagger(app, template={
        "info": {
            "title": "Triathlon Forge API",
            "description": "TriathlonForge API enables triathletes and runners to manage their training data, track progress, and receive personalized recommendations. It integrates with STRAVA to import activity data and provides features such as user authentication, profile management, activity tracking, analytics reporting, training plans, notifications, and social sharing.",
            "version": "1.0.0"
        }
    })

    from .auth import auth_bp
    from app.strava import strava_bp
    from app.utils.log import log_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(strava_bp)
    app.register_blueprint(log_bp)

    @app.before_request
    def log_request_info():
        log_action(f"Request: {request.method} {request.path}")


    return app