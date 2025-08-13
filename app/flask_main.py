"""
Flask Main Application
Replaces FastAPI for better deployment compatibility
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import logging
import time
from datetime import datetime
import os

from .core.config import settings
from .database import connect_to_mongo, close_mongo_connection, check_database_health
from .core.exceptions import CustomHTTPException

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = settings.SECRET_KEY
    app.config['JWT_SECRET_KEY'] = settings.SECRET_KEY
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    
    # Initialize extensions
    jwt = JWTManager(app)
    CORS(app, origins=settings.ALLOWED_ORIGINS, supports_credentials=True)
    
    # Startup initialization (Flask 3 compatible)
    app.config.setdefault('APP_INITIALIZED', False)

    @app.before_request
    def ensure_initialized():
        """Initialize app resources on the first incoming request"""
        if app.config.get('APP_INITIALIZED'):
            return
        startup_time = time.time()
        try:
            logger.info("🚀 Initializing Smart Campus App...")
            if not settings.DEMO_MODE:
                try:
                    connect_to_mongo()
                    logger.info("✅ MongoDB connection established")
                except Exception as e:
                    logger.warning(f"⚠️ MongoDB connection failed (continuing without database): {e}")
                    logger.info("📝 Running in offline/demo mode - some features may be limited")
            else:
                logger.info("🎭 Running in DEMO MODE - MongoDB connection skipped")
                logger.info("📝 Demo mode enabled - using mock data and limited features")
            startup_duration = time.time() - startup_time
            logger.info(f"✅ Initialization completed in {startup_duration:.2f}s")
            app.config['APP_INITIALIZED'] = True
        except Exception as e:
            startup_duration = time.time() - startup_time
            logger.error(f"❌ Initialization failed after {startup_duration:.2f}s: {e}")
    
    @app.teardown_appcontext
    def shutdown(exception=None):
        """Application shutdown"""
        try:
            close_mongo_connection()
            logger.info("🔄 Application shutdown completed")
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")
    
    # Global exception handler
    @app.errorhandler(CustomHTTPException)
    def handle_custom_exception(error):
        return jsonify({
            "error": error.detail,
            "error_type": getattr(error, 'error_type', 'general_error'),
            "extra_data": getattr(error, 'extra_data', {})
        }), error.status_code
    
    @app.errorhandler(Exception)
    def handle_general_exception(error):
        logger.error(f"Unhandled exception: {error}")
        return jsonify({
            "error": "Internal server error",
            "error_type": "internal_error"
        }), 500
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        try:
            db_status = check_database_health()
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "database": db_status,
                "demo_mode": settings.DEMO_MODE
            })
        except Exception as e:
            return jsonify({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 500
    
    # Database status endpoint
    @app.route('/db-status', methods=['GET'])
    def db_status():
        """Database status endpoint"""
        try:
            status = check_database_health()
            return jsonify(status)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # Info endpoint
    @app.route('/info', methods=['GET'])
    def app_info():
        """Application information"""
        return jsonify({
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "description": "Smart Campus App API for Babcock University - Modern, Secure, and Scalable",
            "demo_mode": settings.DEMO_MODE,
            "debug": settings.DEBUG
        })
    
    # Register blueprints (routes)
    from .routers.flask_auth import auth_bp
    from .routers.flask_users import users_bp
    from .routers.flask_attendance import attendance_bp
    from .routers.flask_cafeteria import cafeteria_bp
    from .routers.flask_maps import maps_bp
    from .routers.flask_schedule import schedule_bp
    from .routers.flask_chat import chat_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(attendance_bp, url_prefix='/attendance')
    app.register_blueprint(cafeteria_bp, url_prefix='/cafeteria')
    app.register_blueprint(maps_bp, url_prefix='/maps')
    app.register_blueprint(schedule_bp, url_prefix='/schedule')
    app.register_blueprint(chat_bp, url_prefix='/chat')
    
    return app

# Create app instance
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)), debug=settings.DEBUG)
