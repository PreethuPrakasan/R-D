#!/usr/bin/env python3
"""
Comprehensive system test for Automotive AI Customer Service
"""
import requests
import json
import time

def test_backend_health():
    """Test if Python backend is healthy"""
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("✅ Python Backend: Healthy")
            return True
        else:
            print(f"❌ Python Backend: Unhealthy (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Python Backend: Connection failed - {e}")
        return False

def test_nodejs_server():
    """Test if Node.js server is running"""
    try:
        response = requests.get("http://localhost:5000/")
        if response.status_code == 200:
            print("✅ Node.js Server: Running")
            return True
        else:
            print(f"❌ Node.js Server: Not responding (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Node.js Server: Connection failed - {e}")
        return False

def test_ai_tools():
    """Test AI tools functionality"""
    tools_to_test = [
        {
            "name": "check_vehicle_status",
            "params": {"customer_phone": "+1234567890"},
            "expected_success": True
        },
        {
            "name": "get_service_info", 
            "params": {},
            "expected_success": True
        },
        {
            "name": "book_appointment",
            "params": {
                "customer_phone": "+1234567890",
                "service_name": "Oil Change",
                "preferred_date": "2024-01-15",
                "vehicle_info": "Toyota Camry 2020"
            },
            "expected_success": True
        }
    ]
    
    print("\n🧪 Testing AI Tools:")
    all_passed = True
    
    for tool in tools_to_test:
        try:
            response = requests.post(
                "http://localhost:8000/ai-tools/execute",
                json={
                    "tool_name": tool["name"],
                    "parameters": tool["params"]
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success") == tool["expected_success"]:
                    print(f"✅ {tool['name']}: Working")
                    print(f"   Response: {result.get('message', '')[:100]}...")
                else:
                    print(f"❌ {tool['name']}: Failed - {result.get('message', 'Unknown error')}")
                    all_passed = False
            else:
                print(f"❌ {tool['name']}: HTTP {response.status_code}")
                all_passed = False
                
        except Exception as e:
            print(f"❌ {tool['name']}: Exception - {e}")
            all_passed = False
    
    return all_passed

def test_twilio_integration():
    """Test Twilio webhook endpoint"""
    try:
        response = requests.post("http://localhost:5000/incoming-call")
        if response.status_code == 200:
            # Check if response contains TwiML
            content = response.text
            if "Response" in content and "Stream" in content:
                print("✅ Twilio Integration: TwiML response generated")
                return True
            else:
                print("❌ Twilio Integration: Invalid TwiML response")
                return False
        else:
            print(f"❌ Twilio Integration: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Twilio Integration: Exception - {e}")
        return False

def main():
    print("🚀 Automotive AI Customer Service - System Test")
    print("=" * 50)
    
    # Test individual components
    backend_ok = test_backend_health()
    nodejs_ok = test_nodejs_server()
    
    if not backend_ok or not nodejs_ok:
        print("\n❌ Basic services not running. Please start both servers first.")
        return
    
    # Test AI tools
    tools_ok = test_ai_tools()
    
    # Test Twilio integration
    twilio_ok = test_twilio_integration()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"Python Backend: {'✅ PASS' if backend_ok else '❌ FAIL'}")
    print(f"Node.js Server: {'✅ PASS' if nodejs_ok else '❌ FAIL'}")
    print(f"AI Tools: {'✅ PASS' if tools_ok else '❌ FAIL'}")
    print(f"Twilio Integration: {'✅ PASS' if twilio_ok else '❌ FAIL'}")
    
    if all([backend_ok, nodejs_ok, tools_ok, twilio_ok]):
        print("\n🎉 All tests passed! System is ready for production.")
        print("\n📞 To test with a real call:")
        print("1. Set up a Twilio phone number")
        print("2. Configure webhook URL: https://your-domain.com/incoming-call")
        print("3. Call the number and test the AI assistant!")
    else:
        print("\n⚠️  Some tests failed. Please check the issues above.")

if __name__ == "__main__":
    main()
