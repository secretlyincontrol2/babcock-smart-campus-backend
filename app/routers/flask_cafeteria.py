"""
Flask Cafeteria Router
Basic cafeteria management functionality
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
from datetime import datetime, timedelta
from bson import ObjectId

from ..database import get_database
from ..core.exceptions import CustomHTTPException

logger = logging.getLogger(__name__)

cafeteria_bp = Blueprint('cafeteria', __name__)

@cafeteria_bp.route('/menu', methods=['GET'])
def get_menu():
    """Get cafeteria menu"""
    try:
        db = get_database()
        
        # Get query parameters
        date = request.args.get('date')
        meal_type = request.args.get('meal_type')
        
        # Build filter query
        filter_query = {"is_active": True}
        
        if date:
            try:
                menu_date = datetime.strptime(date, "%Y-%m-%d")
                filter_query["date"] = menu_date
            except ValueError:
                raise CustomHTTPException(400, "Invalid date format. Use YYYY-MM-DD")
        else:
            # Default to today
            today = datetime.utcnow().date()
            filter_query["date"] = today
        
        if meal_type:
            filter_query["meal_type"] = meal_type
        
        # Get menu items
        menu_cursor = db.menu_items.find(filter_query).sort("meal_type", 1)
        menu = []
        
        for item in menu_cursor:
            item['_id'] = str(item['_id'])
            menu.append(item)
        
        return jsonify({
            "menu": menu,
            "total_items": len(menu)
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Get menu error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@cafeteria_bp.route('/menu', methods=['POST'])
@jwt_required()
def create_menu_item():
    """Create menu item (admin only)"""
    try:
        current_user_email = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'meal_type', 'date', 'price', 'category']
        for field in required_fields:
            if not data.get(field):
                raise CustomHTTPException(400, f"Missing required field: {field}")
        
        db = get_database()
        
        # Check if current user is admin
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user or not current_user.get('is_admin', False):
            raise CustomHTTPException(403, "Only admins can create menu items")
        
        # Parse date
        try:
            menu_date = datetime.strptime(data['date'], "%Y-%m-%d")
        except ValueError:
            raise CustomHTTPException(400, "Invalid date format. Use YYYY-MM-DD")
        
        # Create menu item
        menu_item = {
            "name": data['name'],
            "meal_type": data['meal_type'],
            "date": menu_date,
            "price": float(data['price']),
            "category": data['category'],
            "description": data.get('description', ''),
            "is_vegetarian": data.get('is_vegetarian', False),
            "is_available": data.get('is_available', True),
            "is_active": True,
            "created_by": str(current_user['_id']),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = db.menu_items.insert_one(menu_item)
        menu_item['_id'] = str(result.inserted_id)
        
        logger.info(f"Menu item created: {data['name']} by admin {current_user_email}")
        
        return jsonify({
            "message": "Menu item created successfully",
            "menu_item": menu_item
        }), 201
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Create menu item error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@cafeteria_bp.route('/orders', methods=['POST'])
@jwt_required()
def create_order():
    """Create food order"""
    try:
        current_user_email = get_jwt_identity()
        data = request.get_json()
        
        if not data.get('items') or not isinstance(data['items'], list):
            raise CustomHTTPException(400, "Order items are required")
        
        db = get_database()
        
        # Get current user
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user:
            raise CustomHTTPException(404, "User not found")
        
        # Validate and calculate total
        total_amount = 0
        order_items = []
        
        for item in data['items']:
            if not item.get('menu_item_id') or not item.get('quantity'):
                raise CustomHTTPException(400, "Each item must have menu_item_id and quantity")
            
            # Get menu item
            menu_item = db.menu_items.find_one({
                "_id": ObjectId(item['menu_item_id']),
                "is_active": True,
                "is_available": True
            })
            
            if not menu_item:
                raise CustomHTTPException(400, f"Menu item {item['menu_item_id']} not found or unavailable")
            
            item_total = menu_item['price'] * item['quantity']
            total_amount += item_total
            
            order_items.append({
                "menu_item_id": str(menu_item['_id']),
                "name": menu_item['name'],
                "price": menu_item['price'],
                "quantity": item['quantity'],
                "item_total": item_total
            })
        
        # Create order
        order = {
            "user_id": ObjectId(current_user['_id']),
            "student_id": current_user['student_id'],
            "full_name": current_user['full_name'],
            "items": order_items,
            "total_amount": total_amount,
            "status": "pending",
            "order_time": datetime.utcnow(),
            "estimated_ready_time": datetime.utcnow() + timedelta(minutes=20),
            "notes": data.get('notes', ''),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = db.orders.insert_one(order)
        order['_id'] = str(result.inserted_id)
        order['user_id'] = str(order['user_id'])
        
        logger.info(f"Order created: {order['_id']} by user {current_user_email}")
        
        return jsonify({
            "message": "Order created successfully",
            "order": order
        }), 201
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Create order error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@cafeteria_bp.route('/orders', methods=['GET'])
@jwt_required()
def get_my_orders():
    """Get current user's orders"""
    try:
        current_user_email = get_jwt_identity()
        db = get_database()
        
        # Get current user
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user:
            raise CustomHTTPException(404, "User not found")
        
        # Get query parameters
        status = request.args.get('status')
        limit = min(int(request.args.get('limit', 20)), 100)
        
        # Build filter query
        filter_query = {"user_id": ObjectId(current_user['_id'])}
        
        if status:
            filter_query["status"] = status
        
        # Get orders
        orders_cursor = db.orders.find(filter_query).sort("created_at", -1).limit(limit)
        orders = []
        
        for order in orders_cursor:
            order['_id'] = str(order['_id'])
            order['user_id'] = str(order['user_id'])
            orders.append(order)
        
        return jsonify({
            "orders": orders,
            "total_orders": len(orders)
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Get my orders error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@cafeteria_bp.route('/orders/<order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    """Get specific order by ID"""
    try:
        if not ObjectId.is_valid(order_id):
            raise CustomHTTPException(400, "Invalid order ID format")
        
        current_user_email = get_jwt_identity()
        db = get_database()
        
        # Get current user
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user:
            raise CustomHTTPException(404, "User not found")
        
        # Get order
        order = db.orders.find_one({"_id": ObjectId(order_id)})
        if not order:
            raise CustomHTTPException(404, "Order not found")
        
        # Check if user owns this order or is admin
        if str(order['user_id']) != str(current_user['_id']) and not current_user.get('is_admin', False):
            raise CustomHTTPException(403, "Insufficient privileges")
        
        order['_id'] = str(order['_id'])
        order['user_id'] = str(order['user_id'])
        
        return jsonify(order)
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Get order error: {e}")
        raise CustomHTTPException(500, "Internal server error")
