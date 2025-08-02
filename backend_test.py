import requests
import sys
import json
from datetime import datetime
import uuid
import asyncio
import websockets
import time

class AIBrowserTerminalTester:
    def __init__(self, base_url="https://5b15c451-4da1-4e06-871f-f8a9795102c1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.ws_endpoint = None
        self.session_id = "test_session_001"  # Use specified test session ID
        self.browser_use_tests_passed = 0
        self.browser_use_tests_run = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

            print(f"Response Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"Response Data: {json.dumps(response_data, indent=2)}")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error Response: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"Error Text: {response.text}")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timed out after {timeout} seconds")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint - should return 'AI Terminal Assistant Ready'"""
        success, response = self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )
        
        if success and response.get('message') == 'AI Terminal Assistant Ready':
            print("✅ Correct message received")
            return True
        elif success:
            print(f"❌ Unexpected message: {response.get('message')}")
            return False
        return False

    def test_create_session(self):
        """Test creating a browser session"""
        success, response = self.run_test(
            "Create Browser Session",
            "POST",
            "create-session",
            200,
            timeout=45  # Browserless API can be slow
        )
        
        if success and 'wsEndpoint' in response and 'sessionId' in response:
            self.ws_endpoint = response['wsEndpoint']
            self.session_id = response['sessionId']
            print(f"✅ WebSocket endpoint received: {self.ws_endpoint[:50]}...")
            print(f"✅ Session ID received: {self.session_id}")
            return True
        elif success:
            print("❌ Response missing required fields (wsEndpoint, sessionId)")
            return False
        return False

    def test_chat_basic(self):
        """Test basic chat functionality"""
        if not self.session_id:
            print("❌ Skipping - No valid session ID available")
            return False

        success, response = self.run_test(
            "Basic Chat Message",
            "POST",
            "chat",
            200,
            data={
                "session_id": self.session_id,
                "message": "Hello, what can you do?"
            },
            timeout=30
        )
        
        if success:
            # Verify response structure
            required_fields = ['id', 'response']
            if all(field in response for field in required_fields):
                print("✅ Response has correct structure")
                print(f"✅ AI Response: {response['response'][:100]}...")
                return True
            else:
                print(f"❌ Response missing required fields: {required_fields}")
                return False
        return False

    def test_chat_with_browser_action(self):
        """Test chat with browser action"""
        if not self.session_id or not self.ws_endpoint:
            print("❌ Skipping - No valid session or WebSocket endpoint available")
            return False

        success, response = self.run_test(
            "Chat with Browser Action",
            "POST",
            "chat",
            200,
            data={
                "session_id": self.session_id,
                "message": "Go to google.com",
                "ws_endpoint": self.ws_endpoint
            },
            timeout=60  # Browser actions can take time
        )
        
        if success:
            # Verify response structure
            required_fields = ['id', 'response']
            if all(field in response for field in required_fields):
                print("✅ Response has correct structure")
                print(f"✅ AI Response: {response['response'][:100]}...")
                
                # Check if browser action was executed
                if response.get('browser_action'):
                    print("✅ Browser action included in response")
                if response.get('screenshot'):
                    print("✅ Screenshot included in response")
                    
                return True
            else:
                print(f"❌ Response missing required fields: {required_fields}")
                return False
        return False

    def test_chat_screenshot_request(self):
        """Test requesting a screenshot"""
        if not self.session_id or not self.ws_endpoint:
            print("❌ Skipping - No valid session or WebSocket endpoint available")
            return False

        success, response = self.run_test(
            "Screenshot Request",
            "POST",
            "chat",
            200,
            data={
                "session_id": self.session_id,
                "message": "Take a screenshot",
                "ws_endpoint": self.ws_endpoint
            },
            timeout=45
        )
        
        if success and response.get('screenshot'):
            print("✅ Screenshot returned as base64")
            return True
        elif success:
            print("❌ No screenshot in response")
            return False
        return False

    def test_chat_history(self):
        """Test retrieving chat history"""
        if not self.session_id:
            print("❌ Skipping - No valid session ID available")
            return False

        success, response = self.run_test(
            "Get Chat History",
            "GET",
            f"chat-history/{self.session_id}",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"✅ Chat history retrieved - {len(response)} messages")
                
                # Verify message structure if any messages exist
                if response:
                    first_msg = response[0]
                    required_fields = ['id', 'session_id', 'message', 'response', 'timestamp']
                    if all(field in first_msg for field in required_fields):
                        print("✅ Message structure is correct")
                        return True
                    else:
                        print(f"❌ Message missing required fields: {required_fields}")
                        return False
                else:
                    print("✅ Empty chat history (valid)")
                    return True
            else:
                print("❌ Chat history should be a list")
                return False
        return False

    def test_status_endpoints(self):
        """Test the existing status check endpoints"""
        # Test creating a status check
        success, response = self.run_test(
            "Create Status Check",
            "POST",
            "status",
            200,
            data={"client_name": f"test_client_{datetime.now().strftime('%H%M%S')}"}
        )
        
        if not success:
            return False

        # Test getting status checks
        success, response = self.run_test(
            "Get Status Checks",
            "GET",
            "status",
            200
        )
        return success

def main():
    print("🚀 Starting AI Browser Terminal API Tests")
    print("=" * 50)
    
    tester = AIBrowserTerminalTester()
    
    # Test sequence
    tests = [
        ("Root Endpoint", tester.test_root_endpoint),
        ("Status Endpoints", tester.test_status_endpoints),
        ("Create Browser Session", tester.test_create_session),
        ("Basic Chat", tester.test_chat_basic),
        ("Chat with Browser Action", tester.test_chat_with_browser_action),
        ("Screenshot Request", tester.test_chat_screenshot_request),
        ("Chat History", tester.test_chat_history),
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            test_func()
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
    
    # Print final results
    print(f"\n{'='*50}")
    print(f"📊 FINAL RESULTS")
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%" if tester.tests_run > 0 else "No tests run")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())