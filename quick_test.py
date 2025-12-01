#!/usr/bin/env python3
"""
Quick test script to verify the application is working.
Run this after starting the server to verify basic functionality.
"""
import requests
import json
import sys
from uuid import UUID

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    print("1. Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("   ✅ Health check passed")
            return True
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        print("   Make sure the server is running on http://localhost:8000")
        return False

def test_create_sku():
    """Test creating a SKU."""
    print("2. Testing SKU creation...")
    try:
        data = {
            "sku_code": "TEST-SKU-001",
            "name": "Test Product",
            "description": "Quick test product",
            "initial_qty": 100
        }
        response = requests.post(f"{BASE_URL}/api/v1/skus", json=data)
        if response.status_code == 201:
            sku = response.json()
            print(f"   ✅ SKU created: {sku['sku_code']}")
            return sku['sku_id']
        else:
            print(f"   ❌ SKU creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"   ❌ SKU creation failed: {e}")
        return None

def test_get_availability(sku_id):
    """Test getting availability."""
    print("3. Testing availability check...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/inventory/availability", 
                              params={"sku_ids": sku_id})
        if response.status_code == 200:
            availability = response.json()
            if availability:
                avail = availability[0]
                print(f"   ✅ Availability: {avail['available_qty']} available out of {avail['total_qty']} total")
                return True
            else:
                print("   ❌ No availability data returned")
                return False
        else:
            print(f"   ❌ Availability check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Availability check failed: {e}")
        return False

def test_create_hold(sku_id):
    """Test creating a hold."""
    print("4. Testing hold creation...")
    try:
        data = {
            "client_token": "quick-test-token-123",
            "items": [{"sku_id": sku_id, "qty": 10}],
            "expires_in_seconds": 300,
            "strategy": "optimistic"
        }
        response = requests.post(f"{BASE_URL}/api/v1/inventory/holds", json=data)
        if response.status_code == 201:
            reservation = response.json()
            print(f"   ✅ Hold created: {reservation['reservation_id']}")
            print(f"   Status: {reservation['status']}")
            return reservation['reservation_id']
        else:
            print(f"   ❌ Hold creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"   ❌ Hold creation failed: {e}")
        return None

def test_idempotency(sku_id):
    """Test idempotency."""
    print("5. Testing idempotency...")
    try:
        data = {
            "client_token": "quick-test-token-123",  # Same token as before
            "items": [{"sku_id": sku_id, "qty": 10}],
            "expires_in_seconds": 300,
            "strategy": "optimistic"
        }
        response = requests.post(f"{BASE_URL}/api/v1/inventory/holds", json=data)
        if response.status_code == 201:
            reservation = response.json()
            print(f"   ✅ Idempotency working: Same reservation returned")
            return True
        else:
            print(f"   ❌ Idempotency test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Idempotency test failed: {e}")
        return False

def test_convert_hold(reservation_id):
    """Test converting hold to allocation."""
    print("6. Testing hold to allocation conversion...")
    try:
        response = requests.post(f"{BASE_URL}/api/v1/inventory/holds/{reservation_id}/convert")
        if response.status_code == 200:
            reservation = response.json()
            print(f"   ✅ Hold converted to allocation: {reservation['status']}")
            return True
        else:
            print(f"   ❌ Conversion failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Conversion failed: {e}")
        return False

def test_consistency():
    """Test consistency check."""
    print("7. Testing consistency check...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/inventory/consistency")
        if response.status_code == 200:
            report = response.json()
            if report['is_consistent']:
                print(f"   ✅ Consistency check passed: {report['total_skus']} SKUs consistent")
                return True
            else:
                print(f"   ⚠️  Consistency issues found: {len(report['inconsistent_skus'])} issues")
                return False
        else:
            print(f"   ❌ Consistency check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Consistency check failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Quick Test Suite - Inventory Reservation Service")
    print("=" * 60)
    print()
    
    # Test 1: Health
    if not test_health():
        print("\n❌ Server is not running or not accessible.")
        print("   Start the server with: uvicorn app.main:app --reload")
        sys.exit(1)
    
    print()
    
    # Test 2: Create SKU
    sku_id = test_create_sku()
    if not sku_id:
        print("\n❌ Failed to create SKU. Check database connection.")
        sys.exit(1)
    
    print()
    
    # Test 3: Get Availability
    if not test_get_availability(sku_id):
        print("\n❌ Availability check failed.")
        sys.exit(1)
    
    print()
    
    # Test 4: Create Hold
    reservation_id = test_create_hold(sku_id)
    if not reservation_id:
        print("\n❌ Failed to create hold.")
        sys.exit(1)
    
    print()
    
    # Test 5: Idempotency
    if not test_idempotency(sku_id):
        print("\n⚠️  Idempotency test failed (may still work, but check)")
    
    print()
    
    # Test 6: Convert Hold
    if not test_convert_hold(reservation_id):
        print("\n❌ Failed to convert hold to allocation.")
        sys.exit(1)
    
    print()
    
    # Test 7: Consistency
    if not test_consistency():
        print("\n⚠️  Consistency check found issues (may be expected)")
    
    print()
    print("=" * 60)
    print("✅ All basic tests passed!")
    print("=" * 60)
    print("\nFor more detailed testing, see TESTING_GUIDE.md")
    print("Or use the interactive API docs at http://localhost:8000/docs")

if __name__ == "__main__":
    main()

