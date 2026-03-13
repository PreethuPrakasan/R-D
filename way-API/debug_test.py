#!/usr/bin/env python3
"""
Simple test to check server status and credentials
"""
import requests
from requests.auth import HTTPBasicAuth

def test_server_status():
    """Test if server is running"""
    try:
        response = requests.get("http://localhost:8000/docs", timeout=5)
        print(f"✅ Server is running - Status: {response.status_code}")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running or not accessible")
        return False
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        return False

def test_auth_combinations():
    """Test different auth combinations"""
    auth_combinations = [
        ("admin", "secret"),
        ("way_user", "secret"),
        ("admin", "password"),
        ("way_user", "password"),
    ]
    
    payload = {"event": "sms-received"}
    
    for username, password in auth_combinations:
        try:
            response = requests.post(
                "http://localhost:8000/process",
                json=payload,
                auth=HTTPBasicAuth(username, password),
                timeout=10
            )
            print(f"🔐 {username}:{password} -> Status: {response.status_code}")
            if response.status_code != 401:
                print(f"   Response: {response.text[:200]}...")
        except Exception as e:
            print(f"❌ {username}:{password} -> Error: {e}")

if __name__ == "__main__":
    print("🔍 Server Status Check")
    print("=" * 30)
    
    if test_server_status():
        print("\n🔐 Testing Authentication Combinations")
        print("=" * 40)
        test_auth_combinations()
    else:
        print("Cannot test authentication - server not running")
