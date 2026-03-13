#!/usr/bin/env python3
"""
Test script for the Car Service Decision AI API
"""
import json
import requests
from requests.auth import HTTPBasicAuth

# Configuration
BASE_URL = "http://localhost:8000"
USERNAME = "way_user"
PASSWORD = "W@y_U53r"

def test_sms_received():
    """Test the sms-received endpoint"""
    print("Testing SMS Received endpoint...")
    
    payload = {
        "event": "sms-received",
        "customer": {
            "name": "John Doe",
            "phone": "555-1234",
            "email": "john@example.com"
        },
        "communications": {
            "sms": [
                {
                    "from": "customer",
                    "text": "Hi, I'm on my way to pick up my car. Will be there in 15 minutes.",
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            ]
        },
        "currentRepairOrder": {
            "vehicle": {
                "make": "Toyota",
                "model": "Camry",
                "year": 2020,
                "vin": "1HGBH41JXMN109186"
            },
            "repairOrder": {
                "status": "completed",
                "services": [
                    {"name": "Oil Change", "type": "maintenance"},
                    {"name": "Brake Inspection", "type": "inspection"}
                ],
                "shopNotes": "Vehicle ready for pickup. All services completed successfully."
            }
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/process",
            json=payload,
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server. Make sure it's running on localhost:8000")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_invoice_summary():
    """Test the invoice-summary endpoint"""
    print("\nTesting Invoice Summary endpoint...")
    
    payload = {
        "event": "invoice-summary",
        "customer": {
            "name": "Jane Smith",
            "phone": "555-5678"
        },
        "communications": {
            "sms": []
        },
        "currentRepairOrder": {
            "vehicle": {
                "make": "Honda",
                "model": "Civic",
                "year": 2019
            },
            "repairOrder": {
                "status": "completed",
                "services": [
                    {
                        "name": "Engine Diagnostic",
                        "type": "diagnostic",
                        "lineItems": [
                            {"name": "Diagnostic Fee", "amount": 150.00},
                            {"name": "Labor", "amount": 75.00}
                        ]
                    },
                    {
                        "name": "Spark Plug Replacement",
                        "type": "repair",
                        "lineItems": [
                            {"name": "Spark Plugs (4x)", "amount": 45.00},
                            {"name": "Labor", "amount": 120.00}
                        ]
                    }
                ],
                "shopNotes": "Engine misfire resolved. Replaced all spark plugs and performed diagnostic scan."
            }
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/process",
            json=payload,
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server. Make sure it's running on localhost:8000")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_unauthorized():
    """Test unauthorized access"""
    print("\nTesting unauthorized access...")
    
    payload = {"event": "sms-received"}
    
    try:
        response = requests.post(
            f"{BASE_URL}/process",
            json=payload,
            auth=HTTPBasicAuth("wrong", "credentials")
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 401
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_invalid_event():
    """Test invalid event type"""
    print("\nTesting invalid event type...")
    
    payload = {"event": "invalid-event"}
    
    try:
        response = requests.post(
            f"{BASE_URL}/process",
            json=payload,
            auth=HTTPBasicAuth(USERNAME, PASSWORD)
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 422
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Car Service Decision AI - API Test Suite")
    print("=" * 50)
    
    # Run tests
    tests = [
        test_sms_received,
        test_invoice_summary,
        test_unauthorized,
        test_invalid_event
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print("-" * 30)
    
    print(f"\nTest Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed. Check the output above.")
