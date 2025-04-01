# Import necessary modules
from flask import Flask
from routes import register_blueprints

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object('config.Config')
    
    # Register all routes
    register_blueprints(app)
    
    return app 