#!/usr/bin/env python3
"""
Test script to verify custom validation functions work correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_validation():
    """Test the custom validation functions"""
    
    print("🧪 Testing Custom Validation Functions...")
    
    try:
        from app.core.validators import validate_email, validate_student_id, validate_phone_number
        
        # Test email validation
        test_emails = [
            "test@babcock.edu",      # Valid
            "invalid-email",          # Invalid
            "user@domain.com",        # Valid
            "test@",                  # Invalid
            "@domain.com"             # Invalid
        ]
        
        for email in test_emails:
            is_valid = validate_email(email)
            status = "✅" if is_valid else "❌"
            print(f"{status} Email '{email}': {'Valid' if is_valid else 'Invalid'}")
        
        # Test student ID validation
        test_ids = [
            "BU2024001",             # Valid
            "BU12345678",             # Valid
            "BU2024",                 # Invalid (too short)
            "BU202400123",            # Invalid (too long)
            "ABC2024001",             # Invalid (wrong prefix)
            "2024001"                 # Invalid (no prefix)
        ]
        
        for student_id in test_ids:
            is_valid = validate_student_id(student_id)
            status = "✅" if is_valid else "❌"
            print(f"{status} Student ID '{student_id}': {'Valid' if is_valid else 'Invalid'}")
        
        # Test phone validation
        test_phones = [
            "+2348012345678",         # Valid Nigerian
            "08012345678",            # Valid Nigerian
            "+234801234567",          # Valid Nigerian
            "0801234567",             # Valid Nigerian
            "+1234567890",            # Valid International
            "invalid-phone",          # Invalid
            ""                        # Valid (optional)
        ]
        
        for phone in test_phones:
            is_valid = validate_phone_number(phone)
            status = "✅" if is_valid else "❌"
            print(f"{status} Phone '{phone}': {'Valid' if is_valid else 'Invalid'}")
        
        print("\n🎉 Validation tests completed!")
        
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        import traceback
        traceback.print_exc()

def test_schema_validation():
    """Test the Pydantic schema validation"""
    
    print("\n🧪 Testing Pydantic Schema Validation...")
    
    try:
        from app.schemas.user import UserCreate, UserLogin
        
        # Test valid user creation
        valid_user = UserCreate(
            student_id="BU2024001",
            email="test@babcock.edu",
            full_name="Test Student",
            password="test123",
            department="Computer Science",
            level="300"
        )
        print(f"✅ Valid user created: {valid_user.full_name}")
        
        # Test valid login
        valid_login = UserLogin(
            email="test@babcock.edu",
            password="test123"
        )
        print(f"✅ Valid login created: {valid_login.email}")
        
        # Test invalid email
        try:
            invalid_user = UserCreate(
                student_id="BU2024001",
                email="invalid-email",
                full_name="Test Student",
                password="test123",
                department="Computer Science",
                level="300"
            )
            print("❌ Invalid email should have failed validation")
        except ValueError as e:
            print(f"✅ Invalid email correctly rejected: {e}")
        
        # Test invalid student ID
        try:
            invalid_user = UserCreate(
                student_id="INVALID",
                email="test@babcock.edu",
                full_name="Test Student",
                password="test123",
                department="Computer Science",
                level="300"
            )
            print("❌ Invalid student ID should have failed validation")
        except ValueError as e:
            print(f"✅ Invalid student ID correctly rejected: {e}")
        
        print("\n🎉 Schema validation tests completed!")
        
    except Exception as e:
        print(f"❌ Schema validation test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_validation()
    test_schema_validation()
