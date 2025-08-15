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
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return jsonify({
            "error": "Endpoint not found",
            "error_type": "not_found",
            "message": "The requested endpoint does not exist",
            "available_endpoints": {
                "root": "/",
                "health": "/health",
                "info": "/info",
                "docs": "/docs",
                "auth": "/auth/login, /auth/register",
                "users": "/users/profile",
                "attendance": "/attendance/generate-qr",
                "cafeteria": "/cafeteria/menu",
                "maps": "/maps/locations",
                "schedule": "/schedule/classes",
                "chat": "/chat/conversations"
            }
        }), 404
    
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
    
    @app.route('/', methods=['GET'])
    def root():
        """Root endpoint"""
        return jsonify({
            "message": "Welcome to Smart Campus App API",
            "version": settings.APP_VERSION,
            "university": "Babcock University",
            "status": "operational",
            "endpoints": {
                "health": "/health",
                "info": "/info",
                "docs": "/docs",
                "auth": "/auth",
                "users": "/users",
                "attendance": "/attendance",
                "cafeteria": "/cafeteria",
                "maps": "/maps",
                "schedule": "/schedule",
                "chat": "/chat"
            }
        })
    
    # Documentation endpoint
    @app.route('/docs', methods=['GET'])
    def api_docs():
        """API Documentation endpoint"""
        return jsonify({
            "title": "Smart Campus App API Documentation",
            "version": settings.APP_VERSION,
            "description": "API for Babcock University Smart Campus App",
            "base_url": request.url_root.rstrip('/'),
            "endpoints": {
                "authentication": {
                    "POST /auth/register": "Register a new user",
                    "POST /auth/login": "User login",
                    "POST /auth/refresh": "Refresh access token",
                    "POST /auth/logout": "User logout"
                },
                "users": {
                    "GET /users/profile": "Get user profile (requires auth)",
                    "PUT /users/profile": "Update user profile (requires auth)",
                    "GET /users/{id}": "Get user by ID (requires auth)"
                },
                "attendance": {
                    "POST /attendance/generate-qr": "Generate QR code for attendance (requires auth)",
                    "POST /attendance/mark": "Mark attendance using QR code (requires auth)",
                    "GET /attendance/history": "Get attendance history (requires auth)"
                },
                "cafeteria": {
                    "GET /cafeteria/menu": "Get cafeteria menu",
                    "POST /cafeteria/order": "Place food order (requires auth)",
                    "GET /cafeteria/orders": "Get user orders (requires auth)"
                },
                "maps": {
                    "GET /maps/locations": "Get campus locations",
                    "GET /maps/navigation": "Get navigation between points"
                },
                "schedule": {
                    "GET /schedule/classes": "Get class schedule (requires auth)",
                    "POST /schedule/add": "Add to schedule (requires auth)"
                },
                "chat": {
                    "GET /chat/conversations": "Get chat conversations (requires auth)",
                    "POST /chat/message": "Send message (requires auth)"
                },
                "system": {
                    "GET /health": "Health check",
                    "GET /info": "API information",
                    "GET /db-status": "Database status"
                }
            },
            "authentication": {
                "type": "Bearer Token",
                "header": "Authorization: Bearer <access_token>"
            },
            "demo_mode": settings.DEMO_MODE
        })
    
    # Test endpoint to verify app is working
    @app.route('/test', methods=['GET'])
    def test_endpoint():
        """Simple test endpoint to verify app is working"""
        return jsonify({
            "message": "Backend is working!",
            "status": "success",
            "timestamp": datetime.now().isoformat()
        })
    
    # Simple auth test endpoint
    @app.route('/auth-test', methods=['GET'])
    def auth_test():
        """Test auth endpoint to verify routing is working"""
        return jsonify({
            "message": "Auth endpoint is accessible!",
            "status": "success",
            "available_auth_endpoints": [
                "/auth/register",
                "/auth/login", 
                "/auth/refresh",
                "/auth/me"
            ]
        })
    
    # Request debugging middleware
    @app.before_request
    def log_request_info():
        """Log all incoming requests for debugging"""
        logger.info(f"🌐 Request: {request.method} {request.path}")
        logger.info(f"🌐 Headers: {dict(request.headers)}")
        if request.is_json:
            logger.info(f"🌐 JSON Data: {request.get_json()}")
    
    @app.after_request
    def log_response_info(response):
        """Log all outgoing responses for debugging"""
        logger.info(f"📤 Response: {response.status_code} - {response.get_data(as_text=True)[:200]}")
        return response
    
    # Register blueprints (routes)
    try:
        logger.info("🔄 Starting Flask blueprint registration...")
        
        from .routers.flask_auth import auth_bp
        logger.info("✅ Auth blueprint imported successfully")
        
        from .routers.flask_users import users_bp
        logger.info("✅ Users blueprint imported successfully")
        
        from .routers.flask_attendance import attendance_bp
        logger.info("✅ Attendance blueprint imported successfully")
        
        from .routers.flask_cafeteria import cafeteria_bp
        logger.info("✅ Cafeteria blueprint imported successfully")
        
        from .routers.flask_maps import maps_bp
        logger.info("✅ Maps blueprint imported successfully")
        
        from .routers.flask_schedule import schedule_bp
        logger.info("✅ Schedule blueprint imported successfully")
        
        from .routers.flask_chat import chat_bp
        logger.info("✅ Chat blueprint imported successfully")
        
        # Register each blueprint individually with error handling
        try:
            app.register_blueprint(auth_bp, url_prefix='/auth')
            logger.info("✅ Auth blueprint registered successfully")
        except Exception as e:
            logger.error(f"❌ Failed to register auth blueprint: {e}")
        
        try:
            app.register_blueprint(users_bp, url_prefix='/users')
            logger.info("✅ Users blueprint registered successfully")
        except Exception as e:
            logger.error(f"❌ Failed to register users blueprint: {e}")
        
        try:
            app.register_blueprint(attendance_bp, url_prefix='/attendance')
            logger.info("✅ Attendance blueprint registered successfully")
        except Exception as e:
            logger.error(f"❌ Failed to register attendance blueprint: {e}")
        
        try:
            app.register_blueprint(cafeteria_bp, url_prefix='/cafeteria')
            logger.info("✅ Cafeteria blueprint registered successfully")
        except Exception as e:
            logger.error(f"❌ Failed to register cafeteria blueprint: {e}")
        
        try:
            app.register_blueprint(maps_bp, url_prefix='/maps')
            logger.info("✅ Maps blueprint registered successfully")
        except Exception as e:
            logger.error(f"❌ Failed to register maps blueprint: {e}")
        
        try:
            app.register_blueprint(schedule_bp, url_prefix='/schedule')
            logger.info("✅ Schedule blueprint registered successfully")
        except Exception as e:
            logger.error(f"❌ Failed to register schedule blueprint: {e}")
        
        try:
            app.register_blueprint(chat_bp, url_prefix='/chat')
            logger.info("✅ Chat blueprint registered successfully")
        except Exception as e:
            logger.error(f"❌ Failed to register chat blueprint: {e}")
        
        logger.info("✅ All Flask blueprints registration completed")
        
    except Exception as e:
        logger.error(f"❌ Error during Flask blueprint registration: {e}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        # Don't fail the app startup, just log the error
    
    return app

# Create app instance
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)), debug=settings.DEBUG)
