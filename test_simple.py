#!/usr/bin/env python3
"""
Simple test to check basic imports
"""

print("Testing basic imports...")

try:
    import fastapi
    print(f"✅ FastAPI imported: {fastapi.__version__}")
except Exception as e:
    print(f"❌ FastAPI import failed: {e}")

try:
    import pydantic
    print(f"✅ Pydantic imported: {pydantic.__version__}")
except Exception as e:
    print(f"❌ Pydantic import failed: {e}")

try:
    import uvicorn
    print(f"✅ Uvicorn imported: {uvicorn.__version__}")
except Exception as e:
    print(f"❌ Uvicorn import failed: {e}")

try:
    import motor
    print(f"✅ Motor imported: {motor.__version__}")
except Exception as e:
    print(f"❌ Motor import failed: {e}")

try:
    import jwt
    print(f"✅ PyJWT imported: {jwt.__version__}")
except Exception as e:
    print(f"❌ PyJWT import failed: {e}")

print("Import test completed!")
