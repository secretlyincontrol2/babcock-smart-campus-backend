"""
Flask Maps Router
Full maps and location functionality
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
from datetime import datetime
from bson import ObjectId
from typing import Dict, Any

from ..database import get_database
from ..core.exceptions import CustomHTTPException

logger = logging.getLogger(__name__)

maps_bp = Blueprint('maps', __name__)

@maps_bp.route('/locations', methods=['POST'])
@jwt_required()
def create_location():
    """Create a new location (admin only)"""
    try:
        current_user_email = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'category', 'latitude', 'longitude', 'description']
        for field in required_fields:
            if not data.get(field):
                raise CustomHTTPException(400, f"Missing required field: {field}")
        
        db = get_database()
        
        # Check if current user is admin
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user or not current_user.get('is_admin', False):
            raise CustomHTTPException(403, "Only admins can create locations")
        
        # Validate coordinates
        try:
            lat = float(data['latitude'])
            lng = float(data['longitude'])
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                raise ValueError("Invalid coordinates")
        except ValueError:
            raise CustomHTTPException(400, "Invalid latitude or longitude")
        
        # Create location document
        location_doc = {
            "name": data['name'],
            "category": data['category'],
            "latitude": lat,
            "longitude": lng,
            "description": data['description'],
            "address": data.get('address', ''),
            "building": data.get('building', ''),
            "floor": data.get('floor', ''),
            "room": data.get('room', ''),
            "tags": data.get('tags', []),
            "is_active": True,
            "created_by": str(current_user['_id']),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = db.locations.insert_one(location_doc)
        location_doc['_id'] = str(result.inserted_id)
        
        logger.info(f"Location created: {data['name']} by admin {current_user_email}")
        
        return jsonify({
            "message": "Location created successfully",
            "location": location_doc
        }), 201
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Create location error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@maps_bp.route('/locations', methods=['GET'])
def get_locations():
    """Get locations with filtering"""
    try:
        db = get_database()
        
        # Get query parameters
        category = request.args.get('category')
        search = request.args.get('search')
        is_active = request.args.get('is_active', 'true').lower() == 'true'
        
        # Build filter query
        filter_query = {"is_active": is_active}
        
        if category:
            filter_query["category"] = category
        if search:
            filter_query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
                {"building": {"$regex": search, "$options": "i"}}
            ]
        
        # Get locations
        locations_cursor = db.locations.find(filter_query).sort("name", 1)
        locations = []
        
        for location in locations_cursor:
            location['_id'] = str(location['_id'])
            locations.append(location)
        
        return jsonify({
            "locations": locations,
            "total_count": len(locations)
        })
        
    except Exception as e:
        logger.error(f"Get locations error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@maps_bp.route('/locations/<location_id>', methods=['GET'])
def get_location(location_id):
    """Get specific location by ID"""
    try:
        if not ObjectId.is_valid(location_id):
            raise CustomHTTPException(400, "Invalid location ID format")
        
        db = get_database()
        
        location = db.locations.find_one({"_id": ObjectId(location_id)})
        if not location:
            raise CustomHTTPException(404, "Location not found")
        
        location['_id'] = str(location['_id'])
        
        return jsonify(location)
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Get location error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@maps_bp.route('/locations/<location_id>', methods=['PUT'])
@jwt_required()
def update_location(location_id):
    """Update location (admin only)"""
    try:
        if not ObjectId.is_valid(location_id):
            raise CustomHTTPException(400, "Invalid location ID format")
        
        current_user_email = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            raise CustomHTTPException(400, "No data provided")
        
        db = get_database()
        
        # Check if current user is admin
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user or not current_user.get('is_admin', False):
            raise CustomHTTPException(403, "Only admins can update locations")
        
        # Fields that can be updated
        allowed_fields = ['name', 'category', 'latitude', 'longitude', 'description', 'address', 'building', 'floor', 'room', 'tags', 'is_active']
        update_data = {}
        
        for field in allowed_fields:
            if field in data:
                if field in ['latitude', 'longitude']:
                    try:
                        val = float(data[field])
                        if field == 'latitude' and not (-90 <= val <= 90):
                            raise ValueError("Invalid latitude")
                        if field == 'longitude' and not (-180 <= val <= 180):
                            raise ValueError("Invalid longitude")
                        update_data[field] = val
                    except ValueError:
                        raise CustomHTTPException(400, f"Invalid {field}")
                else:
                    update_data[field] = data[field]
        
        if not update_data:
            raise CustomHTTPException(400, "No valid fields to update")
        
        update_data['updated_at'] = datetime.utcnow()
        
        # Update location
        result = db.locations.update_one(
            {"_id": ObjectId(location_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise CustomHTTPException(400, "No changes made")
        
        logger.info(f"Location updated: {location_id} by admin {current_user_email}")
        
        return jsonify({
            "message": "Location updated successfully"
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Update location error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@maps_bp.route('/locations/<location_id>', methods=['DELETE'])
@jwt_required()
def delete_location(location_id):
    """Delete location (admin only)"""
    try:
        if not ObjectId.is_valid(location_id):
            raise CustomHTTPException(400, "Invalid location ID format")
        
        current_user_email = get_jwt_identity()
        db = get_database()
        
        # Check if current user is admin
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user or not current_user.get('is_admin', False):
            raise CustomHTTPException(403, "Only admins can delete locations")
        
        # Delete location
        result = db.locations.delete_one({"_id": ObjectId(location_id)})
        
        if result.deleted_count == 0:
            raise CustomHTTPException(404, "Location not found")
        
        logger.info(f"Location deleted: {location_id} by admin {current_user_email}")
        
        return jsonify({
            "message": "Location deleted successfully"
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete location error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@maps_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all location categories"""
    try:
        db = get_database()
        
        # Get unique categories
        categories = db.locations.distinct("category")
        
        return jsonify({
            "categories": categories
        })
        
    except Exception as e:
        logger.error(f"Get categories error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@maps_bp.route('/campus-info', methods=['GET'])
def get_campus_info():
    """Get campus information"""
    try:
        db = get_database()
        
        # Get campus statistics
        total_locations = db.locations.count_documents({"is_active": True})
        
        # Get category breakdown
        category_pipeline = [
            {"$match": {"is_active": True}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        category_breakdown = list(db.locations.aggregate(category_pipeline))
        
        # Get building breakdown
        building_pipeline = [
            {"$match": {"is_active": True, "building": {"$exists": True, "$ne": ""}}},
            {"$group": {"_id": "$building", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        building_breakdown = list(db.locations.aggregate(building_pipeline))
        
        return jsonify({
            "total_locations": total_locations,
            "category_breakdown": category_breakdown,
            "building_breakdown": building_breakdown,
            "campus_name": "Babcock University",
            "description": "Smart Campus with comprehensive location services"
        })
        
    except Exception as e:
        logger.error(f"Get campus info error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@maps_bp.route('/search', methods=['GET'])
def search_locations():
    """Search locations by query"""
    try:
        query = request.args.get('q', '')
        if not query:
            raise CustomHTTPException(400, "Search query is required")
        
        db = get_database()
        
        # Build search query
        search_query = {
            "is_active": True,
            "$or": [
                {"name": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}},
                {"building": {"$regex": query, "$options": "i"}},
                {"category": {"$regex": query, "$options": "i"}},
                {"tags": {"$in": [query]}}
            ]
        }
        
        # Get search results
        locations_cursor = db.locations.find(search_query).limit(20)
        locations = []
        
        for location in locations_cursor:
            location['_id'] = str(location['_id'])
            locations.append(location)
        
        return jsonify({
            "query": query,
            "results": locations,
            "total_results": len(locations)
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Search locations error: {e}")
        raise CustomHTTPException(500, "Internal server error")
